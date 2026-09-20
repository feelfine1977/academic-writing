import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
from .storage import uid, now, dump, digest
from .content import public_exercise, import_pack, import_source, SKILLS
from . import providers, feedback_engine
from .feedback_context import ContextRepository, paper_context, task_context
from .paper import Paper
from .teaching import Teaching
from .curriculum import Curriculum

DEFAULT_PROFILE={'provider':'ollama','model':'','language':'en','local_confirmed':False,'review_mode':'careful','verifier_model':''}

def ordering_values(text,exercise):
    ids=[p['id'] for p in exercise.get('parts',[])]
    cleaned=text.strip().strip('*`').strip()
    compact=re.sub(r'[\s,/>→\-]+','',cleaned)
    if ids and all(len(id)==1 for id in ids) and compact and all(c.upper() in ids for c in compact):
        return list(compact.upper())
    return [x for x in re.split(r'[\s,/>→\-]+',cleaned) if x]

def assessment_input(exercise,text):
    """Attach a supplied stem without changing the learner's stored text."""
    stem=''
    if exercise['format']=='clause_completion':
        for line in exercise['prompt'].splitlines():
            if '…' in line and line.strip().endswith('…'):
                stem=line.split('…')[0].strip();break
    completed=text
    if stem and not text.strip().casefold().startswith(stem.casefold()):
        completed=stem+' '+text.strip()
    if exercise['format']=='ordering':
        ids=ordering_values(text,exercise);parts={p['id']:p['text'] for p in exercise.get('parts',[])}
        if ids and all(id in parts for id in ids):completed=' '.join(parts[id] for id in ids)
    return {'supplied_stem':stem,'assessment_text':completed}

class Lab:
    def __init__(self, store, root, vault):
        self.store=store;self.root=Path(root);self.vault=Path(vault)
        self.tasks={};self.semaphore=asyncio.Semaphore(1)
        from .assets import load
        self.materials=load(self.root,'tutor_materials.json',{'version':1,'exercises':{},'references':[]},self.vault)
        self.paper=Paper(store,self.root,self.vault)
        self.teaching=Teaching(self)
        self.curriculum=Curriculum(self)
        from .wise_revision import RevisionWorkspace
        self.revision=RevisionWorkspace(self)
        from .passage_finder import PassageFinder
        self.passage_finder=PassageFinder(self)
        from .word_help import WordHelp
        self.word_help=WordHelp(self)
        from .text_coach import TextCoach
        self.text_coach=TextCoach(self)

    def seed(self):
        p=self.root/'content/AWL-PM-001.exercises.json'
        a=self.root/'content/AWL-PM-001.answers.json'
        if p.is_file() and a.is_file():import_pack(self.store,json.loads(p.read_text()),json.loads(a.read_text()))
        bundled=list((self.root/'content/wise').glob('*.exercises.json'))+list((self.root/'content/practice').glob('*.exercises.json'))
        for pack_file in sorted(bundled):
            answer_file=pack_file.with_name(pack_file.name.replace('.exercises.json','.answers.json'))
            import_pack(self.store,json.loads(pack_file.read_text()),json.loads(answer_file.read_text()))
        from .writing_courses import packs
        for pack,answers in packs():import_pack(self.store,pack,answers)
        if not self.store.setting('initial_sources_seeded',False):
            config=self.root/'content/seed_sources.json'
            paths=json.loads(config.read_text()) if config.is_file() else []
            candidates=[]
            for path in [self.vault/p for p in paths]+candidates:
                try:import_source(self.store,path,self.vault)
                except (ValueError,OSError):pass
            self.store.set_setting('initial_sources_seeded',True)
        self.recheck_purpose_answers()

    @staticmethod
    def purpose_choice(e):
        return (e.get('format')=='gap' and e.get('assessment')=='deterministic_task_fit'
                and e.get('paper_node_id') and e.get('stage_index')==1
                and e.get('id','').startswith('AWL-WISE-') and e.get('id','').endswith('-T01'))

    def recheck_purpose_answers(self):
        # Re-evaluate the narrowly defined choice task, preserving attempts and original check events.
        for row in self.store.rows("SELECT a.*,e.payload exercise FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id WHERE e.id LIKE 'AWL-WISE-%-T01'"):
            if self.purpose_choice(json.loads(row['exercise'])):self.check(row)

    def exercise(self,row):
        result=public_exercise(row)
        supplement=self.materials.get('exercises',{}).get(result['id'],{})
        if supplement.get('learner_criteria'):
            result['criteria']=supplement['learner_criteria']
            result['teaching_supplement_version']=self.materials['version']
        if not result.get('criteria'):
            result['criteria']={'gap':['Choose the requested form for each gap.'],'ordering':['Use every supplied part exactly once.','Arrange the parts into a coherent sentence.']}.get(result['format'],['Preserve your intended meaning.','Write clear, grammatical prose.'])
        return result

    def get_session(self,id):
        row=self.store.one('SELECT * FROM sessions WHERE id=?',(id,))
        if not row:raise ValueError('Writing session not found.')
        row['payload']=json.loads(row['payload'])
        row['attempts']=self.store.rows('SELECT * FROM attempts WHERE session_id=? ORDER BY created',(id,))
        for a in row['attempts']:a['payload']=json.loads(a['payload'])
        row['events']=self.store.rows('SELECT * FROM events WHERE session_id=? ORDER BY created',(id,))
        for e in row['events']:e['payload']=json.loads(e['payload'])
        return row

    def session(self,exercise_id,fresh=False):
        exercise=self.store.one('SELECT * FROM exercises WHERE id=?',(exercise_id,))
        if not exercise:raise ValueError('Exercise not found.')
        row=self.store.one('SELECT id FROM sessions WHERE exercise_id=? ORDER BY updated DESC LIMIT 1',(exercise_id,))
        if row and not fresh:return self.get_session(row['id'])
        e=json.loads(exercise['payload']);id=uid()
        self.store.execute('INSERT INTO sessions(id,exercise_id,outline,updated,payload) VALUES(?,?,?,?,?)',
            (id,exercise_id,e.get('confirmed_outline',''),now(),dump({'origin':'learner','assistance_history':'recorded','fresh_attempt':fresh})))
        return self.get_session(id)

    def save_attempt(self, exercise_key, text, request_key, session_id=None, outline=None, reason='', values=None, base_version=None):
        if not text.strip():raise ValueError('Write an answer before submitting.')
        if len(text)>12000:raise ValueError('Choose a shorter passage (up to 12,000 characters).')
        existing=self.store.one('SELECT * FROM attempts WHERE request_key=?',(request_key,))
        if existing:
            session=self.store.one('SELECT * FROM sessions WHERE id=?',(existing['session_id'],))
            if existing['text']!=text or session['exercise_id']!=exercise_key:
                raise ValueError('This request ID already belongs to a different attempt.')
            return existing
        session=self.get_session(session_id) if session_id else self.session(exercise_key)
        if session['exercise_id']!=exercise_key:raise ValueError('The session belongs to another exercise.')
        id=uid();parent=session['attempts'][-1]['id'] if session['attempts'] else None
        final_outline=session['outline'] if outline is None else outline
        payload={'outline':final_outline,'reason':reason,'values':values,'origin':'learner','assistance_history':session['payload'].get('assistance_history','recorded')}
        with self.store.connect() as db:
            if base_version is not None:
                current=db.execute('SELECT version FROM sessions WHERE id=?',(session['id'],)).fetchone()['version']
                if current!=base_version:raise ValueError('This draft changed in another tab. Reload the saved session or keep your browser copy.')
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',(id,session['id'],parent,text,digest(text),now(),request_key,dump(payload)))
            db.execute('UPDATE sessions SET text=?,outline=?,version=version+1,updated=? WHERE id=?',(text,final_outline,now(),session['id']))
        return self.store.one('SELECT * FROM attempts WHERE id=?',(id,))

    def check(self,attempt):
        session=self.store.one('SELECT * FROM sessions WHERE id=?',(attempt['session_id'],))
        row=self.store.one('SELECT * FROM exercises WHERE id=?',(session['exercise_id'],))
        e=json.loads(row['payload']);a=json.loads(row['answer'])
        payload=json.loads(attempt['payload']) if isinstance(attempt['payload'],str) else attempt['payload']
        if e['format'] not in ('gap','ordering'):
            return {'checked':False,'message':'Your attempt is saved. Request tutor feedback or revise using the criteria.','criteria':e.get('criteria',[])}
        expected=a['expected_values'];actual=payload.get('values')
        if actual is None:
            actual=[x.strip() for x in attempt['text'].split('/')]
            if e['format']=='ordering':actual=ordering_values(attempt['text'],e)
        accepted=a.get('accepted_value_sets',[expected])
        correct=any([x.strip().casefold() for x in actual]==[x.casefold() for x in candidate] for candidate in accepted)
        if self.purpose_choice(e) and len(expected)==1:
            normal=lambda value:' '.join(value.strip().rstrip('.').split()).casefold()
            # Accept the exact option alone or the explicit sentence frame used in this activity.
            correct=correct or normal(attempt['text']) in {normal(expected[0]),normal('The paragraph should '+expected[0])}
        if e['format']=='ordering':
            sentence=' '.join(next(p['text'] for p in e['parts'] if p['id']==id) for id in expected)
            normal=lambda text:' '.join(text.strip().strip('*`').split()).casefold()
            correct=correct or normal(attempt['text'])==normal(sentence)
        result={'checked':True,'correct':correct,'message':'Correct for this exercise.' if correct else 'Your answer does not yet match the requested form. Try the hint and revise.',
                'explanation':a.get('explanation','') if correct else '', 'scope':'Exercise answer/function only; not a full grammar or scientific assessment.'}
        if e['format']=='ordering':
            result['message']='Correct. Your order forms the requested sentence.' if correct else 'Use the clickable parts, or type their letters in order. Spaces, commas, arrows, and letters without separators all work.'
            if e.get('paper_node_id'):
                result['message']='This matches the supplied planning outline.' if correct else 'Your order differs from the supplied planning outline. This is not a grammar judgement; use the hint or discuss a defensible alternative with the tutor.'
        already=self.store.one("SELECT payload FROM events WHERE session_id=? AND kind='check' AND json_extract(payload,'$.attempt_id')=? ORDER BY created DESC,rowid DESC LIMIT 1",(session['id'],attempt['id']))
        corrected=self.purpose_choice(e) and already and correct and not json.loads(already['payload']).get('correct')
        if not already or corrected:self.store.event(session['id'],'check',{'attempt_id':attempt['id'],**result,**({'recheck_reason':'Exact purpose option accepted inside its sentence frame.'} if corrected else {})})
        return result

    def assistance(self,session_id,kind):
        session=self.get_session(session_id)
        row=self.store.one('SELECT * FROM exercises WHERE id=?',(session['exercise_id'],))
        e=json.loads(row['payload']);a=json.loads(row['answer'])
        if kind!='hint' and len(session['attempts'])<2:
            raise ValueError('Examples unlock after two saved attempts. You can request a hint now.')
        self.store.event(session_id,'hint_displayed' if kind=='hint' else 'example_answer_displayed',{'before_first_attempt':not bool(session['attempts'])})
        if kind=='hint':
            help=self.teaching.example(session['exercise_id'])['task_help']
            return {'text':'\n\n'.join(h['title']+': '+h['text'] for h in help['hints']),
                    'hints':help['hints'],'terms':help['terms'],'steps':help['steps']}
        example=a.get('example') or (' / '.join(a.get('expected_values',[])))
        extra=self.materials.get('exercises',{}).get(e['id'],{})
        examples=extra.get('examples') or ([' / '.join(v) for v in a['accepted_value_sets']] if a.get('accepted_value_sets') else ([example] if example else []))
        if e['format']=='ordering':examples=[' '.join(next(p['text'] for p in e['parts'] if p['id']==id) for id in a['expected_values'])]
        return {'example':example or None,'examples':examples,'expected_values':a.get('expected_values'),
                'explanation':extra.get('explanation',a.get('explanation','')),'criteria':e.get('criteria',[]),
                'label':'Accepted answer for this task' if e['format'] in ('gap','ordering') else 'Examples of valid answers — other wording is welcome'}

    async def queue_review(self,attempt_id,kind,request_key):
        previous=self.store.one('SELECT * FROM jobs WHERE request_key=?',(request_key,))
        if previous:
            if previous['attempt_id']!=attempt_id or previous['kind']!=kind:raise ValueError('This request ID belongs to another review.')
            return self.job(previous['id'])
        if len(self.tasks)>=3:raise ValueError('The local tutor queue is full. Wait for a review to finish or cancel one.')
        attempt=self.store.one('SELECT * FROM attempts WHERE id=?',(attempt_id,))
        if not attempt:raise ValueError('Saved attempt not found.')
        profile=self.store.setting('profile',DEFAULT_PROFILE)
        if not profile.get('model'):raise ValueError('Select a local model in Settings first. Your attempt is saved.')
        if not profile.get('local_confirmed'):raise ValueError('Confirm local-only operation in Settings first.')
        session=self.get_session(attempt['session_id'])
        row=self.store.one('SELECT * FROM exercises WHERE id=?',(session['exercise_id'],))
        exercise=self.exercise(row)
        if kind=='show_example' and len(session['attempts'])<2:raise ValueError('Examples unlock after two saved attempts.')
        meta=json.loads(attempt['payload'])
        parent=self.store.one('SELECT text FROM attempts WHERE id=?',(attempt['parent_id'],)) if attempt['parent_id'] else None
        payload={'profile':profile,'review_mode':profile.get('review_mode','careful'),'source_hash':attempt['hash'],'revision_id':attempt_id,'session_id':session['id'],
                 'input':{'learner_text':attempt['text'],**task_context(self,exercise,meta.get('outline','')),
                          'previous_text':parent['text'] if parent else None,'learner_explanation':meta.get('reason',''),
                          **assessment_input(exercise,attempt['text'])}}
        help=self.teaching.example(exercise['key'])['task_help']
        payload['input']['learner_task_help']={'output':help['output'],'terms':[
            t for t in help['terms'] if t['term'] in ('actor','referent','diagnosis','concession','premise')]}
        payload['coaching_history']=self.text_coach.matches(exercise['key'],attempt['text'],attempt['created'])
        concerns=[json.loads(r['payload']) for r in self.store.rows("SELECT e.payload FROM events e JOIN jobs j ON json_extract(e.payload,'$.job_id')=j.id WHERE e.kind='feedback_disputed' AND j.attempt_id=? ORDER BY e.created DESC LIMIT 2",(attempt_id,))]
        if concerns:payload['input']['learner_questions']=[c['message'] for c in concerns]
        payload['guidance']=ContextRepository(self.root,self.store.path).select_guidance(payload['input'])
        if kind=='show_example':self.store.event(session['id'],'example_answer_requested',{'attempt_id':attempt_id})
        id=uid()
        self.store.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)',(id,attempt_id,kind,'queued',request_key,now(),dump(payload),None,None))
        return await self._start_job(id)

    async def _start_job(self,id):
        task=asyncio.create_task(self._run(id))
        self.tasks[id]=task
        task.add_done_callback(lambda _:self.tasks.pop(id,None))
        return self.job(id)

    async def _run(self,id):
        try:
            async with self.semaphore:
                row=self.store.one('SELECT * FROM jobs WHERE id=?',(id,))
                if not row or row['status']!='queued':return
                self.store.execute("UPDATE jobs SET status='running' WHERE id=?",(id,))
                p=json.loads(row['payload'])
                def progress(stage):
                    self.store.event(p['session_id'],'review_stage',{'job_id':id,'stage':stage,'label':feedback_engine.STAGES[stage]})
                def preview(result):
                    self.store.execute("UPDATE jobs SET result=? WHERE id=? AND status='running'",(dump(result),id))
                result=await feedback_engine.review(self.root,self.store,{**row,'payload':p},progress,preview)
                progress('complete')
                self.store.execute("UPDATE jobs SET status='complete',result=? WHERE id=? AND status='running'",(dump(result),id))
                if result.get('example'):
                    self.store.event(p['session_id'],'example_answer_generated',{'job_id':id})
        except asyncio.CancelledError:
            self.store.execute("UPDATE jobs SET status='cancelled',result=NULL,error='Request cancelled. Runtime-side generation may take a moment to stop.' WHERE id=? AND status IN ('queued','running')",(id,))
            raise
        except Exception as e:
            message=str(e) if isinstance(e,ValueError) else 'The local tutor could not complete the request. Check the runtime and try again.'
            self.store.execute("UPDATE jobs SET status='failed',error=? WHERE id=? AND status IN ('queued','running')",(message[:2000],id))

    def job(self,id):
        row=self.store.one('SELECT * FROM jobs WHERE id=?',(id,))
        if not row:raise ValueError('Review not found.')
        payload=json.loads(row.pop('payload'))
        row['review_mode']=payload.get('review_mode','legacy')
        stages=self.store.rows("SELECT created,payload FROM events WHERE kind='review_stage' AND json_extract(payload,'$.job_id')=? ORDER BY created",(id,))
        row['stages']=[{'created':s['created'],**json.loads(s['payload'])} for s in stages]
        row['stage']=row['stages'][-1] if stages else None
        row['result']=json.loads(row['result']) if row['result'] else None
        if row['result']:
            history=payload.get('coaching_history')
            if history is None:
                prior=payload.get('input',{});exercise_key=prior.get('exercise',{}).get('key')
                history=self.text_coach.matches(exercise_key,prior.get('learner_text',''),row['created']) if exercise_key else []
            row['result']['coaching_history']=history
        return row

    def activity(self):
        """Small navigation feed, including every unfinished review and recent history."""
        rows=self.store.rows("""SELECT j.id,j.status,j.created,j.result,a.id AS attempt_id,
            a.session_id,s.exercise_id,e.payload FROM jobs j
            JOIN attempts a ON a.id=j.attempt_id JOIN sessions s ON s.id=a.session_id
            JOIN exercises e ON e.id=s.exercise_id
            WHERE j.status IN ('queued','running') OR j.id IN
              (SELECT id FROM jobs ORDER BY created DESC LIMIT 20)
            ORDER BY j.created DESC""")
        for row in rows:
            e=json.loads(row.pop('payload'));r=json.loads(row.pop('result') or '{}')
            row.update(title=e['title'],preview_ready=bool(r) and row['status']=='running',paper_node_id=e.get('paper_node_id'))
        return {'reviews':rows}

    def cancel(self,id):
        row=self.job(id)
        if row['status'] in ('queued','running'):
            self.store.execute("UPDATE jobs SET status='cancelled',result=NULL,error='Application request cancelled; runtime cancellation is best effort.' WHERE id=?",(id,))
            if id in self.tasks:self.tasks[id].cancel()
        return self.job(id)

    async def close(self):
        for task in list(self.tasks.values()):task.cancel()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)

    def export_session(self,id):
        session=self.get_session(id)
        ex=self.store.one('SELECT payload FROM exercises WHERE id=?',(session['exercise_id'],))
        e=json.loads(ex['payload'])
        origin='legacy_declared_unknown_assistance' if session['payload'].get('assistance_history')=='unknown' else 'learner'
        lines=['---','type: writing-practice',f'session_id: {id}',f'text_origin: {origin}',f'exported: {now()}','---','',f"# {e['title']}",'',f"Exercise: {session['exercise_id']}",'','## Research idea outline','',session['outline'] or '(No separate outline supplied.)','']
        for i,a in enumerate(session['attempts']):
            lines += [f"## {'First attempt' if i==0 else f'Revision {i}'}",'',a['text'],'',f"Saved: {a['created']} · Hash: {a['hash']}",'']
            if a['payload'].get('reason'):lines+=['### My explanation','',a['payload']['reason'],'']
            for job in self.store.rows("SELECT * FROM jobs WHERE attempt_id=? AND status='complete'",(a['id'],)):
                r=json.loads(job['result']);lines+=['### Tutor feedback — proposed guidance','',r['summary'],'']
                if r.get('quality'):
                    q=r['quality']
                    lines += [f"Review status: {q.get('status','unknown')} · Mode: {q.get('mode','unknown')}",
                              'Automatic completion allowed by review checks: '+str(q.get('auto_completion_allowed',False)), '']
                    if q.get('disagreements'):
                        lines += ['Separate readings disagreed; inspect these judgements:', dump(q['disagreements']), '']
                    if not q.get('auto_completion_allowed'):
                        lines += ['This feedback does not establish activity completion. Review its uncertainty or required corrections.', '']
                if r.get('strengths'):
                    lines+=['#### What is already well written','']
                    for s in r['strengths']:lines += [f"- {s['quote']}: {s['explanation']}"]
                if r.get('criteria'):
                    lines+=['','#### Criterion coverage','']
                    for c in r['criteria']:lines += [f"- [{c['status']}] {c.get('criterion',c['criterion_index'])}: {c['explanation']}"]
                lines+=['','#### Revision priorities','']
                for issue in r['issues']:lines += [f"- {issue['category']}: {issue['quote']}",f"  {issue['explanation']} Hint: {issue['hint']}"]
                if r.get('meaning_concerns'):lines+=['','#### Scientific meaning to check','']+['- '+x for x in r['meaning_concerns']]
                lines+=['',f"Local model: {r.get('generation',{}).get('model','unknown')} · Prompt: {r.get('generation',{}).get('prompt_version','unknown')}",'']
                if r.get('example'):lines+=['','### Generated example — not learner prose','',r['example'],'']
        lines+=['## Assistance and learning events','']
        for event in session['events']:lines.append(f"- {event['created']}: {event['kind']} — {dump(event['payload'])}")
        lines+=['','## Exercise sources','']
        packrow=self.store.one('SELECT p.payload FROM packs p JOIN exercises e ON e.pack_id=p.id WHERE e.id=?',(session['exercise_id'],))
        for s in json.loads(packrow['payload']).get('sources',[]):
            if s['id'] in e.get('source_ids',[]):lines.append(f"- {s.get('title',s['id'])}: {s.get('path','')} (hash: {s.get('sha256','unknown')})")
        return '\n'.join(lines)+'\n'

    def import_legacy(self,data):
        if data.get('schemaVersion')!=1 or not isinstance(data.get('drafts'),dict):raise ValueError('Unsupported legacy backup. Expected schemaVersion 1 and drafts.')
        hash=digest(dump(data))
        old=self.store.one('SELECT payload FROM imports WHERE id=?',(hash,))
        if old:return {k:v for k,v in {**json.loads(old['payload']),'already_imported':True}.items() if k!='raw'}
        pack={'schema':'awl.exercise-pack.v1','pack_id':'LEGACY-'+hash[:10],'version':1,'title':'Earlier writing practice','sources':[],'exercises':[]}
        answers={'schema':'awl.answer-key.v1','pack_id':pack['pack_id'],'pack_version':1,'answers':[]}
        for key,d in data['drafts'].items():
            if not isinstance(d,dict):raise ValueError('Invalid legacy draft record.')
            for field in ('initial','text','revision'):
                if field in d and (not isinstance(d[field],str) or len(d[field])>100000):raise ValueError('Invalid legacy text.')
            id='LEGACY-'+digest(key)[:12]
            pack['exercises'].append({'id':id,'title':f'Earlier practice: {key}','format':'free_writing','level':'fresh_prose','skill_ids':['S06'],'source_ids':[],'prompt':'Continue your earlier writing attempt.','criteria':['Preserve the intended meaning.','Explain a change you made.'],'response_contract':{'type':'text','exact_match_allowed':False},'legacy_key':key})
            answers['answers'].append({'id':id,'explanation':'This is earlier open writing; no automatic grade was imported.'})
        if not pack['exercises']:return {'drafts':0,'already_imported':False}
        # Import occurs in a temporary store, then one atomic transaction merges the validated records.
        from tempfile import TemporaryDirectory
        from .storage import Store,TABLES
        with TemporaryDirectory() as tmp:
            temporary=Store(tmp);import_pack(temporary,pack,answers)
            for e,(key,d) in zip(pack['exercises'],data['drafts'].items()):
                session_id=uid();created=now()
                timestamp=d.get('firstSavedAt') or d.get('startedAt')
                if isinstance(timestamp,(int,float)):
                    try:created=datetime.fromtimestamp(timestamp/1000,timezone.utc).isoformat()
                    except (ValueError,OverflowError,OSError):pass
                text=d.get('text') or d.get('revision') or d.get('initial','')
                exercise_id=f"{pack['pack_id']}@1:{e['id']}"
                temporary.execute('INSERT INTO sessions(id,exercise_id,text,updated,payload) VALUES(?,?,?,?,?)',(session_id,exercise_id,text,created,dump({'legacy':d,'assistance_history':'unknown'})))
                initial=d.get('initial',text);first=uid()
                if initial:
                    temporary.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',(first,session_id,None,initial,digest(initial),created,'legacy-'+hash+'-'+e['id'],dump({'legacy':d,'assistance_history':'unknown','origin':'legacy_declared'})))
                    rev=d.get('revision','')
                    if rev and rev!=initial:temporary.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',(uid(),session_id,first,rev,digest(rev),created,'legacy-rev-'+hash+'-'+e['id'],dump({'assistance_history':'unknown','reason':d.get('reason','')})))
                temporary.event(session_id,'legacy_import',{'exposure':d.get('exposure','unknown'),'feedback_flag':d.get('feedback','unknown'),'not_a_verified_tutor_review':True})
            result={'drafts':len(data['drafts']),'already_imported':False,'pack_id':f"{pack['pack_id']}@1"}
            temporary.execute('INSERT INTO imports VALUES(?,?)',(hash,dump({**result,'raw':data})))
            snapshot=temporary.snapshot()
            with self.store.connect() as db:
                for table in ('packs','exercises','sessions','attempts','events','imports'):
                    for row in snapshot['tables'][table]:
                        columns=list(row)
                        db.execute(f'INSERT INTO {table} ({",".join(columns)}) VALUES({",".join("?" for _ in columns)})',[row[k] for k in columns])
            return result
