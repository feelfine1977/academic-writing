"""Bounded, source-checked retrieval from a paper's private Obsidian guidance.

No embeddings, network service, arbitrary paths, or write access are required.
A source match verifies the quoted record, not the supervisor's approval of an
interpretation or the scientific truth of a manuscript claim.
"""
import hashlib
import json
import re
from pathlib import Path

VERSION = 'grounding-1'
MAX_KNOWLEDGE = 400_000
BASES = [
    {'id':'author-question','instruction':'Answer the author’s current question about the submitted passage. Do not create additional task requirements.'},
    {'id':'current-move','instruction':'Assess only the selected writing move, if one is selected. Later moves are future work, not omissions in this passage.'},
    {'id':'text-clarity','instruction':'Identify a concrete reading or grammar difficulty in the actual prose. Repetition, sentence length and a missing connector word alone are not defects.'},
    {'id':'claim-fidelity','instruction':'Keep the author’s scope, uncertainty, technical meaning, citations and placeholders. Do not add facts or strengthen claims.'},
]


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def normalized(value):
    return ' '.join(str(value).split())


def tokens(value):
    return set(re.findall(r'[a-z][a-z-]{3,}',str(value).lower()))-{'that','this','with','from','have','what','which','text','writing','should','would','paragraph','section','about'}


def _read(path,limit):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ValueError('Guidance file is missing, linked outside its folder, or too large.')
    return path.read_text(encoding='utf-8')


def _source(root,relative):
    if not isinstance(relative,str) or len(relative)>250:
        raise ValueError('Use a relative source path within Section writing.')
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts or rel.suffix.lower() not in ('.txt','.md'):
        raise ValueError('Guidance sources must be local Markdown or text in Section writing.')
    path=root/rel
    if any(p.is_symlink() for p in [path,*path.parents] if p!=root.parent):
        raise ValueError('Linked guidance sources are not supported.')
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Source is outside the paper guidance folder.')
    return path


def _string(value,limit,label):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError('Invalid '+label+' in Tutor knowledge.md.')
    return value


def _ids(value):
    return isinstance(value,list) and len(value)<=40 and all(isinstance(s,str) and len(s)<=100 for s in value)


def load_knowledge(root):
    """Read the curated index afresh: Obsidian edits invalidate future retrieval."""
    root=Path(root);path=root/'Tutor knowledge.md'
    if not path.exists():return {'records':[],'notices':['No curated supervisor knowledge is installed for this paper. The tutor uses the current card and general writing guidance.'],'fingerprint':VERSION,'available':False}
    notices=[];records=[]
    try:
        raw=_read(path,MAX_KNOWLEDGE)
        block=re.search(r'^```json\s*\n(.*?)^```\s*$',raw,re.M|re.S)
        data=json.loads(block.group(1) if block else raw)
        if data.get('schema_version')!=1:raise ValueError('Unsupported tutor knowledge format.')
        sources=data.get('source_documents',[]);requirements=data.get('requirements',[])
        if not isinstance(sources,list) or len(sources)>50 or not isinstance(requirements,list) or len(requirements)>100:
            raise ValueError('Keep a paper knowledge set within 50 sources and 100 requirements.')
        source_map={};seen=set()
        for src in sources:
            ident=_string(src.get('id'),100,'source identity')
            if ident in source_map:raise ValueError('Duplicate guidance source identity.')
            content=_read(_source(root,src.get('path')),2_000_000)
            expected=src.get('sha256')
            source_map[ident]={**src,'content':content,'hash':digest(content),'changed':bool(expected and expected!=digest(content))}
        for row in requirements:
            ident=_string(row.get('id'),100,'requirement identity')
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident) or ident in seen or ident in {x['id'] for x in BASES}:
                raise ValueError('Each supervisor requirement needs a unique safe identity.')
            seen.add(ident)
            try:
                instruction=_string(row.get('instruction'),1800,'guidance')
                if 'not_applicable_when' in row:
                    exceptions=row['not_applicable_when']
                    if (not isinstance(exceptions,list) or len(exceptions)>20 or
                            any(not isinstance(value,str) or len(value)>1000 for value in exceptions)):
                        raise ValueError('not_applicable_when must be a list of up to 20 strings, each at most 1,000 characters.')
                if 'positive_example' in row:
                    example=row['positive_example']
                    if not isinstance(example,str) or len(example)>2400:
                        raise ValueError('positive_example must be a string of at most 2,400 characters.')
                stage=row.get('stage',[])
                if not _ids(stage) or not stage or not set(stage)<= {'connect','rewrite','polish'}:raise ValueError('Unknown writing stage.')
                scope=row.get('scope',{})
                if not isinstance(scope,dict) or not _ids(scope.get('moves',[])):raise ValueError('Invalid move scope.')
                if not _ids(row.get('supersedes',[])) or not _ids(row.get('conflicts_with',[])):raise ValueError('Invalid requirement relationships.')
                evidence=row.get('evidence',[])
                if not isinstance(evidence,list) or not 1<=len(evidence)<=8:raise ValueError('A guidance record needs source evidence.')
                refs=[]
                for e in evidence:
                    source=source_map.get(e.get('source_id'))
                    if not source:raise ValueError('Unknown source.')
                    quote=_string(e.get('quote'),2400,'source quotation')
                    if source['changed']:raise ValueError('The source changed since this guidance was indexed. Recheck its quotation and interpretation.')
                    if normalized(quote) not in normalized(source['content']):raise ValueError('The quoted words are not found in the source.')
                    paragraphs=e.get('paragraphs',[])
                    if not _ids(paragraphs):raise ValueError('Invalid paragraph locator.')
                    if paragraphs:
                        numbers=[]
                        for locator in paragraphs:
                            found=re.findall(r'P(\d{4})',locator)
                            if not found:raise ValueError('Invalid numbered transcript locator.')
                            if len(found)==2:numbers.extend(range(int(found[0]),int(found[1])+1))
                            else:numbers.extend(map(int,found))
                        chunks=re.findall(r'(?m)^P(\d{4})\s+(.*?)(?=^P\d{4}\s+|\Z)',source['content'],re.S)
                        located=' '.join(t for n,t in chunks if int(n) in numbers)
                        if normalized(quote) not in normalized(located):raise ValueError('The quotation does not match its numbered locator.')
                    refs.append({'source_id':source['id'],'title':source.get('title',source['id']),
                        'date':source.get('date',''),'path':source['path'],'hash':source['hash'],
                        'locator':', '.join(paragraphs) or e.get('locator',''),
                        'quote':quote,'speaker':e.get('speaker',''),'interpretation':e.get('interpretation','')})
                status=row.get('status','active')
                if status not in ('active','historical','qualified','superseded'):raise ValueError('Unknown guidance status.')
                records.append({**row,'id':ident,'instruction':instruction,'stage':stage,'scope':scope,'status':status,'evidence':refs})
            except (ValueError,TypeError,AttributeError) as error:
                notices.append(ident+': '+str(error)+' This record was excluded.')
        return {'records':records,'notices':notices,'fingerprint':digest(raw+''.join(s['hash'] for s in source_map.values())), 'available':True}
    except (ValueError,OSError,UnicodeError,TypeError,AttributeError) as error:
        return {'records':[],'notices':['Supervisor retrieval is unavailable: '+str(error)+' The tutor cannot claim to follow these records.'],'fingerprint':digest(str(error)),'available':False}


def move_context(steps,move_id):
    if not move_id:return {'selected':None,'before':None,'after':None,'notice':'No single outline idea selected. Assess the submitted passage and author question; the complete outline is not a checklist for this passage.'}
    index=next((i for i,s in enumerate(steps) if s['id']==move_id),None)
    if index is None:raise ValueError('The selected outline idea changed. Choose it again before requesting feedback.')
    def brief(s):
        value={k:s[k] for k in ('id','title','purpose','points','bridge_question','boundary') if k in s}
        if 'bridge_question' not in value and 'bridge' in s:
            value['bridge_question']=s['bridge']
        return value
    return {'selected':brief(steps[index]),'before':brief(steps[index-1]) if index else None,
        'after':brief(steps[index+1]) if index+1<len(steps) else None,
        'notice':'Before and after provide orientation only. Do not require their content in this passage.'}


def retrieve(root,section_id,section_title,stage,query='',move_id=None,max_records=5):
    knowledge=load_knowledge(root);eligible=[];historical=[]
    for row in knowledge['records']:
        scope=row['scope'];section=scope.get('section_id',scope.get('section','any'))
        if 'section_id' in scope:
            if section not in ('any','*',section_id):continue
        elif not isinstance(section,str) or section.casefold() not in ('any','*',section_title.casefold()):continue
        if stage not in row['stage']:continue
        if scope.get('moves') and move_id not in scope['moves']:continue
        if row['status'] in ('historical','superseded','qualified'):historical.append(row['id']);continue
        eligible.append(row)
    replaced={ident for r in eligible for ident in r.get('supersedes',[])}
    eligible=[r for r in eligible if r['id'] not in replaced]
    conflicts=[];eligible_ids={r['id'] for r in eligible}
    for row in eligible:
        for other in row.get('conflicts_with',[]):
            if other in eligible_ids and sorted([row['id'],other]) not in conflicts:conflicts.append(sorted([row['id'],other]))
    conflicting={i for pair in conflicts for i in pair}
    terms=tokens(query)
    def score(r):
        searchable=' '.join([r['instruction'],str(r.get('tags',[])),str(r.get('counterexample','')),str(r.get('positive_example',''))])
        return (len(terms & tokens(searchable))+ (5 if move_id and move_id in r['scope'].get('moves',[]) else 0), r.get('strength')=='explicit',r['id'])
    relevant=[r for r in eligible if r['id'] not in conflicting and
              (score(r)[0]>0 or (not terms and not r['scope'].get('moves') and r.get('default_for_stage') is True))]
    chosen=sorted(relevant,key=score,reverse=True)[:max_records]
    output=[];chars=0
    for row in chosen:
        item={k:row.get(k) for k in ('id','instruction','kind','strength','status','not_applicable_when','positive_example')}
        item['evidence']=[{k:e[k] for k in ('source_id','title','date','locator','quote','hash')} for e in row['evidence'][:1]]
        # Cut by record, never truncate a quotation into a misleading fragment.
        size=len(json.dumps(item,ensure_ascii=False))
        if chars+size>8500:continue
        output.append(item);chars+=size
    return {'version':VERSION,'fingerprint':knowledge['fingerprint'],'available':knowledge['available'],
        'requirements':output,'general_bases':BASES,'conflicts':conflicts,
        'notices':knowledge['notices']+(['Conflicting current guidance was excluded. Resolve the named records in Tutor knowledge.md before relying on it.'] if conflicts else []),
        'excluded_historical':sorted(set(historical)|replaced),'eligible_count':len(eligible),'retrieved_count':len(output),
        'notice':('Source quotations were matched to local records. Interpretations are proposed guidance, not supervisor approval. Other records are not automatically requirements for this passage.'
                  if output else 'No supervisor excerpt was supplied for this reading. Use the current author question and scoped card guidance; the tutor cannot claim alignment with unseen supervisor records.')}
