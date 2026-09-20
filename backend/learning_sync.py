"""Exchange immutable saved learning records through ordinary Markdown files.

Live queues, device settings and the SQLite database remain local. Import uses
explicit tables and columns; duplicate identities with different content are errors.
"""
from pathlib import Path
import hashlib
import json
import threading
from datetime import datetime, timezone

from .storage import dump, digest
from .workspace import atomic_write
from scripts.create_paper_workspace import portable_name

COLUMNS={
 'packs':('id','payload'), 'exercises':('id','pack_id','payload','answer'),
 'sources':('id','source_key','hash','payload'),
 'attempts':('id','session_id','parent_id','text','hash','created','request_key','payload'),
 'events':('id','session_id','kind','created','payload'),
 'jobs':('id','attempt_id','kind','status','request_key','created','payload','result','error'),
 'observations':('id','session_id','skill','result','due','created','payload')}


class LearningSync:
    def __init__(self,workspace):
        self.workspace=workspace;self.store=workspace.lab.store;self.lock=threading.RLock()
        self.last={'state':'not_configured','message':'Choose a vault to share saved learning.'}
        self.known={};self.exported=set()
        self.destination=None

    @property
    def root(self):return self.workspace.safe(self.workspace.lab.vault/'06_Academic_Writing_Lab'/'Learning')

    def write(self,kind,title,payload,readable=''):
        payload={'schema':'awl.learning.v1','kind':kind,'data':payload}
        checksum=digest(dump(payload))
        if checksum in self.exported:return
        directory=self.root/kind;directory.mkdir(parents=True,exist_ok=True)
        # The title is for readers; a short content fingerprint disambiguates
        # immutable versions when two devices publish at the same time.
        path=directory/(portable_name(title)[:65]+' - '+checksum[:12]+'.md')
        text='# '+title+'\n\n'+readable+'\n\n<!-- awl-record '+checksum+' -->\n```json\n'+dump(payload)+'\n```\n'
        if not path.exists():atomic_write(self.workspace.safe(path),text,exclusive=True)
        elif path.read_text(encoding='utf-8')!=text:raise ValueError('A learning archive file changed: '+path.name+'. Keep it and restore the unchanged archive before syncing.')
        self.exported.add(checksum)

    def export(self):
        store=self.store
        from .coaching_archive import portable_question
        for p in store.rows('SELECT * FROM packs'):
            pack=json.loads(p['payload'])
            self.write('Knowledge',pack['title']+' · v'+str(pack['version']),{'pack':p,'exercises':store.rows('SELECT * FROM exercises WHERE pack_id=?',(p['id'],))},'Original exercise pack and answer records for use on your other computer.')
        for source in store.rows('SELECT * FROM sources'):
            p=json.loads(source['payload'])
            self.write('Research sources',p.get('title','Research source'),source,p.get('raw',p.get('brief','')))
        reviews=store.setting('writing_completion_reviews',{})
        for session in store.rows('SELECT s.*,e.payload exercise FROM sessions s JOIN exercises e ON e.id=s.exercise_id'):
            exercise=json.loads(session['exercise']);id=session['id']
            attempts=store.rows('SELECT * FROM attempts WHERE session_id=? ORDER BY created,id',(id,))
            events=store.rows('SELECT * FROM events WHERE session_id=? ORDER BY created,id',(id,))
            jobs=store.rows("SELECT j.* FROM jobs j JOIN attempts a ON a.id=j.attempt_id WHERE a.session_id=? AND j.status='complete' ORDER BY j.created,j.id",(id,))
            observations=store.rows('SELECT * FROM observations WHERE session_id=? ORDER BY created,id',(id,))
            if not attempts and not events:continue
            data={'session':{k:session[k] for k in ('id','exercise_id','payload')},'attempts':attempts,'events':events,'jobs':jobs,'observations':observations,
                  'completion_reviews':{a['id']:reviews[a['id']] for a in attempts if a['id'] in reviews}}
            readable=['Saved answers and visible tutor feedback. Each review belongs to its saved answer.','']
            for i,a in enumerate(attempts,1):
                p=json.loads(a['payload']);readable += ['## Attempt '+str(i)+' · '+a['created'],'',a['text'],'']
                if p.get('outline'):readable += ['### My outline','',p['outline'],'']
                if p.get('reason'):readable += ['### My revision reason','',p['reason'],'']
                for j in jobs:
                    if j['attempt_id']==a['id']:
                        readable += ['### Tutor feedback','', '```json',json.dumps(json.loads(j['result']),ensure_ascii=False,indent=2),'```','']
            self.write('Writing practice',exercise['title'],data,'\n'.join(readable))
        for row in store.rows("SELECT payload FROM settings WHERE id LIKE 'writing_question:%'"):
            job=portable_question(json.loads(row['payload']))
            readable='## My question\n\n'+job['question']+'\n\n## Text discussed\n\n'+job['text']+'\n\n## Tutor response\n\n'+json.dumps(job.get('result'),ensure_ascii=False,indent=2)
            self.write('Writing questions',job['question'][:90],job,readable)

    @staticmethod
    def insert(db,table,row):
        columns=COLUMNS[table]
        if not isinstance(row,dict) or set(row)!=set(columns):raise ValueError('Invalid learning record columns: '+table)
        prior=db.execute('SELECT * FROM '+table+' WHERE id=?',(row['id'],)).fetchone()
        if prior:
            if dict(prior)!=row:raise ValueError('Different saved records share one identity in '+table+'. Both archive files are kept; no existing record was replaced.')
            return
        if table=='attempts' and digest(row['text'])!=row['hash']:raise ValueError('A saved answer hash does not match.')
        if table=='jobs' and row['status']!='complete':raise ValueError('Only finished feedback can be imported.')
        db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',[row[k] for k in columns])

    def import_record(self,payload):
        data=payload['data'];kind=payload['kind']
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if kind=='Knowledge':
                from .content import validate_pack
                pack=json.loads(data['pack']['payload'])
                answers={'schema':'awl.answer-key.v1','pack_id':pack['pack_id'],'pack_version':pack['version'],'answers':[json.loads(e['answer']) for e in data['exercises']]}
                validate_pack(pack,answers)
                self.insert(db,'packs',data['pack'])
                for row in data['exercises']:self.insert(db,'exercises',row)
            elif kind=='Research sources':
                self.insert(db,'sources',data);p=json.loads(data['payload'])
                if not db.execute('SELECT id FROM source_search WHERE id=?',(data['id'],)).fetchone():db.execute('INSERT INTO source_search VALUES(?,?,?)',(data['id'],p['title'],p['brief']))
            elif kind=='Writing practice':
                s=data['session'];prior=db.execute('SELECT * FROM sessions WHERE id=?',(s['id'],)).fetchone()
                if prior and (prior['exercise_id']!=s['exercise_id'] or prior['payload']!=s['payload']):raise ValueError('Conflicting learning session identity.')
                if not prior:
                    db.execute('INSERT INTO sessions(id,exercise_id,updated,payload) VALUES(?,?,?,?)',(s['id'],s['exercise_id'],'',s['payload']))
                pending=list(data['attempts'])
                while pending:
                    ready=[a for a in pending if not a['parent_id'] or db.execute('SELECT id FROM attempts WHERE id=?',(a['parent_id'],)).fetchone()]
                    if not ready:raise ValueError('Waiting for an earlier saved attempt.')
                    for a in ready:self.insert(db,'attempts',a);pending.remove(a)
                for table in ('events','jobs','observations'):
                    for row in data[table]:self.insert(db,table,row)
                # Rebuild the resumable session from saved attempts, never from a
                # remote mutable draft or an unfinished feedback job.
                latest=db.execute('SELECT * FROM attempts WHERE session_id=? ORDER BY created DESC,id DESC LIMIT 1',(s['id'],)).fetchone()
                current=db.execute('SELECT * FROM sessions WHERE id=?',(s['id'],)).fetchone()
                if latest and latest['created']>current['updated']:
                    db.execute('UPDATE sessions SET text=?,outline=?,updated=?,version=version+1 WHERE id=?',(latest['text'],json.loads(latest['payload']).get('outline',''),latest['created'],s['id']))
                old=db.execute("SELECT payload FROM settings WHERE id='writing_completion_reviews'").fetchone()
                records=json.loads(old['payload']) if old else {}
                for id,review in data.get('completion_reviews',{}).items():
                    if id not in {a['id'] for a in data['attempts']} or review.get('basis')!='learner_criteria_review':raise ValueError('Invalid completion record.')
                    if id not in records:records[id]=review
                db.execute("INSERT INTO settings VALUES('writing_completion_reviews',?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(dump(records),))
            elif kind=='Writing questions':
                from .coaching_archive import import_question
                import_question(db,data)
            else:raise ValueError('Unknown learning record kind.')

    def sync(self):
        import re
        with self.lock:
            if not self.workspace.status()['enabled']:return self.last
            try:
                self.workspace.require_enabled()
                if self.destination!=str(self.root):
                    self.known={};self.exported=set();self.destination=str(self.root)
                # Always publish this device's saved work before reading remote
                # additions, so a failed import never strands local answers.
                self.export();issues=[];imported=0
                for kind in ('Knowledge','Research sources','Writing practice','Writing questions'):
                    for path in sorted((self.root/kind).glob('*.md')):
                        try:
                            path=self.workspace.safe(path);stat=path.stat();signature=(stat.st_mtime_ns,stat.st_size)
                            if self.known.get(str(path))==signature:continue
                            if stat.st_size>12_000_000:raise ValueError('Learning record exceeds the import size limit.')
                            text=path.read_text(encoding='utf-8')
                            matches=list(re.finditer(r'\n<!-- awl-record ([a-f0-9]{64}) -->\n```json\n(.+)\n```\n\Z',text,re.S))
                            if not matches:raise ValueError('Waiting for a complete learning record.')
                            m=matches[-1];record=json.loads(m.group(2))
                            if digest(dump(record))!=m.group(1) or record.get('schema')!='awl.learning.v1' or record.get('kind')!=kind:raise ValueError('Invalid learning record checksum or version.')
                            self.import_record(record);self.known[str(path)]=signature;self.exported.add(m.group(1));imported+=1
                        except Exception as error:issues.append(path.name+': '+str(error))
                self.last={'state':'attention' if issues else 'saved','imported':imported,'issues':issues[:20],
                           'at':datetime.now(timezone.utc).isoformat(),'message':'Saved learning is in your local vault. Remote Obsidian Sync delivery is not verified.'}
            except Exception as error:self.last={'state':'error','message':str(error)}
            return self.last
