"""Intentional writing checkpoints, stored as private Markdown in the paper vault.

These are the writer's records, not authorship detection or a proficiency score.
Autosaves and tutor rewrites do not create practice credit.
"""
import json
import re
import uuid

from .storage import now
from .workspace import Conflict, atomic_write, sha


def canonical_prose(text):
    return ' '.join(re.findall(r'\w+', text.casefold(), re.UNICODE))


def practice_root(ws, paper_id, section_id):
    return ws.safe(ws.locate(paper_id).parent/'Section writing'/'Practice'/sha(section_id)[:20])


def intentional_practice(ws, paper_id, section_id):
    """Read immutable records on any device; reject malformed/foreign records."""
    ws.card(paper_id, section_id)
    records=[]
    for path in sorted(practice_root(ws,paper_id,section_id).glob('*.md')):
        ws.safe(path)
        try:
            if path.stat().st_size>350000:continue
            raw=path.read_text(encoding='utf-8')
            # The first fenced block is the canonical record. Visible prose below
            # is a convenience for reading in Obsidian, not a second data source.
            record=json.loads(raw.split('```json\n',1)[1].split('\n```',1)[0])
            if not isinstance(record,dict):continue
            if not isinstance(record.get('id'),str) or str(uuid.UUID(record['id']))!=record['id']:continue
            if record.get('origin') not in ('own_attempt','model_assisted'):continue
            if any(not isinstance(record.get(k),str) for k in ('created','reflection','goal','next_action','stage')):continue
            if record.get('paper_id')!=paper_id or record.get('section_id')!=section_id:continue
            if not isinstance(record.get('text'),str) or record.get('text_hash')!=sha(record['text']):continue
            if record.get('schema')!='awl.writing-checkpoint.v1':continue
            records.append(record)
        except (OSError,ValueError,IndexError,AttributeError,TypeError):continue
    # A synced conflict copy cannot count as another writing attempt.
    distinct={canonical_prose(r['text']) for r in records if r.get('origin')=='own_attempt'}-{''}
    records.sort(key=lambda r:(str(r.get('created','')),str(r.get('id',''))),reverse=True)
    return {'meaningful_attempts':len(distinct),'checkpoint_count':len({r.get('id') for r in records}),
            'checkpoints':[{k:v for k,v in r.items() if k!='text'} for r in records[:100]],
            'notice':'Intentional, self-reported writing attempts. Autosaves are not counted; this does not measure authorship or proficiency.'}


def checkpoint(ws,paper_id,section_id,body):
    allowed={'base_hash','request_id','reflection','origin'}
    if not isinstance(body,dict) or set(body)-allowed:raise ValueError('Include the saved version, reflection and kind of attempt.')
    try:request_id=str(uuid.UUID(body.get('request_id','')))
    except (ValueError,TypeError,AttributeError):raise ValueError('Use a unique checkpoint request id.') from None
    reflection=body.get('reflection','')
    if not isinstance(reflection,str) or not reflection.strip() or len(reflection)>2000:
        raise ValueError('Briefly record what you wrote, clarified or decided to keep (up to 2,000 characters).')
    origin=body.get('origin')
    if origin not in ('own_attempt','model_assisted'):raise ValueError('Choose an own attempt or a model-assisted checkpoint.')
    with ws.lock:
        note=ws.card(paper_id,section_id)
        if note['type'] not in ('section','subsection'):raise ValueError('Open a section to record a writing checkpoint.')
        path=ws.safe(practice_root(ws,paper_id,section_id)/(request_id+'.md'))
        if path.exists():return intentional_practice(ws,paper_id,section_id)
        if note['hash']!=body.get('base_hash') or note['conflict']:raise Conflict('The section changed. Compare or reload it before recording your checkpoint.')
        text=note['fields'].get('Manuscript prose','').strip()
        if not canonical_prose(text):raise ValueError('Write some section prose before recording an attempt.')
        if canonical_prose(text)==canonical_prose(note['fields'].get('Writing scaffold','')):
            raise ValueError('Rewrite part of the scaffold yourself before recording a writing attempt.')
        record={'schema':'awl.writing-checkpoint.v1','id':request_id,'paper_id':paper_id,'section_id':section_id,
                'created':now(),'origin':origin,'text':text,'text_hash':sha(text),
                'reflection':reflection.strip(),'goal':note['fields'].get('Writing intention',''),
                'next_action':note['fields'].get('Next writing action',''),'stage':note['fields'].get('Section writing stage','connect')}
        # Escape fences in JSON strings so arbitrary draft text cannot close it.
        payload=json.dumps(record,ensure_ascii=False,indent=2).replace('`','\\u0060')
        raw='# Writing checkpoint\n\n```json\n'+payload+'\n```\n\n## What moved forward\n\n'+record['reflection']+'\n\n## Next writing action\n\n'+record['next_action']+'\n\n## Draft at this checkpoint\n\n'+text+'\n'
        atomic_write(path,raw,exclusive=True)
        return intentional_practice(ws,paper_id,section_id)
