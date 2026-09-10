"""Portable, offline library for the dedicated iPad application."""
import json
from .storage import now
from .exercise_help import GLOSSARY

def library_package(lab):
    curriculum=lab.curriculum.snapshot()
    current=set(curriculum['exercise_status'])
    used={r['exercise_id'] for r in lab.store.rows('SELECT DISTINCT exercise_id FROM sessions')}
    exercises=[]
    for row in lab.store.rows('SELECT * FROM exercises'):
        if row['id'] not in current|used:continue
        e=lab.exercise(row);a=json.loads(row['answer']);support=lab.teaching.example(e['key']);example=support['example'];help=support['task_help']
        hints=[help['output'],*[h['title']+': '+h['text'] for h in help['hints']],
               *[t['term']+': '+t['meaning']+' Example: '+t['example'] for t in help['terms'][:2]]]
        supplement=lab.materials.get('exercises',{}).get(e['id'],{})
        model_answers=supplement.get('examples') or ([a['example']] if a.get('example') else [])
        exercises.append({'id':e['key'],'title':e['title'],'prompt':e['prompt'],'format':e['format'],
            'level':e['level'],'difficulty':e.get('difficulty_label',e['level']),
            'criteria':e['criteria'],'choices':e.get('choices',[]),'parts':e.get('parts',[]),'expected':a.get('accepted_value_sets',[a['expected_values']] if a.get('expected_values') else []),
            'explanation':a.get('explanation',''),'hints':hints,'modelAnswers':model_answers,
            'example':{k:example[k] for k in ['subject','task','answer','moves','transfer']}})
    courses=[{'id':c['id'],'title':c['title'],'goal':c['goal'],'moduleIds':[m['id'] for m in c['modules']]} for c in curriculum['courses']]
    modules=[{'id':m['id'],'title':m['title'],'goal':m['goal'],'courseId':m['course_id'],'exerciseIds':m['exercise_keys']} for m in curriculum['modules']]
    knowledge=[{'id':'wise-card:'+c['id'],'title':c['title'],'body':c['raw'],
                'kind':'WISE source card','provenance':'Imported source wording may be LLM-assisted; verify claims before use.',
                'sourcePath':c['archive_path']} for c in lab.paper.cards.values()]
    knowledge += [{'id':'writing-term:'+term,'title':term,'body':meaning+'\n\nExample: '+example,
                   'kind':'Writing vocabulary','provenance':'Original plain-language teaching explanation.',
                   'sourcePath':''} for term,meaning,example in GLOSSARY]
    seen=set()
    for row in lab.store.rows('SELECT * FROM sources ORDER BY rowid DESC'):
        if row['source_key'] in seen:continue
        seen.add(row['source_key']);s=json.loads(row['payload'])
        knowledge.append({'id':'source:'+row['id'],'title':s['title'],'body':s['raw'],
                          'kind':'Obsidian source','provenance':s['evidence_status'],'sourcePath':s['relative_path']})
    for m in lab.teaching.advanced['moves']:
        # A portable teaching note; do not depend on a Mac-only PDF URL.
        knowledge.append({'id':'phrase:'+m['id'],'title':m.get('title',m['id']),
                          'body':json.dumps(m,ensure_ascii=False,indent=2),'kind':'Academic phrasebook',
                          'provenance':'Curated teaching support; examples are not evidence for WISE.','sourcePath':''})
    plans=lab.paper.workbench.state()['plans']
    wise=[{'id':n['id'],'title':n['title'],'section':n['section_title'],'purpose':n['purpose'],
           'ideas':n['ideas'],'boundary':n['boundary'],'draftExerciseId':n['draft_exercise_key'],
           'plan':{k:v for k,v in plans.get(n['id'],{}).items() if isinstance(v,str)}} for n in lab.paper.blueprint['nodes']]
    attempts=[]
    for a in lab.store.rows('SELECT a.*,s.exercise_id FROM attempts a JOIN sessions s ON s.id=a.session_id ORDER BY a.created'):
        p=json.loads(a['payload'])
        attempts.append({'id':a['id'],'exerciseId':a['exercise_id'],'text':a['text'],
                         'outline':p.get('outline',''),'reason':p.get('reason',''),'created':a['created'],'origin':'Mac import'})
    reviews={id:{'reflection':r['reflection'],'created':r['reviewed_at']} for id,r in lab.store.setting('writing_completion_reviews',{}).items()}
    completions={k:{'status':s['status'],'attemptId':s.get('evidence_attempt_id') or ''} for k,s in curriculum['exercise_status'].items() if s['completed']}
    return {'schema':'awl.ipad.library.v1','created':now(),'title':'Urszula’s Academic Writing Lab',
            'exercises':exercises,'courses':courses,'modules':modules,'knowledge':knowledge,'wise':wise,
            'completions':completions,'initialAttempts':attempts,'initialReviews':reviews,
            'note':'Offline practice and self-review. Scientific claims and open prose still require judgement.'}
