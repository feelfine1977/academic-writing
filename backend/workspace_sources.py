"""Manuscript imports and exact passage links in a portable paper folder."""
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import re
import uuid

from .workspace import atomic_write, frontmatter, split_note
from .wise_revision import extract
from scripts.create_paper_workspace import portable_name, unique_name, link_label

MAX_BYTES = 16 * 1024 * 1024


def text_segments(raw, tex=False):
    try: text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as error: raise ValueError('Save this text file as UTF-8 before importing it.') from error
    if len(text)>2_000_000: raise ValueError('Import a shorter text file (up to two million characters).')
    segments=[]; section=''; start=0
    for block in re.split(r'\n\s*\n',text):
        offset=text.find(block,start);start=offset+len(block)
        if not block.strip():continue
        headings = re.findall(r'\\(?:sub)*section\*?(?:\[[^\]]*\])?\{([^}]+)\}',block) if tex else re.findall(r'^#{1,6}\s+(.+)',block,re.M)
        if headings:section=headings[-1]
        line=text.count('\n',0,offset)+1
        segments.append({'id':'line-'+str(line),'text':block.strip(),'locator':'Source lines '+str(line)+'–'+str(line+block.count('\n')),
                         'ink':'unknown','approval':'needs_review','role':'passage','heading':section})
    return segments


class PaperSources:
    def __init__(self, workspace):self.workspace=workspace

    def root(self, paper_id):
        return self.workspace.safe(self.workspace.locate(paper_id).parent/'Sources')

    def upload(self, paper_id, filename, raw, *, columns=2, black_means_agreed=False):
        root=self.root(paper_id)
        if not raw or len(raw)>MAX_BYTES:raise ValueError('Choose a source file no larger than 16 MB.')
        suffix=Path(filename).suffix.lower()
        if suffix not in {'.pdf','.tex','.txt','.md','.docx'}:raise ValueError('Import PDF, TeX, Word, Markdown or plain text.')
        if columns not in (1,2):raise ValueError('Choose one or two PDF columns.')
        if suffix in ('.tex','.txt','.md'):segments=text_segments(raw,suffix=='.tex')
        else:
            try:segments=extract(raw,filename,'manuscript',black_means_agreed,columns)
            except ValueError:raise
            except Exception as error:raise ValueError('This source could not be read. Try an unlocked PDF or a UTF-8 text export.') from error
        if not segments:raise ValueError('No text could be extracted. For a scanned PDF, supply an OCR or text version.')
        with self.workspace.lock:
            root.mkdir(parents=True,exist_ok=True)
            name=unique_name(Path(filename).stem,{p.name.casefold() for p in root.iterdir()})
            directory=self.workspace.safe(root/name);directory.mkdir()
            original='Original - '+portable_name(Path(filename).stem)+suffix
            # Original bytes and the exact index precede the manifest. A partially
            # delivered source is never treated as a complete searchable import.
            with (directory/original).open('xb') as stream:
                stream.write(raw);stream.flush()
                import os
                os.fsync(stream.fileno())
            source_id=str(uuid.uuid4())
            meta={'awl_schema':1,'awl_kind':'paper_source','awl_id':source_id,'title':filename,
                  'original':original,'sha256':hashlib.sha256(raw).hexdigest(),'columns':columns,
                  'black_means_agreed':bool(black_means_agreed),'segment_count':len(segments)}
            index=json.dumps(segments,ensure_ascii=False,indent=2)
            meta['index_sha256']=hashlib.sha256(index.encode()).hexdigest()
            atomic_write(directory/'Passage index.md','# Passage index\n\n```json\n'+index+'\n```\n',exclusive=True)
            prose=['# Passages from '+filename,'','[Original file]('+quote(original)+')','']
            for s in segments:
                prose += ['## '+s['id'],'',s['locator']+' · '+s.get('ink','unknown')+' · '+s.get('approval','needs_review'),'',s['text'],'']
            atomic_write(directory/'Passages.md','\n'.join(prose),exclusive=True)
            note='PDF extraction order and colour labels need your review.' if suffix=='.pdf' else 'Source text is preserved. TeX is read as text; commands and included files are not executed or loaded.' if suffix=='.tex' else 'Source text is preserved for mapping to your argument plan.'
            atomic_write(directory/'Source.md',frontmatter(meta)+'# '+filename+'\n\n[Read passages](Passages.md) · [Original file]('+quote(original)+')\n\n'+note+'\n',exclusive=True)
            return {**meta,'folder':name,'note':note}

    def catalogue(self,paper_id):
        items=[];issues=[]
        for path in sorted(self.root(paper_id).glob('*/Source.md')):
            try:
                meta,_=split_note(self.workspace.safe(path).read_text(encoding='utf-8'))
                if meta.get('awl_kind')!='paper_source':continue
                original=self.workspace.safe(path.parent/meta['original'])
                if original.parent!=path.parent:raise ValueError('Invalid source file link.')
                if not original.is_file() or not all((path.parent/f).is_file() for f in ('Passage index.md','Passages.md')):raise ValueError('Waiting for source files to finish syncing.')
                if original.stat().st_size>MAX_BYTES or hashlib.sha256(original.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('The original file changed or is incomplete. Import a changed source as a new version.')
                items.append({**meta,'folder':path.parent.name,'path':str(path),'uri':self.workspace.uri(path.parent/'Passages.md')})
            except (ValueError,OSError,KeyError) as error:issues.append(path.parent.name+': '+str(error))
        ids=[s['awl_id'] for s in items]
        duplicates={id for id in ids if ids.count(id)>1}
        if duplicates:issues.append('Duplicate source identities need resolution in Obsidian. Both copies are kept.')
        return {'sources':[s for s in items if s['awl_id'] not in duplicates],'issues':issues}

    def read(self,paper_id,source_id):
        source=next((s for s in self.catalogue(paper_id)['sources'] if s['awl_id']==source_id),None)
        if not source:raise ValueError('Source not found or still syncing.')
        root=Path(source['path']).parent
        raw=self.workspace.safe(root/'Passage index.md').read_text(encoding='utf-8')
        match=re.fullmatch(r'# Passage index\n\n```json\n(.*)\n```\n',raw,re.S)
        if not match or hashlib.sha256(match.group(1).encode()).hexdigest()!=source['index_sha256']:raise ValueError('The source index is incomplete or changed. Import the revised source as a new version.')
        segments=json.loads(match.group(1))
        if len(segments)!=source['segment_count']:raise ValueError('The source index is incomplete.')
        return source,segments

    def search(self,paper_id,query='',ink='all',source_id=None):
        if ink not in ('all','black','coloured','mixed','unknown','agreed'):raise ValueError('Unknown colour filter.')
        tokens=re.findall(r'\w+',query.casefold());hits=[]
        catalogue=self.catalogue(paper_id)
        for item in catalogue['sources']:
            if source_id and item['awl_id']!=source_id:continue
            source,segments=self.read(paper_id,item['awl_id'])
            for i,s in enumerate(segments):
                if ink=='agreed' and s.get('approval')!='agreed_black':continue
                if ink not in ('all','agreed') and s.get('ink')!=ink:continue
                text=s['text'].casefold();score=sum(text.count(t) for t in tokens)
                if tokens and not all(t in text for t in tokens):continue
                hits.append({**s,'source_id':item['awl_id'],'source_title':source['title'],'score':score,
                             'before':segments[i-1]['text'] if i else '', 'after':segments[i+1]['text'] if i+1<len(segments) else '',
                             'link':'../Sources/'+quote(source['folder'])+'/Passages.md#'+s['id']})
        hits.sort(key=lambda s:-s['score'])
        return {'results':hits[:80],'total':len(hits),'issues':catalogue['issues']}

    def mapping(self,paper_id,source_id,segment_id,decision,reason):
        if decision not in ('keep','adapt','combine','background'):raise ValueError('Choose how this passage relates to the argument.')
        source,segments=self.read(paper_id,source_id)
        s=next((s for s in segments if s['id']==segment_id),None)
        if not s:raise ValueError('Passage not found.')
        link='../Sources/'+quote(source['folder'])+'/Passages.md#'+s['id']
        return '\n\n### '+decision.capitalize()+' · '+source['title']+' · '+s['locator']+'\n\n['+link_label('Read original passage')+']('+link+')\n\n'+'\n'.join('> '+line for line in s['text'].splitlines())+'\n\nMy reason: '+reason.strip()+'\n'
