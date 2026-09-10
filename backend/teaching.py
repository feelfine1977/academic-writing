"""Versioned reading support; never a source of learner manuscript text."""
import json
from .exercise_help import help_for,teaching_example
from .storage import now, uid, dump

SOURCES = [
    {'title':'Manchester Academic Phrasebank: transitions', 'url':'https://www.phrasebank.manchester.ac.uk/signalling-transition/', 'use':'Signal how one part of an argument leads to the next.'},
    {'title':'Manchester Academic Phrasebank: cautious claims', 'url':'https://www.phrasebank.manchester.ac.uk/using-cautious-language/', 'use':'Match certainty and generalisation to the evidence.'},
    {'title':'Purdue OWL: paragraphs and paragraphing', 'url':'https://owl.purdue.edu/owl/general_writing/academic_writing/paragraphs_and_paragraphing/index.html', 'use':'Develop one connected purpose and make references between sentences clear.'},
    {'title':'Purdue OWL: conciseness', 'url':'https://owl.purdue.edu/owl/general_writing/academic_writing/conciseness/index.html', 'use':'Choose words that carry a specific meaning; remove avoidable padding.'},
]

PATTERNS = [
    ['Concession','Although + subject + verb, main clause.', 'Although the collection is large, evening access is restricted.', 'Do not add but to join these same two clauses. The clauses must express a real concession.'],
    ['Concession with a phrase','Despite + noun phrase / -ing form, main clause.', 'Despite its large collection, the library offers limited evening access.', 'Despite does not take a bare finite clause: despite it has is not this construction.'],
    ['Reason','Because + reason, consequence.', 'Because the bridge is closed, the bus takes a longer route.', 'State the reason. Do not infer a cause merely from two observations.'],
    ['Consequence','Premise; therefore, consequence.', 'The room holds only ten people; therefore, a group of twelve cannot all enter at once.', 'Therefore marks an inference; it does not create a missing premise. Then often means next in time.'],
    ['Contrast','Statement. However, contrasting statement.', 'The tour covers more exhibits. However, it leaves less time at each one.', 'However does not mean because. Use a full stop or semicolon between independent clauses.'],
    ['Comparison','X ..., whereas Y ...', 'The short tour covers paintings, whereas the longer tour also includes sculpture.', 'Compare on a common dimension; whereas alone does not explain why the difference matters.'],
    ['Condition','If X, then Y. / Y only if X.', 'If the museum is closed, the tour is cancelled. Entry is permitted only if a ticket is valid.', 'If gives a sufficient condition in this construction; only if gives a necessary condition. They are not interchangeable.'],
    ['Definition','Here, X refers to ...', 'Here, a visit refers to one entry by a person on a given day.', 'State the unit, scope and distinguishing features; a list of benefits is not a definition.'],
    ['Boundary','The evidence establishes X within Y; Z remains untested.', 'The survey describes preferences among respondents; actual evening attendance remains untested.', 'Hedging cannot repair a claim whose essential evidence is absent.'],
    ['Handover','This leaves [specific question]. The next paragraph addresses [needed step].', 'Demand for evening access leaves a staffing question. We next compare the hours two schedules require.', 'Write the actual connection. Avoid empty promises such as this will be discussed further.'],
]

RULES = [
    'Give each paragraph a job in the argument. A useful plan is claim → support → reason → boundary → handover, but the job may need fewer or more moves; there is no mandatory five-sentence formula.',
    'Start from the meaning you intend. Name who or what acts, what is measured, and what each pronoun refers to. Active and passive voice can both be appropriate.',
    'Keep a precise technical term stable after defining it. Repeating a needed term is clearer than rotating through approximate synonyms.',
    'Separate observations, interpretations, assumptions and tested effects. State the population, unit, conditions and denominator where they affect the claim.',
    'Use concrete verbs when they preserve the idea. Replace an abstract phrase only if the replacement says exactly what happened.',
    'Check articles, agreement and connector grammar after the argument makes sense. Sentence length alone is not a quality score, and no word list can determine whether a human wrote a sentence.',
    'Record a citation where a claim depends on earlier work. Check the source and its scope; a citation key or a fluent summary does not establish support.',
]




class Teaching:
    def __init__(self, lab):
        self.lab = lab
        from .assets import load
        self.support = load(lab.root,'teaching_support.json',vault=lab.vault)
        self.vocabulary = load(lab.root,'wise/vocabulary.json',{},lab.vault)
        self.advanced = load(lab.root,'advanced/learning.json',vault=lab.vault)
        self.support['exercise_examples'].update(self.advanced['exercise_examples'])
        self.support['examples'].update(self.advanced['examples'])
        self.plain_examples=load(lab.root,'plain_examples.json',{},lab.vault)
        self.reviews = {}
        self.review_roles = []
        for path in sorted((lab.root/'content/reviews').glob('review-*.json')):
            data = json.loads(path.read_text())
            self.review_roles.append(data['reviewer_role'])
            for r in data['cards']:
                if r['card_id'] in self.reviews:
                    raise ValueError('Duplicate card reader review: '+r['card_id'])
                self.reviews[r['card_id']] = {**r, 'reviewer_role':data['reviewer_role']}

    def example(self, exercise_key):
        row = self.lab.store.one('SELECT * FROM exercises WHERE id=?',(exercise_key,))
        if not row: raise ValueError('Exercise not found.')
        e = self.lab.exercise(row)
        e['hints']=json.loads(row['payload']).get('hints',[])
        template = self.support['exercise_examples'].get(exercise_key)
        if not template:
            # Old versions and user-created packs receive an explicitly marked
            # format illustration, not a claim of hand-reviewed task alignment.
            template = {'gap':'preposition','ordering':'order','clause_completion':'contrast',
                        'paragraph_from_ideas':'paragraph','free_writing':'transfer'}.get(e['format'],'bridge')
        node = next((n for n in self.lab.paper.blueprint['nodes'] if n['id']==e.get('paper_node_id')),None)
        example=teaching_example(e,self.support['examples'][template],self.plain_examples)
        help=help_for(e,example)
        return {'version':self.support['version'], 'scope':self.support['scope'],
                'exercise_key':exercise_key, 'tailored':exercise_key in self.support['exercise_examples'],
                'example':example,'task_help':help,
                'bridge_ideas':node['ideas'] if node and e.get('stage_index')==5 else [],
                'output_note':help['output']}

    def view_example(self, session_id):
        session = self.lab.get_session(session_id)
        r = self.example(session['exercise_id'])
        self.lab.store.event(session_id,'cross_domain_example_viewed',{'version':r['version'],'example_id':r['example']['id']})
        return r

    def toolbox(self, node_id=None):
        node = next((n for n in self.lab.paper.blueprint['nodes'] if n['id']==node_id),None)
        if node_id and not node: raise ValueError('Writing target not found.')
        return {'version':1, 'patterns':PATTERNS, 'rules':RULES, 'sources':SOURCES,
                'vocabulary':self.vocabulary.get(node['section'],[]) if node else sum(self.vocabulary.values(),[]),
                'reader_question':('Why must a process owner decide which issues to investigate first?' if node_id=='I-01' else
                                   f'What does the reader need to understand about {node["title"].lower()} before moving on?' if node else ''),
                'plan':['State the point this paragraph must establish.','Give the evidence, definition or premise that supports it.',
                        'Explain why that support leads to the point; name missing assumptions.',
                        'State a material limit or exception, if relevant.','Leave the next paragraph a specific question to answer.']}

    def phrasebook(self, node_id=None):
        node = self.lab.paper.nodes.get(node_id) if node_id else None
        if node_id and not node:
            raise ValueError('Writing target not found.')
        moves = [dict(m, suggested=bool(node and node['section'] in m['sections']))
                 for m in self.advanced['moves']]
        return {'version': self.advanced['version'], 'node_id': node_id,
                'purpose': node['purpose'] if node else None,
                'boundary': node['boundary'] if node else None,
                'moves': moves, 'books': self.advanced['books'],
                'note': 'Original teaching patterns informed by the supplied books, including Academic Phrasebank. Choose the meaning first; these patterns do not supply evidence or write your manuscript.'}

    def review(self, card_id):
        card = self.lab.paper.cards.get(card_id)
        if not card: raise ValueError('Source card not found.')
        record = self.reviews.get(card_id)
        if not record: return {'card_id':card_id, 'available':False}
        return {**record, 'available':True, 'stale':record['source_hash']!=card['source_hash'],
                'title':card['title'], 'section':card['section'], 'in_paper':card['in_paper']}

    def review_index(self):
        cards=[]
        for c in self.lab.paper.cards.values():
            r=self.review(c['id'])
            cards.append({k:r.get(k) for k in ('card_id','title','section','in_paper','available','stale','verdict','material_type','intended_meaning','reader_question')} |
                         {'finding_count':len(r.get('findings',[])), 'major_count':sum(f['severity']=='major' for f in r.get('findings',[]))})
        return {'version':1, 'date':'2026-09-09', 'scope':'AI reader reviews of the 375 imported WISE cards, read in section context against the argument overview. Includes alternatives and non-prose material. Not human expert consultation, citation verification or an assessment of your unaided English.',
                'reviewers':self.review_roles, 'cards':cards,
                'reviewed':sum(c['available'] for c in cards),'total':len(cards)}

    def report(self, context, quote, comment):
        if not comment.strip(): raise ValueError('Describe what is unclear before saving.')
        record = {'id':uid(),'created':now(),'context':context,'quote':quote.strip(),'comment':comment.strip(),'status':'open'}
        # BEGIN IMMEDIATE prevents concurrent tabs from losing one another's flags.
        with self.lab.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM settings WHERE id=?',('wording_flags',)).fetchone()
            reports=json.loads(row['payload']) if row else []
            reports.append(record)
            db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',('wording_flags',dump(reports)))
        return record

    def resolve_report(self, record_id, status):
        with self.lab.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM settings WHERE id=?',('wording_flags',)).fetchone()
            reports=json.loads(row['payload']) if row else []
            record=next((r for r in reports if r['id']==record_id),None)
            if not record: raise ValueError('Comment not found.')
            record['status']=status
            db.execute('UPDATE settings SET payload=? WHERE id=?',(dump(reports),'wording_flags'))
        return record
