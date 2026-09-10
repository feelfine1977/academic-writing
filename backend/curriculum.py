"""Practice completion derived from saved checks, tutor reviews and learner reviews."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
import hashlib
import json
from .storage import dump, now

ENGLISH_COURSES = [
    ('sentences','Accurate sentences','Control agreement, articles and verb forms.',[1,2,3,11]),
    ('vocabulary','Precise research vocabulary','Choose words, complements and quantities that preserve your meaning.',[4,8,9,12]),
    ('connections','Connect reasons and qualifications','Make contrast, conditions and inference explicit.',[5,6,7]),
    ('description','Describe research clearly','Use parallel operations, analytical units and bounded research sentences.',[10]),
]

def tutor_meets_criteria(job, attempt, exercise):
    """Count a validated review of this saved answer, never praise or an example alone."""
    if exercise['format'] in ('gap', 'ordering') or job['status'] != 'complete':
        return False
    if job['kind'] not in ('initial_hint', 'review_revision', 'argument_review'):
        return False
    try:
        result = json.loads(job['result'])
        payload = json.loads(job['payload'])
        expected = exercise.get('criteria', [])
        assessed = result['criteria']
        return bool(expected) and all((
            result.get('validation') == 'structure_and_spans_checked; content_is_tutor_proposal',
            result.get('revision_id') == attempt['id'] == payload.get('revision_id'),
            result.get('source_hash') == attempt['hash'] == payload.get('source_hash'),
            payload['input']['learner_text'] == attempt['text'],
            payload['input']['exercise']['key'] == exercise['key'],
            payload['input']['exercise']['criteria'] == expected,
            sorted(c['criterion_index'] for c in assessed) == list(range(len(expected))),
            all(c['status'] == 'met' and c.get('criterion') == expected[c['criterion_index']] for c in assessed),
            all(issue['category'] == 'optional_clarity' for issue in result['issues']),
            all(idea['status'] == 'present' for idea in result.get('idea_coverage', [])),
            not result.get('meaning_concerns'),
            not result.get('example'),
            not payload.get('review_mode') or result.get('quality',{}).get('auto_completion_allowed') is True,
        ))
    except (KeyError, IndexError, TypeError, ValueError):
        return False

class Curriculum:
    def __init__(self,lab):self.lab=lab

    def acknowledge(self,attempt_id,reflection):
        if len(reflection.strip())<10:raise ValueError('Write a short note about what you checked or changed (at least 10 characters).')
        row=self.lab.store.one('SELECT a.*,e.payload exercise FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id WHERE a.id=?',(attempt_id,))
        if not row:raise ValueError('Saved attempt not found.')
        if json.loads(row['exercise'])['format'] in ('gap','ordering'):raise ValueError('Closed exercises are completed by a correct checked answer.')
        # The learner attests a review, not that the prose is objectively correct.
        with self.lab.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT payload FROM settings WHERE id=?',('writing_completion_reviews',)).fetchone()
            records=json.loads(old['payload']) if old else {}
            records[attempt_id]={'attempt_id':attempt_id,'reviewed_at':records.get(attempt_id,{}).get('reviewed_at',now()),'reflection':reflection.strip(),'basis':'learner_criteria_review'}
            db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',('writing_completion_reviews',dump(records)))
        return records[attempt_id]

    def snapshot(self):
        store=self.lab.store
        latest={}
        for row in store.rows('SELECT * FROM packs'):
            p=json.loads(row['payload'])
            if p['pack_id'] not in latest or p['version']>latest[p['pack_id']]['version']:latest[p['pack_id']]={**p,'key':row['id']}
        current={p['key'] for p in latest.values()}
        exercises={r['id']:self.lab.exercise(r) for r in store.rows('SELECT * FROM exercises') if r['pack_id'] in current}
        attempts=store.rows('SELECT a.*,s.exercise_id FROM attempts a JOIN sessions s ON s.id=a.session_id ORDER BY a.created,a.id')
        by_exercise=defaultdict(list)
        for a in attempts:by_exercise[a['exercise_id']].append(a)
        checked={}
        support=defaultdict(list)
        events=store.rows('SELECT e.*,s.exercise_id FROM events e JOIN sessions s ON s.id=e.session_id ORDER BY e.created,e.rowid')
        for event in events:
            p=json.loads(event['payload'])
            if event['kind']=='check':checked[p.get('attempt_id')]=p
            if event['kind'] in ('hint_displayed','example_answer_displayed','cross_domain_example_viewed','offline_example_available'):support[event['exercise_id']].append(event)
        acknowledged=store.setting('writing_completion_reviews',{})
        reviews=defaultdict(list)
        for job in store.rows("SELECT * FROM jobs WHERE status='complete' AND kind IN ('initial_hint','review_revision','argument_review') ORDER BY created,id"):
            reviews[job['attempt_id']].append(job)
        statuses={}
        for key,e in exercises.items():
            aa=by_exercise[key];closed=e['format'] in ('gap','ordering')
            successful=[]
            for a in aa:
                if closed:
                    if checked.get(a['id'],{}).get('correct'):
                        successful.append({'attempt':a,'at':a['created'],'status':'correct','basis':'checked_answer','job_id':None})
                    continue
                if a['id'] in acknowledged:
                    successful.append({'attempt':a,'at':acknowledged[a['id']]['reviewed_at'],'status':'reviewed','basis':'learner_criteria_review','job_id':None})
                for job in reviews[a['id']]:
                    if tutor_meets_criteria(job,a,e):
                        result=json.loads(job['result'])
                        successful.append({'attempt':a,'at':result.get('reviewed_at') or job['created'],'status':'tutor_met','basis':'tutor_criteria_review','job_id':job['id']})
            successful.sort(key=lambda record:(record['at'],record['attempt']['id']))
            completion=successful[0] if successful else None
            first=completion['attempt'] if completion else None
            complete_at=completion['at'] if completion else None
            used_support=bool(first and any(ev['created']<=complete_at for ev in support[key]))
            statuses[key]={'key':key,'status':completion['status'] if completion else 'in_progress' if aa else 'not_started',
                           'completed':bool(first),'attempts':len(aa),'closed':closed,'completed_at':complete_at,
                           'evidence_attempt_id':first['id'] if first else None,'support_used':used_support,
                           'completion_basis':completion['basis'] if completion else None,'evidence_job_id':completion['job_id'] if completion else None,
                           'latest_attempt_id':aa[-1]['id'] if aa else None,'points':10 if first else 0}

        courses=[]
        def course(id,title,goal,kind):
            r={'id':id,'title':title,'goal':goal,'kind':kind,'modules':[]};courses.append(r);return r
        def module(c,id,title,keys,goal=''):
            keys=[k for k in keys if k in exercises]
            if not keys:return
            m={'id':id,'title':title,'goal':goal or c['goal'],'course_id':c['id'],'exercise_keys':keys,
               'total':len(keys),'completed':sum(statuses[k]['completed'] for k in keys)}
            m['is_complete']=m['completed']==m['total'];m['percent']=round(100*m['completed']/m['total'])
            m['next_key']=next((k for k in keys if not statuses[k]['completed']),None)
            m['skills']=sorted({s for k in keys for s in exercises[k]['skill_ids']})
            c['modules'].append(m)
        ordered=list(exercises)
        for spec in self.lab.teaching.advanced['courses']:
            c=course(spec['id'],spec['title'],spec['goal'],'advanced')
            for ms in spec['modules']:
                keys=[k for k in ordered if exercises[k].get('module_id')==ms['id']]
                if keys:
                    keys.sort(key=lambda k: exercises[k]['id'])
                    module(c,ms['id'],ms['title'],keys,ms['goal'])
                    c['modules'][-1].update(reading=ms['reading'],rule=ms['rule'])
        for id,title,goal,families in ENGLISH_COURSES:
            c=course('english-'+id,title,goal,'english')
            for f in families:
                keys=[k for k in ordered if exercises[k]['id'].startswith(f'AWL-EN-F{f:02}-')]
                if keys:module(c,f'english-F{f:02}',exercises[keys[0]]['family'],keys,exercises[keys[0]]['prompt'].split('\n')[0])
            if id=='description':module(c,'research-starter','From a sentence to a bounded paragraph',[k for k in ordered if exercises[k]['id'].startswith('AWL-PM-001-E')])
        topic_ids=list(dict.fromkeys(e['topic_id'] for e in exercises.values() if e['id'].startswith('AWL-TOPIC-')))
        for tid in topic_ids:
            es=[e for e in exercises.values() if e.get('topic_id')==tid and e['id'].startswith('AWL-TOPIC-')]
            c=course('topic-'+tid,es[0]['topic_title'],es[0].get('topic_goal','Apply writing skills to a research topic.'),'topic')
            for difficulty in ('foundation','developing','advanced'):
                module(c,'topic-'+tid+'-'+difficulty,difficulty.title(),[e['key'] for e in es if e['difficulty']==difficulty])
        for section,title in self.lab.paper.blueprint['sections'].items():
            c=course('wise-'+section,'WISE: '+title,'Build this section from checked ideas, targeted practice and your own prose.','paper')
            for n in self.lab.paper.blueprint['nodes']:
                if n['section']==section:module(c,'wise-'+n['id'],n['title'],[k for k in ordered if exercises[k].get('paper_node_id')==n['id']],n['purpose'])
        assigned={k for c in courses for m in c['modules'] for k in m['exercise_keys']}
        for p in latest.values():
            keys=[k for k in ordered if k not in assigned and exercises[k]['pack_key']==p['key']]
            if keys:
                c=course('custom-'+p['pack_id'],p['title'],'Practise from your confirmed source ideas.','custom')
                module(c,'custom-'+p['pack_id'],p['title'],keys)
        modules=[]
        for c in courses:
            c['total']=sum(m['total'] for m in c['modules']);c['completed']=sum(m['completed'] for m in c['modules'])
            c['is_complete']=bool(c['total']) and c['completed']==c['total'];c['percent']=round(100*c['completed']/c['total']) if c['total'] else 0
            c['next_module']=next((m['id'] for m in c['modules'] if not m['is_complete']),None)
            modules+=c['modules']
        lookup={k:m for m in modules for k in m['exercise_keys']}
        recent=next((a for a in reversed(attempts) if a['exercise_id'] in lookup),None)
        recommended=None
        if recent:
            m=lookup[recent['exercise_id']];c=next(c for c in courses if c['id']==m['course_id'])
            candidate=m if not m['is_complete'] else next((mm for mm in c['modules'] if not mm['is_complete']),None)
            if candidate:recommended={'module_id':candidate['id'],'course_id':c['id'],'exercise_key':candidate['next_key'],
                                      'title':candidate['title'],'reason':('Continue this module from your first unfinished activity.' if candidate==m else 'You completed '+m['title']+'. Continue with this module.')}
        if not recommended:
            candidate=next((m for m in modules if not m['is_complete']),None)
            if candidate:recommended={'module_id':candidate['id'],'course_id':candidate['course_id'],'exercise_key':candidate['next_key'],'title':candidate['title'],'reason':'Continue with the next unfinished module. You can choose another course at any time.'}
        skills=[]
        from .content import SKILLS
        for id,title in SKILLS.items():
            keys=[k for k,e in exercises.items() if id in e['skill_ids']]
            if keys:
                skills.append({'id':id,'title':title,'total':len(keys),'completed':sum(statuses[k]['completed'] for k in keys),
                               'correct':sum(statuses[k]['status']=='correct' for k in keys),'reviewed':sum(statuses[k]['status']=='reviewed' for k in keys),
                               'tutor_met':sum(statuses[k]['status']=='tutor_met' for k in keys),
                               'is_complete':all(statuses[k]['completed'] for k in keys),'exercise_keys':keys})
        completed=sum(s['completed'] for s in statuses.values());points=10*completed
        selected=len([n for n in self.lab.paper.state()['nodes'].values() if n.get('attempt_id')])
        days=sorted({a['created'][:10] for a in attempts})
        week_start=(datetime.now(timezone.utc)-timedelta(days=6)).date().isoformat()
        badges=[{'id':'first-step','title':'First step','earned':completed>=1,'description':'Complete one activity.'},
                {'id':'module','title':'A skill practised','earned':any(m['is_complete'] for m in modules),'description':'Complete a module.'},
                {'id':'course','title':'Course completed','earned':any(c['is_complete'] for c in courses),'description':'Complete a course.'},
                {'id':'reviser','title':'Thoughtful return','earned':sum(len(a)>1 for a in by_exercise.values())>=5,'description':'Return to revise five activities.'},
                {'id':'paper','title':'Into the paper','earned':selected>0,'description':'Select your own saved paragraph for WISE.'}]
        return {'version':1,'courses':courses,'modules':modules,'exercise_status':statuses,'skills':skills,'recommended':recommended,'badges':badges,
                'summary':{'completed':completed,'total':len(exercises),'percent':round(100*completed/len(exercises)) if exercises else 0,
                           'points':points,'correct':sum(s['status']=='correct' for s in statuses.values()),'reviewed':sum(s['status']=='reviewed' for s in statuses.values()),
                           'tutor_met':sum(s['status']=='tutor_met' for s in statuses.values()),
                           'modules_complete':sum(m['is_complete'] for m in modules),'courses_complete':sum(c['is_complete'] for c in courses),
                           'selected_paragraphs':selected,'writing_targets':len(self.lab.paper.nodes),'active_days_last_seven':sum(d>=week_start for d in days),
                           'support_used':sum(s['completed'] and s['support_used'] for s in statuses.values())},
                'completion_rule':'Closed tasks: a saved, correct checked answer. Open writing: a validated tutor review that meets every task criterion with no unresolved meaning, language or task issues, or your recorded criteria review and reflection. Optional style suggestions do not block completion. Ten points per completed activity, once; retries do not multiply points. Earlier successes remain visible after later practice.',
                'assessment_note':'This is practice evidence, not a CEFR level or a certified judgement of publication readiness. Supported practice counts; assistance is recorded separately.'}

    def certificate(self,kind,id):
        s=self.snapshot()
        items=s['modules'] if kind=='module' else s['courses'] if kind=='course' else s['skills'] if kind=='skill' else []
        item=next((x for x in items if x['id']==id),None)
        if not item or not item['is_complete']:raise ValueError('Complete every activity in this '+kind+' to unlock its certificate.')
        keys=item.get('exercise_keys') or [k for m in item['modules'] for k in m['exercise_keys']]
        evidence=[s['exercise_status'][k] for k in keys]
        when=max(e['completed_at'] for e in evidence)[:10]
        fingerprint=hashlib.sha256(dump(sorted((e['key'],e['evidence_attempt_id']) for e in evidence)).encode()).hexdigest()[:12].upper()
        count=len(keys);correct=sum(e['closed'] for e in evidence);reviewed=sum(e['status']=='reviewed' for e in evidence);tutor_met=sum(e['status']=='tutor_met' for e in evidence);assisted=sum(e['support_used'] for e in evidence)
        e=escape
        return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Practice completion — {e(item['title'])}</title><style>
        body{{font:18px/1.6 Georgia,serif;color:#26324c;background:#f5f6fb;margin:0;padding:40px}}main{{max-width:850px;margin:auto;background:white;border:3px double #6174b4;padding:55px;text-align:center}}h1{{font-size:38px}}h2{{font-size:30px;color:#354b97}}.label{{font:14px sans-serif;letter-spacing:2px}}.note{{font:14px/1.6 sans-serif;color:#566078}}hr{{border:0;border-top:1px solid #cbd2e6;margin:32px 0}}@media print{{body{{padding:0;background:white}}main{{border:3px double #6174b4;max-width:none;padding:35px}}}}
        </style><main><p class="label">ACADEMIC WRITING LAB · LOCAL PRACTICE RECORD</p><h1>Certificate of completion</h1><p>This records that</p><h2>{e(self.lab.store.setting('learner_name','The learner'))}</h2><p>completed the practice {e(kind)}</p><h2>{e(item['title'])}</h2><p>{count} activities · {count*10} practice points<br>Completed {e(when)}</p><hr><p class="note">Evidence: {correct} closed activities with a correct saved answer; {tutor_met} open activities meeting all tutor criteria; {reviewed} open activities with a saved learner criteria review. Support was recorded before completion in {assisted} activities. Repeated attempts earn no additional completion points.</p><p class="note">This is a self-study completion record issued by the local Writing Lab. It is not an accredited qualification, a language proficiency certificate or human expert approval of a manuscript.</p><p class="note">Record {fingerprint} · Curriculum v1<br>Open this file in a browser and use Print to save a PDF or paper copy.</p></main></html>'''
