from pathlib import Path
import json
import re
import yaml
from .storage import dump, digest, uid, now

SKILLS = {'S01':'Reference & agreement','S02':'Academic collocations','S03':'Contrast & concession','S04':'Reasons & implications','S05':'Definitions & precision','S06':'Paragraph arguments','S07':'Methods & comparisons','S08':'Results & uncertainty','S09':'Literature synthesis','S10':'Paper coherence'}
FORMATS = {'gap','ordering','clause_completion','keywords_to_sentence','outline_to_sentences','paragraph_from_ideas','free_writing'}

def validate_pack(pack, answers):
    if pack.get('schema')!='awl.exercise-pack.v1' or answers.get('schema')!='awl.answer-key.v1':
        raise ValueError('Use an AWL exercise pack and its separate answer key.')
    if pack.get('pack_id')!=answers.get('pack_id') or pack.get('version')!=answers.get('pack_version'):
        raise ValueError('The pack and answer-key versions do not match.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',pack.get('pack_id','')) or not isinstance(pack.get('version'),int) or pack['version']<1:
        raise ValueError('Invalid pack ID or version.')
    items=pack.get('exercises',[])
    if not 1<=len(items)<=500:
        raise ValueError('A pack must contain 1–500 exercises.')
    if len({e.get('id') for e in items})!=len(items):
        raise ValueError('Exercise IDs must be unique.')
    keys={a['id']:a for a in answers.get('answers',[])}
    if set(keys)!={e['id'] for e in items} or len(keys)!=len(answers.get('answers',[])):
        raise ValueError('Every exercise needs exactly one answer/rubric record.')
    sources={s['id'] for s in pack.get('sources',[])}
    for e in items:
        if e.get('format') not in FORMATS or not isinstance(e.get('prompt'),str) or not e['prompt'].strip():
            raise ValueError('Unknown exercise format or empty prompt.')
        if len(e['prompt'])>20000 or not set(e.get('source_ids',[]))<=sources or not set(e.get('skill_ids',[]))<=set(SKILLS):
            raise ValueError('Invalid source, skill, or prompt size.')
        a=keys[e['id']]
        expected=a.get('expected_values',[])
        if e['format']=='gap':
            if not expected or any(v not in e.get('choices',[]) for v in expected):
                raise ValueError('Gap answers must occur in the word bank.')
            if e.get('response_contract',{}).get('value_count')!=len(expected):
                raise ValueError('Gap count does not match answer key.')
            for alternative in a.get('accepted_value_sets',[expected]):
                if len(alternative)!=len(expected) or any(v not in e.get('choices',[]) for v in alternative):
                    raise ValueError('Accepted alternatives must fit the gap count and word bank.')
        elif e['format']=='ordering':
            part_ids=[p['id'] for p in e.get('parts',[])]
            if len(set(part_ids))!=len(part_ids) or sorted(expected)!=sorted(part_ids):
                raise ValueError('Ordering answers must be a permutation of the supplied parts.')
        elif e.get('response_contract',{}).get('exact_match_allowed'):
            raise ValueError('Open writing cannot be graded by exact answer matching.')
    return keys

def import_pack(store, pack, answers):
    keys=validate_pack(pack,answers)
    pack_key=f"{pack['pack_id']}@{pack['version']}"
    with store.connect() as db:
        existing=db.execute('SELECT payload FROM packs WHERE id=?',(pack_key,)).fetchone()
        if existing:
            old=json.loads(existing['payload'])
            if old!=pack:
                raise ValueError('This pack version already exists with different content. Increase its version.')
            for e in pack['exercises']:
                row=db.execute('SELECT answer FROM exercises WHERE id=?',(f"{pack_key}:{e['id']}",)).fetchone()
                if not row or json.loads(row['answer'])!=keys[e['id']]:
                    raise ValueError('Answer key changed. Import it as a new pack version.')
            return {'pack_id':pack_key,'count':len(keys),'already_imported':True}
        db.execute('INSERT INTO packs VALUES(?,?)',(pack_key,dump(pack)))
        for e in pack['exercises']:
            db.execute('INSERT INTO exercises VALUES(?,?,?,?)',(f"{pack_key}:{e['id']}",pack_key,dump(e),dump(keys[e['id']])))
    return {'pack_id':pack_key,'count':len(keys),'already_imported':False}

def public_exercise(row):
    p=json.loads(row['payload'])
    p.pop('hints',None)
    p['key']=row['id'];p['pack_key']=row['pack_id']
    p.setdefault('difficulty',{'guided':'foundation','open_sentence':'developing','short_argument':'developing','fresh_prose':'advanced','transfer':'advanced'}.get(p.get('level'),'developing'))
    p['difficulty_label']={'foundation':'Foundation','developing':'Developing','advanced':'Advanced','stretch':'Stretch'}.get(p['difficulty'],p['difficulty'])
    if 'topic_id' not in p:
        topic=('wise','WISE paper argument') if p.get('paper_node_id') else ('english','Academic English patterns') if p['id'].startswith('AWL-EN-') else ('research','Research writing basics')
        p['topic_id'],p['topic_title']=topic
    return p

def safe_source(path, root):
    root=Path(root).resolve()
    path=Path(path)
    if not path.is_absolute():path=root/path
    actual=path.resolve()
    if not actual.is_relative_to(root) or actual.suffix.lower() not in {'.md','.txt','.tex'}:
        raise ValueError('Choose a Markdown, text, or TeX file inside the configured vault.')
    rel=actual.relative_to(root)
    if any(x.startswith('.') or x in {'90_Archive','90_Previous','06_Academic_Writing_Lab','_tools'} for x in rel.parts) or '.excalidraw.' in actual.name:
        raise ValueError('Archived, generated output, drawing and private configuration files are excluded.')
    if not actual.is_file() or actual.stat().st_size>300000:
        raise ValueError('Source file is missing or larger than 300 KB.')
    return actual

def parse_source(path, root):
    path=safe_source(path,root)
    raw=path.read_text(encoding='utf-8')
    meta={};body=raw
    if raw.startswith('---\n'):
        parts=raw.split('---',2)
        if len(parts)==3:
            loaded=yaml.safe_load(parts[1])
            meta=loaded if isinstance(loaded,dict) else {}
            body=parts[2]
    title=re.search(r'^#\s+(.+)',body,re.M)
    title=str(meta.get('title') or (title.group(1) if title else path.stem))
    # Store the original separately; retrieval excludes proposed prose and answer-like sections.
    usable=re.split(r'^##?\s+(?:Suggested LaTeX|LaTeX|Manuscript provenance|Revision checks|References|Bibliography)\b',body,flags=re.M|re.I)[0]
    lines=[]
    for line in usable.splitlines():
        if re.match(r'^\s*(?:```|>\s*\[!|---)',line):continue
        line=re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]',r'\2',line)
        line=re.sub(r'\[\[([^\]]+)\]\]',r'\1',line)
        line=re.sub(r'^\s*[>#]+\s*','',line).strip()
        if line:lines.append(line)
    brief='\n'.join(lines)[:12000]
    collection=str(path.relative_to(Path(root).resolve()).parent)
    return {'title':title,'path':str(path),'relative_path':str(path.relative_to(Path(root).resolve())),
            'collection':collection,'original_id':str(meta.get('id') or meta.get('card_id') or path.stem),
            'hash':digest(raw),'text_origin':'unknown','argument_provenance':str(meta.get('argument_provenance','unspecified')),
            'evidence_status':'unverified_source_material','metadata':json.loads(json.dumps(meta,default=str)),
            'raw':raw,'brief':brief,'created':now(),'file_type':path.suffix.lower()}

def import_source(store,path,root):
    p=parse_source(path,root)
    key=p['path']
    existing=store.one('SELECT id FROM sources WHERE source_key=? AND hash=?',(key,p['hash']))
    if existing:return existing['id']
    id=uid()
    with store.connect() as db:
        db.execute('INSERT INTO sources VALUES(?,?,?,?)',(id,key,p['hash'],dump(p)))
        db.execute('INSERT INTO source_search VALUES(?,?,?)',(id,p['title'],p['brief']))
    return id

def build_pack(title, outline, source_rows, skill):
    """Deterministic task scaffolds. Supplied ideas stay explicit; no invented research results."""
    if skill!='S03':raise ValueError('The current pack builder supports contrast and concession (S03).')
    pack_id='AWL-'+uid()[:8].upper()
    sources=[{'id':r['id'],'title':json.loads(r['payload'])['title'],'path':json.loads(r['payload'])['path'],'sha256':r['hash']} for r in source_rows]
    brief='Confirmed research ideas (content supplied by you):\n'+outline
    prompts=[
        ('guided','gap','Warm up: agreement','These findings ___ further interpretation.\nChoose: require / requires.\nThis sentence is a constructed grammar example, not a claim about your source.', ['S01']),
        ('open_sentence','clause_completion','Build a contrast','Write a sentence beginning with Although. Use one confirmed idea and its actual limitation. If no limitation is given, ask what it is instead of inventing one.\n\n'+brief,[skill]),
        ('open_sentence','keywords_to_sentence','Choose your own construction','Express the same confirmed contrast with a different construction, such as despite or however. Change the sentence structure as needed.\n\n'+brief,[skill]),
        ('short_argument','outline_to_sentences','Connect the reasoning','Write two or three sentences connecting an observation, its interpretation and a qualification from the outline. Make each inferential step explicit.\n\n'+brief,['S04','S06']),
        ('fresh_prose','paragraph_from_ideas','Write a fresh paragraph','Write 80–150 words from the confirmed ideas. Use your own sentence structure. Preserve conditions and uncertainty. Do not imitate the source prose.\n\n'+brief,['S06',skill]),
    ]
    exercises=[];answers=[]
    for i,(level,fmt,name,prompt,skills) in enumerate(prompts,1):
        id=f'{pack_id}-E{i:02}'
        closed=fmt=='gap'
        exercises.append({'id':id,'version':1,'title':name,'format':fmt,'skill_ids':list(dict.fromkeys(skills)),
            'level':level,'prompt':prompt,'source_ids':[s['id'] for s in sources],'confirmed_outline':outline,
            'choices':['require','requires'] if closed else [],'parts':[],
            'hints':[{'level':1,'text':'Identify the subject and its number.' if closed else 'Identify the claim, its supporting reason, and its limitation before changing the sentence.'}],
            'criteria':[] if closed else ['Preserve the confirmed ideas and their limits.','Keep the logical connection clear.','Use a grammatical construction; alternative wording is welcome.'],
            'response_contract':{'type':'ordered_gap_values' if closed else 'text','exact_match_allowed':closed,**({'value_count':1} if closed else {})},
            'assessment':'deterministic_task_fit' if closed else 'criterion_based_feedback'})
        answers.append({'id':id,**({'expected_values':['require']} if closed else {'example':None}),
            'explanation':'The plural subject takes require.' if closed else 'Use the criteria and your confirmed ideas; there is no single required sentence.'})
    pack={'schema':'awl.exercise-pack.v1','pack_id':pack_id,'version':1,'title':title,'created':now(),'origin':'template_scaffold_with_learner_confirmed_ideas','independent_content_review':'pending','sources':sources,'exercises':exercises}
    key={'schema':'awl.answer-key.v1','pack_id':pack_id,'pack_version':1,'answers':answers}
    return pack,key
