"""Transparent card-to-lesson mapping; risk cues are questions, not research verdicts."""
import re

# Paper-specific patterns and node guidance belong to the private vault catalogue.
# Public code keeps only broadly applicable writing checks.
CHECKS=[
 ('benefit',r'\b(?:benefit|intervention|causal)\b','causality','Distinguish an observation, a recommendation and a demonstrated effect. State what the supplied evidence supports.'),
 ('absolute-gap',r'\b(?:no existing|no prior|none|lack(?:s|ing)?)\b','gap','Check the scope of an absence claim and consider relevant counterexamples.'),
 ('explanation',r'\b(?:explanation|causal)\b','interpretation','State what the explanation establishes and what still needs evidence.'),
]


def paper_checks(lab):
    from .assets import load
    return load(lab.root,'wise/writing_checks.json',{'checks':CHECKS,'focus':{}},lab.vault)

CATEGORIES={'scope':'scope','structure':'information-flow','terminology':'definitions','reasoning':'premises','evidence':'attribution','reference':'reference','grammar':'concision'}
SECTION={'I':['problem','premises','transitions'],'II':['compare-sources','gap','attribution'],'III':['method-rationale','conditions','definitions'],
         'IV':['definitions','method-rationale','quantities'],'V':['results','interpretation','quantities'],'VI':['limitations','recommendations','scope'],'AB':['abstract','concision','scope']}

def lesson(lab,id,reason,quote='',source=None):
    move=next(m for m in lab.teaching.advanced['moves'] if m['id']==id)
    return {'id':id,'title':move['title'],'reason':reason,'quote':quote,'source':source,
            'rule':move['rule'],'watch':move['watch'],'pattern':move['pattern'],'example':move['example'],
            'reading':move['reading'],'practice_key':move['practice_key'],
            'warmup_key':move['practice_key'].replace('-Q04','-Q01')}

def scan(text,checks=None):
    hits=[]
    for id,pattern,move,reason in (CHECKS if checks is None else checks):
        match=re.search(pattern,text,re.I)
        if match:
            start=max(text.rfind('\n',0,match.start())+1,text.rfind('. ',0,match.start())+2,0)
            end=text.find('\n',match.end())
            if end<0:end=min(len(text),match.end()+180)
            quote=text[start:min(end,start+700)].strip()
            if not quote:quote=match.group()
            hits.append({'check':id,'move':move,'reason':reason,'quote':quote})
    return hits

def card_support(lab,card_id):
    if card_id not in lab.paper.cards:raise ValueError('Source card not found.')
    card=lab.paper.cards[card_id];review=lab.teaching.review(card_id);text=card['latex']
    findings=scan(text,paper_checks(lab).get('checks',CHECKS))
    tips=[lesson(lab,h['move'],h['reason'],h['quote'],card_id) for h in findings]
    stale=review.get('stale',True)
    for f in review.get('findings',[]) if not stale else []:
        if f['quote'] and f['quote'] not in text:continue
        tips.append(lesson(lab,CATEGORIES.get(f['category'],'premises'),f['revision_task'],f['quote'],card_id))
    distinct={}
    for tip in tips:distinct.setdefault(tip['id'],tip)
    if not distinct:
        move=SECTION.get(card['section'],['information-flow'])[0]
        distinct[move]=lesson(lab,move,'No new cue was found by these checks. Confirm this passage’s argument job and preserve wording that already does it.',source=card_id)
    return {'card_id':card_id,'source_hash':card['source_hash'],'previous_review_stale':stale,
            'material_type':review.get('material_type'),'checks':findings,'tips':list(distinct.values())[:3],
            'scope':'Rule-based recheck against the new revision concerns plus existing AI reader findings; not a new human expert review or verification of the underlying publications.'}

def node_support(lab,node_id):
    n=lab.paper.node(node_id);selected=lab.paper.state()['nodes'].get(node_id,{}).get('source_ids',[])
    cards=selected or n['source_card_ids'];tips=[]
    focus=paper_checks(lab).get('focus',{})
    if node_id in focus:
        id,reason=focus[node_id];tips.append(lesson(lab,id,reason,source='New discussion / expanded crosswalk'))
    ordered=sorted(cards,key=lambda id:lab.teaching.reviews.get(id,{}).get('material_type')!='prose')
    prose=[id for id in ordered if lab.teaching.reviews.get(id,{}).get('material_type')=='prose']
    for id in (prose or ordered):
        if id in lab.paper.cards:tips.extend(card_support(lab,id)['tips'])
    for id in SECTION[n['section']]:tips.append(lesson(lab,id,'Useful for this target’s job: '+n['purpose'],source='Paragraph purpose'))
    unique={}
    for t in tips:unique.setdefault(t['id'],t)
    expanded=[]
    for doc in lab.revision.index():
        for c in doc.get('argument_cards',[]):
            ids=[c['card_id']]
            if re.fullmatch(r'II-B[1-6]',c['card_id']):ids+=['III-S'+c['card_id'][-1],'IV-M'+c['card_id'][-1]]
            if c['card_id'] in ('II-AS','II-A0'):ids+=['II-A7','II-GAP']
            if c['card_id'] in ('II-BS','II-B0'):ids+=['II-GAP','III-IN']
            if node_id in ids:expanded.append({**c,'document_id':doc['id']})
    return {'node_id':node_id,'tips':list(unique.values())[:3],'card_ids':cards,'expanded_cards':expanded,
            'basis':'Your selected cards' if selected else 'Suggested cards and this target’s purpose',
            'workflow':'Keep what already works. Choose one relevant drill only when a specific problem blocks the next edit. Return and apply the skill to one passage.'}

# Deterministic links from a validated reading into existing lessons. The tutor
# never invents exercise IDs, and a recommendation is not a new grading criterion.
REVIEW_MATCHES=[
    (r'causal|intervention|implementation|implement|benefit|effectiveness','causality'),
    (r'missing premise|connecting reason|logical|reasoning|does not follow|justify','premises'),
    (r'overclaim|certainty|scope|generalis|generaliz|quantifier','scope'),
    (r'wordiness|wordy|concis|redundan|repetit|inflated|in order to','concision'),
    (r'collocation|word choice|idiomatic|natural phrase','collocations'),
    (r'referent|pronoun|ambig|reference|\bactor\b','reference'),
    (r'transition|handover|next paragraph','transitions'),
    (r'passive|active voice|tense','voice'),
]

def review_lessons(lab,job_id,node_id):
    lab.paper.node(node_id)
    job=lab.job(job_id);result=job.get('result') or {}
    findings=sorted(result.get('issues',[]),key=lambda x:x.get('category')=='optional_clarity')
    findings += [{'category':'task_fit','explanation':c['explanation']} for c in result.get('criteria',[]) if c['status'] in ('partial','missing','uncertain')]
    tips=[];seen=set()
    for f in findings:
        text=' '.join(str(f.get(k,'')) for k in ('explanation','hint'))
        move=next((id for pattern,id in REVIEW_MATCHES if re.search(pattern,text,re.I)),None)
        if not move:move={'argument':'premises','meaning_question':'scope','usage':'collocations','optional_clarity':'concision'}.get(f.get('category'))
        if not move or move in seen:continue
        seen.add(move);tips.append(lesson(lab,move,text,f.get('quote',''),source='Feedback on saved attempt'))
        if len(tips)==2:break
    # Offer an optional response-planning lesson when a required criterion remains
    # unfulfilled but no more specific language pattern matched.
    if findings and not tips:tips=[lesson(lab,'information-flow','The feedback identifies an unmet task requirement. This lesson may help you plan the response; check its fit before starting.')]
    return {'revision_id':result.get('revision_id'),'node_id':node_id,'provisional':job['status']!='complete','tips':tips,
            'basis':'Suggested from this saved reading using the existing lesson catalogue. Choose one only if it helps; this is not an additional completion requirement.'}
