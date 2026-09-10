"""Small Markdown backup parts that fit Obsidian Sync Standard's per-file limit."""
import base64
import gzip
import hashlib
import io
import json
import re
from .storage import dump,validate_backup

PART_CHARS=3_000_000
MAX_EXPANDED=250_000_000

def split_backup(backup,part_chars=PART_CHARS):
    validate_backup(backup)
    raw=gzip.compress(dump(backup).encode(),compresslevel=6,mtime=0)
    encoded=base64.b64encode(raw).decode();id=hashlib.sha256(raw).hexdigest()
    chunks=[encoded[i:i+part_chars] for i in range(0,len(encoded),part_chars)]
    output=[]
    for i,chunk in enumerate(chunks,1):
        record={'schema':'awl.backup.part.v1','backup_id':id,'encoding':'gzip+base64','index':i,'count':len(chunks),'data':chunk,'sha256':hashlib.sha256(chunk.encode()).hexdigest()}
        output.append((f'Backup part {i:03d} of {len(chunks):03d}.md',f'# Writing Lab backup part {i} of {len(chunks)}\n\nKeep every numbered part together. Restore by selecting all parts in Writing Lab Settings. This is backup data; do not edit it.\n\n```json\n'+dump(record)+'\n```\n'))
    return output

def unpack_backup(body):
    if body.get('schema')!='awl.backup.parts.v1':return body
    parts=body.get('parts')
    if not isinstance(parts,list) or not 1<=len(parts)<=100:raise ValueError('Select all numbered backup part files from one backup folder.')
    records=[]
    for text in parts:
        if not isinstance(text,str) or len(text)>4_000_000:raise ValueError('One backup part is invalid or too large.')
        match=re.search(r'```json\n(.+)\n```\s*$',text,re.S)
        try:record=json.loads(match.group(1)) if match else None
        except ValueError:record=None
        if not isinstance(record,dict) or record.get('schema')!='awl.backup.part.v1' or record.get('encoding')!='gzip+base64':raise ValueError('Choose only the numbered Backup part Markdown files, or choose one full JSON backup.')
        chunk=record.get('data')
        if not isinstance(chunk,str) or hashlib.sha256(chunk.encode()).hexdigest()!=record.get('sha256'):raise ValueError('A backup part was changed or damaged. Use an intact copy.')
        records.append(record)
    count=len(records)
    if any(r.get('count')!=count or r.get('backup_id')!=records[0].get('backup_id') for r in records) or {r.get('index') for r in records}!=set(range(1,count+1)):
        raise ValueError('Backup parts are missing, duplicated or from different backups. Select one complete set.')
    try:
        raw=base64.b64decode(''.join(r['data'] for r in sorted(records,key=lambda r:r['index'])),validate=True)
        if hashlib.sha256(raw).hexdigest()!=records[0]['backup_id']:raise ValueError('Backup checksum mismatch.')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:expanded=f.read(MAX_EXPANDED+1)
        if len(expanded)>MAX_EXPANDED:raise ValueError('The expanded backup exceeds 250 MB.')
        backup=json.loads(expanded)
    except (OSError,EOFError,ValueError) as error:raise ValueError('The backup could not be reconstructed: '+str(error)) from None
    validate_backup(backup)
    return backup
