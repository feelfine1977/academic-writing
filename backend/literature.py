"""Read-only discovery of shared literature cards and an optional local catalogue.

Paper drafts and bibliography writes keep using the workspace's versioned APIs.
The catalogue never turns an exported abstract into a verified quotation.
"""
from pathlib import Path
import json
import re
import threading
import yaml

ROOT = Path('02_Shared/Literature')
CATALOGUE = Path('100_do_not_sync/Literature_Catalogue/Library_Index.json')


def section(body, name):
    match = re.search(r'^## '+re.escape(name)+r'\s*\n(.*?)(?=^## |\Z)', body, re.S | re.M)
    return match.group(1).strip() if match else ''


def read_card(raw):
    match = re.match(r'\A---\n(.*?)\n---\n', raw.replace('\r\n','\n'), re.S)
    if not match: raise ValueError('The literature card needs its document properties.')
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta,dict) or meta.get('library_schema') != 1:
        raise ValueError('Unsupported literature card version.')
    return meta, raw.replace('\r\n','\n')[match.end():]


def passages(body):
    text = section(body, 'Quotations with context')
    result = []
    for match in re.finditer(r'^### (Q[\w-]+)\s*[·—-]\s*([^\n]+)\n(.*?)(?=^### |\Z)', text, re.S | re.M):
        ident, title, block = match.groups()
        quoted = re.findall(r'^> ?(.*)$', block, re.M)
        if not quoted: continue
        def field(label):
            value = re.search(r'\*\*'+re.escape(label)+r':\*\*\s*(.*?)(?=\n\s*\n|\Z)', block, re.S)
            return value.group(1).strip() if value else ''
        page = re.search(r'\*\*Printed page:\*\*\s*(.*?);\s*\*\*PDF page:\*\*\s*(\d+)',block)
        context=field('Context')
        # Incomplete template passages are shown in Obsidian, never offered as evidence.
        if not page or not context or not page.group(1).strip(): continue
        result.append({'id':ident.lower(),'title':title.strip(),'passage':'\n'.join(quoted),
                       'printedPage':page.group(1).strip(),'pdfPage':page.group(2),
                       'context':context,'supports':field('Supports'),'limits':field('Use with care'),
                       'use':field('Writing use')})
    return result


class Literature:
    def __init__(self, workspace):
        self.workspace=workspace
        self._lock=threading.RLock()
        self._stamp=None
        self._entries=[]
        self._warnings=[]

    def index(self):
        self.workspace.require_enabled()
        vault=self.workspace.lab.vault
        candidates=[vault/ROOT/'Library_Index.json',vault/CATALOGUE]
        files=[self.workspace.safe(p) for p in candidates if p.is_file()]
        sources=self.workspace.safe(vault/ROOT/'Sources')
        cards=sorted(sources.rglob('*.md')) if sources.is_dir() else []
        cards=[self.workspace.safe(p) for p in cards]
        stamp=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files+cards)
        with self._lock:
            if self._stamp==stamp:return self._entries,self._warnings
            rows={};warnings=[]
            for p in files:
                if p.stat().st_size>40_000_000:raise ValueError('The literature index is too large.')
                try:
                    value=json.loads(p.read_text(encoding='utf-8'))
                    if value.get('schema')!=1 or not isinstance(value.get('entries'),list):raise ValueError()
                    for entry in value['entries']:
                        if isinstance(entry,dict) and isinstance(entry.get('id'),str):rows[entry['id']]=dict(entry)
                except (OSError,ValueError,AttributeError):
                    warnings.append('Could not read '+p.name+'. Valid source cards remain available.')
            seen=set()
            for p in cards:
                if p.stat().st_size>4_000_000:
                    warnings.append('Skipped a source card larger than 4 MB: '+p.name);continue
                try:
                    meta,body=read_card(p.read_text(encoding='utf-8'))
                    ident=meta.get('library_id')
                    if not isinstance(ident,str) or not re.fullmatch(r'[\w-]{1,100}',ident):raise ValueError('A unique library_id is required.')
                    if ident in seen:
                        rows.pop(ident,None);warnings.append('Duplicate library_id; resolve it in Obsidian: '+ident);continue
                    seen.add(ident)
                    row=rows.setdefault(ident,{'id':ident,'keys':[],'export_count':0})
                    for field in ['title','author','year','doi']:
                        if field in meta:row[field]=str(meta[field] or '')
                    row.update(key=str(meta.get('citekey') or row.get('key') or ''),status=str(meta.get('reading_status') or 'catalogued'),
                               has_note=True,note=p.relative_to(vault).as_posix(),uri=self.workspace.uri(p),
                               tags=[t.removeprefix('lit/topic/') for t in meta.get('tags',[]) if isinstance(t,str) and t.startswith('lit/topic/')],
                               uses=[t.removeprefix('lit/use/') for t in meta.get('tags',[]) if isinstance(t,str) and t.startswith('lit/use/')],
                               quote_count=len(passages(body)),overview=section(body,'In brief'))
                except (OSError,ValueError,yaml.YAMLError,TypeError) as error:
                    warnings.append('Check source-card properties: '+p.name)
            # A missing note never masquerades as a current reading card.
            for row in rows.values():
                if row.get('note'):
                    try:p=self.workspace.safe(vault/row['note'])
                    except ValueError:p=None
                    if not p or not p.is_file() or not p.resolve().is_relative_to(sources.resolve()):
                        row.update(has_note=False,quote_count=0,status='catalogued');row.pop('note',None);row.pop('uri',None)
            self._entries=list(rows.values());self._warnings=warnings;self._stamp=stamp
            return self._entries,warnings

    def search(self,q='',topic='',status='',scope='notes',offset=0):
        rows,warnings=self.index()
        terms=q.casefold().split()[:12]
        topics=sorted({t for e in rows for t in e.get('tags',[]) if isinstance(t,str)})
        result=[]
        for e in rows:
            if scope!='all' and not e.get('has_note'):continue
            if topic and topic not in e.get('tags',[]):continue
            if status and e.get('status')!=status:continue
            hay=' '.join(str(e.get(f,'')) for f in ['title','author','year','key','keys','doi','tags','uses','overview']).casefold()
            if not all(t in hay for t in terms):continue
            result.append(e)
        result.sort(key=lambda e:(e.get('status')!='passages-checked',not e.get('has_note'),e.get('title','').casefold()))
        offset=max(0,int(offset));fields=['id','title','author','year','key','tags','status','has_note','quote_count','pdf_available','conflicting_keys']
        return {'entries':[{f:e.get(f) for f in fields} for e in result[offset:offset+40]],'total':len(result),'offset':offset,
                'topics':topics,'warnings':warnings,'catalogue_total':len(rows),'next_offset':offset+40 if offset+40<len(result) else None}

    def detail(self,ident):
        rows,_=self.index();found=next((e for e in rows if e['id']==ident),None)
        if not found:raise ValueError('This source is no longer in the library. Search again.')
        entry=dict(found);entry['quotes']=[]
        if entry.get('note'):
            p=self.workspace.safe(self.workspace.lab.vault/entry['note'])
            if not p.resolve().is_relative_to((self.workspace.lab.vault/ROOT/'Sources').resolve()):raise ValueError('Invalid literature-card location.')
            meta,body=read_card(p.read_text(encoding='utf-8'))
            entry['overview']=section(body,'In brief');entry['reading']=section(body,'Read and cite')
            entry['guide']='\n\n'.join('### '+name+'\n\n'+section(body,name) for name in
                ['Method and evidence','Main findings','Limits of the evidence','Use for WISE'] if section(body,name))
            bib=re.search(r'```bibtex\s*\n(.*?)\n```',section(body,'BibTeX'),re.S)
            entry['bibtex']=bib.group(1).strip() if bib else ''
            entry['quotes']=passages(body)
            entry['related']=[{'id':r['id'],'title':r.get('title','')} for r in rows if entry.get('doi') and r.get('doi','').startswith(entry['doi']+'_') and r.get('quote_count')]

        return entry
