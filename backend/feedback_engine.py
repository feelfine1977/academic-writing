"""Grounded readings, deterministic comparison, and an auditable completion decision."""
import asyncio
import copy
import time
from . import providers
from .feedback_mcp import retrieve_with_fallback
from .storage import now

PIPELINE_VERSION='2.1'
STAGES={'context':'Reading saved task and writing guidance',
        'first_reading':'Reading meaning, English and task requirements',
        'second_reading':'Checking the answer in a separate reading',
        'compare':'Comparing judgements and checking quotations',
        'complete':'Feedback ready'}


def adequate(review):
    return (bool(review['criteria']) and all(c['status']=='met' for c in review['criteria'])
            and all(i['category']=='optional_clarity' for i in review['issues'])
            and all(i['status']=='present' for i in review.get('idea_coverage',[]))
            and not review.get('meaning_concerns') and not review.get('example'))


def compare(first,second):
    """No voting by fluent summaries: expose criterion disagreement and retain concerns."""
    result=copy.deepcopy(first);differences=[]
    other={c['criterion_index']:c for c in second['criteria']}
    for c in result['criteria']:
        b=other[c['criterion_index']]
        c['readings']=[{'reading':1,'status':c['status'],'explanation':c['explanation']},
                       {'reading':2,'status':b['status'],'explanation':b['explanation']}]
        if c['status']!=b['status']:
            differences.append({'criterion_index':c['criterion_index'],'criterion':c['criterion'],
                                'first_status':c['status'],'second_status':b['status']})
            c['status']='uncertain'
            c['explanation']='The two readings disagree. Compare their reasons below before changing your wording.'
    # Keep each reader's exact validated issue. A differing concern is a proposal, not a confirmed error.
    combined=[];seen=set()
    for number,review in enumerate((first,second),1):
        for issue in review['issues']:
            key=(issue['category'],issue['quote'],issue['explanation'])
            if key not in seen:combined.append({**issue,'raised_by':number});seen.add(key)
    combined.sort(key=lambda i:i['category']=='optional_clarity')
    result['issues']=combined[:3]
    result['meaning_concerns']=list(dict.fromkeys(first.get('meaning_concerns',[])+second.get('meaning_concerns',[])))[:5]
    result['idea_coverage']=first.get('idea_coverage',[])
    decision_agrees=adequate(first)==adequate(second)
    if differences or not decision_agrees:
        result['summary']='The readings reached different judgements. Your answer is saved; check the differing reasons before deciding whether to revise.'
    return result,{'disagreements':differences,'decision_agrees':decision_agrees,
                   'auto_completion_allowed':adequate(first) and adequate(second)}


def model_input(context,role):
    p=copy.deepcopy(context['snapshot']['input'])
    # Retain the full assessment contract, remove browsing/navigation metadata from model attention.
    keys=('id','key','title','format','prompt','criteria','parts','choices','learning_objective','teaching_note',
          'task_type','paper_node_id','paper_draft','rhetorical_move','skill_ids','course_domain')
    p['exercise']={k:v for k,v in p['exercise'].items() if k in keys}
    p['writing_guidance']=[{k:v for k,v in g.items() if k not in ('content_hash','reading','wise_application','practice_key')} for g in context['guidance']['guidance']]
    p['mechanical_checks']={k:v for k,v in context['contract'].items() if k not in ('snapshot_hash','assessment_text','supplied_stem')}
    p['reading_role']=role
    return p


async def review(root,store,job,progress,preview=None):
    started=time.monotonic();p=job['payload'];mode=p.get('review_mode','careful')
    progress('context');context=await retrieve_with_fallback(root,store.path,job['id'])
    profile=p['profile'];data=context['snapshot']['input'];e=data['exercise']
    supplied=data.get('assessment_text') if e['format']=='ordering' else None
    progress('first_reading')
    raw,generation=await providers.generate(profile,model_input(context,'first'),job['kind'])
    first=providers.validate_review(raw,data['learner_text'],job['kind'],e.get('criteria',[]),supplied)
    first_elapsed=round(time.monotonic()-started,2)
    result=copy.deepcopy(first);readings=[{'role':'first','review':first,'generation':generation}]
    quality={'pipeline_version':PIPELINE_VERSION,'mode':mode,'transport':context['transport'],
             'snapshot_hash':context['snapshot']['snapshot_hash'],'protocol_version':context.get('protocol_version'),
             'tool_calls':context['tool_calls'],'guidance':context['guidance']['guidance'],
             'context_notice':context.get('notice'),'mechanical_checks':context['contract'],
             'disagreements':[],'auto_completion_allowed':adequate(first),'status':'single_reading'}
    if mode=='careful' and job['kind']!='show_example' and e['format'] not in ('gap','ordering'):
        # Publish only a fully parsed, quotation-checked reading. It is not a
        # completion decision, and remains tied to this immutable saved attempt.
        if preview:
            early=copy.deepcopy(first)
            early.update(revision_id=p['revision_id'],source_hash=p['source_hash'],
                         quality={'status':'checking','auto_completion_allowed':False,
                                  'first_feedback_seconds':first_elapsed})
            preview(early)
        progress('second_reading')
        second_profile={**profile,'model':profile.get('verifier_model') or profile['model']}
        try:
            raw,g2=await providers.generate(second_profile,model_input(context,'second'),job['kind'])
            second=providers.validate_review(raw,data['learner_text'],job['kind'],e.get('criteria',[]),supplied)
            readings.append({'role':'second','review':second,'generation':g2})
            result,comparison=compare(first,second)
            quality.update(comparison,status='agreement' if not comparison['disagreements'] and comparison['decision_agrees'] else 'disagreement',
                           same_model=profile['model']==second_profile['model'])
        except asyncio.CancelledError:raise
        except Exception as error:
            quality.update(status='provisional',auto_completion_allowed=False,
                           verification_error=str(error)[:1500] if isinstance(error,ValueError) else 'The second reading could not finish. Retry to check this feedback.')
            result['summary']='The first reading is available, but its separate check did not finish. Treat this feedback as provisional and retry before relying on it.'
    progress('compare')
    if context['contract'].get('brief_within_limit') is False:
        quality.update(auto_completion_allowed=False,status='contract_check')
        result['summary']='The separately labelled brief exceeds 60 words. Shorten that part without removing the argument or its limits; the editorial note is counted separately.'
        result['issues']=[{'category':'task_fit','quote':'','occurrence':0,'span':None,'explanation':f"The brief contains {context['contract']['brief_words']} words; the limit is 60.",'hint':'Revise the brief only; keep the editorial note separate.'},*result['issues']][:3]
    flags=[f"Reading {i+1} marks every task criterion met but also requests required corrections. Check the criteria and correction together before relying on the judgement." for i,x in enumerate(readings) if x['review']['criteria'] and all(c['status']=='met' for c in x['review']['criteria']) and any(v['category']!='optional_clarity' for v in x['review']['issues'])]
    quality['consistency_flags']=flags
    if flags and quality['status'] in ('agreement','single_reading'):
        quality.update(status='needs_review',auto_completion_allowed=False)
    quality.update(readings=readings,duration_seconds=round(time.monotonic()-started,2),
                   first_feedback_seconds=first_elapsed,
                   limitation='Separate model calls can share the same mistakes. Agreement is not expert validation or verification of scientific evidence.')
    result.update(quality=quality,revision_id=p['revision_id'],source_hash=p['source_hash'],generation=generation,
                  reviewed_at=now(),validation='structure_and_spans_checked; content_is_tutor_proposal')
    return result
