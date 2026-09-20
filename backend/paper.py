"""Paper assembly selects immutable writing or explicitly retained manuscript versions."""
import json
import re
from .storage import now, dump
from .workbench import Workbench

class Paper:
    def __init__(self, store, root, vault=None):
        self.store=store
        from .assets import load
        self.blueprint=load(root,'wise/blueprint.json',{'nodes':[],'sections':{},'books':[],'title':'My paper'},vault)
        self.writing_checks=load(root,'wise/writing_checks.json',{},vault)
        self.nodes={n['id']:n for n in self.blueprint['nodes']}
        self.cards={c['id']:c for c in load(root,'wise/cards.json',[],vault)}
        self.workbench=Workbench(self)

    def state(self):
        return self.store.setting('wise_paper_state',{'version':0,'nodes':{},'history':[]})

    def node(self, id):
        if id not in self.nodes:raise ValueError('Unknown paper target.')
        return self.nodes[id]

    def save(self, id, version, *, attempt_id=None, source_ids=None, confirmed=False, clear_selection=False):
        node=self.node(id)
        if clear_selection and attempt_id is not None:raise ValueError('Choose either a version or removal from the manuscript.')
        if attempt_id is not None:
            row=self.store.one('SELECT a.*,e.payload exercise_payload FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id WHERE a.id=?',(attempt_id,))
            exercise=json.loads(row['exercise_payload']) if row else {}
            if not row or exercise.get('paper_node_id')!=id or not exercise.get('paper_draft'):
                raise ValueError('Select a saved paragraph attempt belonging to this paper target.')
            if not confirmed:raise ValueError('Confirm that you have reviewed the paragraph before selecting it.')
            if json.loads(row['payload']).get('origin')!='learner':raise ValueError('Only learner attempts can be selected.')
        if source_ids is not None and (len(source_ids)>12 or len(set(source_ids))!=len(source_ids) or any(k not in self.cards for k in source_ids)):
            raise ValueError('Choose up to twelve distinct source cards from the archive.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute("SELECT payload FROM settings WHERE id='wise_paper_state'").fetchone()
            state=json.loads(r['payload']) if r else {'version':0,'nodes':{},'history':[]}
            if state['version']!=version:raise ValueError('The paper changed in another tab. Reload before selecting a version.')
            previous=state['nodes'].get(id,{})
            current={**previous,'updated':now()}
            if attempt_id is not None:
                current['attempt_id']=attempt_id
                current.pop('reuse_id',None)
            if clear_selection:
                current.pop('attempt_id',None)
                current.pop('reuse_id',None)
            if source_ids is not None:current['source_ids']=source_ids
            state['nodes'][id]=current
            state['history'].append({'node_id':id,'previous':previous,'current':current,'created':now()})
            state['version']+=1
            db.execute("INSERT INTO settings VALUES('wise_paper_state',?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(dump(state),))
        return self.summary()

    def summary(self):
        state=self.state();selected={}
        revision=self.store.setting('wise_revision',{})
        for id,p in state['nodes'].items():
            if p.get('attempt_id'):
                a=self.store.one('SELECT id,text,created,payload,session_id FROM attempts WHERE id=?',(p['attempt_id'],))
                if a:
                    a['payload']=json.loads(a['payload']);selected[id]=a
            elif p.get('reuse_id') in revision.get('reuse_versions',{}):
                selected[id]=revision['reuse_versions'][p['reuse_id']]
        practice=self.store.rows('SELECT s.exercise_id,count(a.id) attempts FROM sessions s LEFT JOIN attempts a ON a.session_id=s.id GROUP BY s.exercise_id')
        counts={r['exercise_id']:r['attempts'] for r in practice}
        drafts={}
        for a in self.store.rows('SELECT a.id,a.text,a.created,a.session_id,e.payload exercise FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id ORDER BY a.created,a.id'):
            exercise=json.loads(a.pop('exercise'))
            if exercise.get('paper_draft'):drafts[exercise['paper_node_id']]=a
        return {'blueprint':self.blueprint,'state':state,'selected':selected,'practice_counts':counts,
                'workbench':self.workbench.state(),'drafts':drafts,
                'revision_decisions':[d for d in revision.get('decisions',{}).values() if d['status'] not in ('resolved','superseded')],
                'checks':self.checks(selected),'selected_count':len(selected)}

    def checks(self, selected):
        issues=[]
        for id,a in selected.items():
            text=a['text'];node=self.nodes[id]
            for rule in self.writing_checks.get('terminology_checks',[]):
                if node['section'] not in rule.get('sections',[]):continue
                terms=re.findall(rule['pattern'],text,re.I)
                if terms:issues.append({'node_id':id,'kind':'terminology','message':rule['message']+' Terms: '+', '.join(sorted(set(terms)))})
            if re.search(r'\[(?:citation|source|evidence|TODO)[^\]]*\]',text,re.I):
                issues.append({'node_id':id,'kind':'evidence','message':'This selected version still contains an evidence or drafting placeholder.'})
            if re.search(r'\b(?:proves? causation|guarantees? savings|always improves|eliminates all)\b',text,re.I):
                issues.append({'node_id':id,'kind':'claim','message':'Check the scope and evidence for the strong claim. This phrase check cannot determine whether it is justified.'})
        return {'prompts':issues,'missing_targets':[n for n in self.nodes if n not in selected],
                'scope':'Mechanical review prompts and draft coverage only; not a scientific or English grade.'}

    def export(self):
        summary=self.summary();selected=summary['selected'];b=self.blueprint
        lines=['# WISE — my working manuscript','','Selected writing and explicitly retained manuscript passages. Empty targets remain visible; evidence and citations still need author review.','']
        order=['AB','I','II','III','IV','V','VI']
        for section in order:
            lines+=['## '+b['sections'][section],'']
            ids=self.workbench.state()['manuscript_orders'].get(section,[n['id'] for n in b['nodes'] if n['section']==section])
            for id in ids:
                n=self.nodes[id]
                a=selected.get(n['id'])
                lines += [a['text'] if a else f'[Draft needed: {n["id"]} — {n["title"]}]','']
        lines+=['---','## Version and source record','',f'Exported: {now()}','Argument source: '+b['overview_path'],'']
        for n in b['nodes']:
            if n['id'] not in selected:continue
            a=selected[n['id']];p=summary['state']['nodes'].get(n['id'],{})
            lines += [f'### {n["id"]}: {n["title"]}',f'Selected version: {a["id"]} ({a["created"]})',
                      'Origin: '+a['payload'].get('origin','learner'),
                      'Cards selected: '+(', '.join(p.get('source_ids',[])) or 'No explicit card selection recorded.'),
                      'Idea / evidence / support notes:',a['payload'].get('outline',''),'']
            if a.get('document_id'):
                doc=self.store.setting('wise_upload:'+a['document_id'],{})
                lines += ['Manuscript source: '+doc.get('filename',a['document_id']),
                          'Passages: '+', '.join(s['locator'] for s in doc.get('segments',[]) if s['id'] in a['segment_ids']),
                          'Source convention: '+('black text declared agreed' if a['source_agreed'] else 'agreement requires review'),
                          'Version treatment: '+('retained exactly as extracted; check PDF formatting' if a['mode']=='keep' else 'author adaptation; changed wording needs review'),'']
        return '\n'.join(lines)
