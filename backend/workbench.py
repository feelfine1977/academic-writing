"""Author-owned argument planning; independent of source text and exercise completion."""
import json
from .storage import dump, now, uid

PLAN_FIELDS={'reader_before','contribution','bridge','handover','open_question','next_action','scratchpad'}
EVIDENCE_STATES={'open_question','linked_unassessed','supports','supports_narrower','does_not_support'}

class Workbench:
    def __init__(self,paper):
        self.paper=paper;self.store=paper.store

    def empty(self):
        return {'version':0,'plans':{},'orders':{},'manuscript_orders':{},'reverse_outlines':{},'evidence':{},'history':[]}

    def state(self):
        return self.store.setting('wise_workbench',self.empty())

    def change(self,version,kind,target,apply):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT payload FROM settings WHERE id='wise_workbench'").fetchone()
            state=json.loads(row['payload']) if row else self.empty()
            if state['version']!=version:raise ValueError('The argument plan changed in another tab. Reload to compare; your browser notes remain available.')
            previous=apply(state)
            state['history'].append({'kind':kind,'target':target,'previous':previous,'created':now()})
            state['version']+=1
            db.execute("INSERT INTO settings VALUES('wise_workbench',?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(dump(state),))
        return state

    def plan(self,id,version,fields):
        self.paper.node(id)
        if not set(fields)<=PLAN_FIELDS:raise ValueError('Unknown argument field.')
        if any(not isinstance(v,str) or len(v)>3000 for v in fields.values()):raise ValueError('Keep each planning note within 3,000 characters.')
        def apply(s):
            previous=s['plans'].get(id,{})
            s['plans'][id]={**previous,**fields,'updated':now()}
            return previous
        return self.change(version,'plan',id,apply)

    def order(self,section,version,ids):
        expected=[n['id'] for n in self.paper.nodes.values() if n['section']==section]
        if not expected or len(ids)!=len(expected) or set(ids)!=set(expected):raise ValueError('Include each target in this section exactly once.')
        def apply(s):
            previous=s['orders'].get(section,expected)
            s['orders'][section]=ids
            return previous
        return self.change(version,'planning_order',section,apply)

    def apply_order(self,section,version):
        if section not in self.paper.blueprint['sections']:raise ValueError('Unknown section.')
        def apply(s):
            previous=s['manuscript_orders'].get(section)
            s['manuscript_orders'][section]=s['orders'].get(section,[n['id'] for n in self.paper.nodes.values() if n['section']==section])
            return previous
        return self.change(version,'manuscript_order',section,apply)

    def reverse_outline(self,attempt_id,version,synopsis):
        row=self.store.one('SELECT a.id,e.payload exercise FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id WHERE a.id=?',(attempt_id,))
        exercise=json.loads(row['exercise']) if row else {}
        if not row:
            reused=self.store.setting('wise_revision',{}).get('reuse_versions',{}).get(attempt_id)
            if reused:exercise={'paper_draft':True,'paper_node_id':reused['node_id']}
        if not exercise.get('paper_draft'):raise ValueError('Choose a saved WISE paragraph version.')
        def apply(s):
            previous=s['reverse_outlines'].get(attempt_id)
            s['reverse_outlines'][attempt_id]={'synopsis':synopsis.strip(),'node_id':exercise['paper_node_id'],'updated':now()}
            return previous
        return self.change(version,'reverse_outline',attempt_id,apply)

    def evidence(self,version,record,id=None):
        nodes=record['node_ids']
        if not nodes or len(nodes)!=len(set(nodes)) or any(n not in self.paper.nodes for n in nodes):raise ValueError('Choose distinct WISE targets for this evidence question.')
        if not record['claim'].strip():raise ValueError('State the claim or question you want to examine.')
        status=record['status']
        if status not in EVIDENCE_STATES:raise ValueError('Choose an evidence status.')
        if status!='open_question' and not record['locator'].strip():raise ValueError('Record an exact source or artefact locator before marking evidence as linked.')
        if status in ('supports','supports_narrower','does_not_support') and not record['rationale'].strip():raise ValueError('Explain your assessment of what the evidence supports.')
        if status in ('supports','supports_narrower') and not record['boundary'].strip():raise ValueError('Record the scope or limit of this evidence.')
        key=id or uid()
        def apply(s):
            previous=s['evidence'].get(key)
            if id and not previous:raise ValueError('Evidence record not found.')
            s['evidence'][key]={**record,'id':key,'created':previous['created'] if previous else now(),'updated':now(),'assessment_by':'author'}
            return previous
        return self.change(version,'evidence',key,apply)

    def export(self):
        state=self.state();lines=['# WISE — argument planning notes','','Author planning notes and evidence assessments; separate from selected manuscript prose.','']
        for section,title in self.paper.blueprint['sections'].items():
            lines+=['## '+title,'']
            for id in state['orders'].get(section,[n['id'] for n in self.paper.nodes.values() if n['section']==section]):
                p=state['plans'].get(id,{})
                lines+=['### '+id+' · '+self.paper.nodes[id]['title'],'Argument job: '+self.paper.nodes[id]['purpose'],'']
                for field in ('reader_before','contribution','bridge','handover','open_question','next_action','scratchpad'):
                    if p.get(field):lines+=[field.replace('_',' ').title()+': '+p[field],'']
        lines+=['## Evidence questions and links','']
        for e in state['evidence'].values():
            lines+=['### '+e['claim'],'Targets: '+', '.join(e['node_ids']),'Author status: '+e['status'],'Locator: '+e['locator'],'Reason: '+e['rationale'],'Boundary: '+e['boundary'],'']
        lines+=['## Reverse outline of saved versions','']
        for attempt,r in state['reverse_outlines'].items():lines+=[r['node_id']+' · attempt '+attempt+': '+r['synopsis'],'']
        return '\n'.join(lines)
