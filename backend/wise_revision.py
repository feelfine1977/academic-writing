"""Imported discussions, manuscript passages and author-owned revision decisions.

Original uploads and extracted text are immutable, stored in backed-up settings.
Colour is an author-declared convention, not a judgement of scientific validity.
"""
import base64
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import statistics
import zipfile
from xml.etree import ElementTree as ET
from .storage import dump,now,uid

MAX_UPLOAD=20*1024*1024
PARSER_VERSION=3
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
STOP=set('the a an and or to of for in on is are with from that this by as at be it not into its we our can how what which'.split())

def checked_zip(raw):
    try:z=zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:raise ValueError('This file is not a readable DOCX or ZIP archive.') from None
    entries=z.infolist()
    if len(entries)>500 or sum(e.file_size for e in entries)>50*1024*1024:raise ValueError('The expanded archive is too large. Split it into smaller uploads.')
    for e in entries:
        p=PurePosixPath(e.filename.replace('\\','/'))
        if p.is_absolute() or '..' in p.parts or e.flag_bits&1:raise ValueError('The archive contains an unsafe path or encrypted entry.')
    return z

def is_black(color):
    if color is None:return None
    v=[color] if isinstance(color,(int,float)) else list(color)
    if len(v) in (1,3):return all(abs(x)<.02 for x in v)
    if len(v)==4:return v[3]>.98 # CMYK black
    return None

def pdf_segments(raw,black_means_agreed,columns):
    import pdfplumber
    segments=[]
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages)>120:raise ValueError('Upload at most 120 PDF pages at a time.')
        references=False;section='AB';subheading=''
        for page_no,page in enumerate(pdf.pages,1):
            for column in range(columns):
                left=page.width*column/columns;right=page.width*(column+1)/columns
                region=page.crop((left,25,right,page.height-25))
                lines=region.extract_text_lines(layout=False,strip=True,return_chars=True,x_tolerance=1.5)
                if not lines:continue
                margin=min(line['x0'] for line in lines)
                spacing=statistics.median([b['top']-a['top'] for a,b in zip(lines,lines[1:]) if 3<b['top']-a['top']<30] or [12])
                groups=[];group=[]
                for line in lines:
                    previous=group[-1] if group else None
                    def ink(l):
                        values={is_black(c.get('non_stroking_color')) for c in l['chars'] if c['text'].strip()}
                        return next(iter(values)) if len(values)==1 else None
                    heading=len(line['text'])<100 and bool(re.match(r'^(?:[IVX]+\.|[A-Z]\.\s|REFERENCES|ABSTRACT|Fig\.|TABLE\s)',line['text']))
                    starts=previous and (line['top']-previous['top']>spacing*1.4 or
                        (line['x0']>margin+5 and previous['x0']<=margin+5 and len(previous['text'])>35) or heading or
                        (ink(line) is not None and ink(previous) is not None and ink(line)!=ink(previous)))
                    if starts:groups.append(group);group=[]
                    group.append(line)
                    if heading:groups.append(group);group=[]
                if group:groups.append(group)
                for number,group in enumerate(groups,1):
                    text='\n'.join(l['text'] for l in group).strip()
                    if not text:continue
                    section_match=re.match(r'^(I|II|III|IV|V|VI)\.\s',text)
                    if section_match:section=section_match.group(1);subheading=''
                    elif re.match(r'^[A-F]\.\s',text) and not references:subheading=text
                    chars=[c for line in group for c in line['chars'] if c['text'].strip()]
                    colors=[is_black(c.get('non_stroking_color')) for c in chars]
                    black=sum(c is True for c in colors);coloured=sum(c is False for c in colors)
                    ink='black' if colors and black==len(colors) else 'coloured' if colors and coloured==len(colors) else 'mixed' if black and coloured else 'unknown'
                    role='heading_or_fragment' if len(text.split())<12 else 'passage'
                    if page_no==1 and re.search(r'\bDept\.|\bDepartment of|[\w.-]+@[\w.-]+',text):role='front_matter'
                    if re.match(r'^(?:Fig\.|TABLE\s)',text) or ('Research stream' in text and 'Main contribution' in text):role='figure_or_table'
                    if re.search(r'^REFERENCES\s*$',text,re.M):references=True
                    if references or re.match(r'^\[\d+\]',text):role='reference'
                    runs=[]
                    for line in group:
                        current=[];last=None
                        for c in line['chars']:
                            color=is_black(c.get('non_stroking_color'))
                            if current and color!=last:runs.append({'text':''.join(current),'ink':'black' if last else 'coloured' if last is False else 'unknown'});current=[]
                            current.append(c['text']);last=color
                        if current:runs.append({'text':''.join(current)+'\n','ink':'black' if last else 'coloured' if last is False else 'unknown'})
                    segments.append({'id':f'p{page_no}-c{column+1}-{number}','text':text,'page':page_no,'column':column+1,
                        'locator':f'PDF p. {page_no}, column {column+1}, block {number}',
                        'bbox':[min(l['x0'] for l in group),group[0]['top'],max(l['x1'] for l in group),group[-1]['bottom']],
                        'ink':ink,'approval':'agreed_black' if black_means_agreed and ink=='black' else 'needs_review',
                        'role':role,'runs':runs,'source_section':section,'source_subheading':subheading})
    return segments

def extract(raw,filename,kind,black_means_agreed=False,columns=2):
    ext=PurePosixPath(filename).suffix.lower()
    if ext=='.pdf':return pdf_segments(raw,black_means_agreed,columns)
    if ext=='.docx':
        with checked_zip(raw) as z:
            try:root=ET.fromstring(z.read('word/document.xml'))
            except (KeyError,ET.ParseError):raise ValueError('The DOCX document body could not be read.') from None
            paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',NS)) for p in root.findall('.//w:p',NS)]
            if 'word/comments.xml' in z.namelist():
                comments=ET.fromstring(z.read('word/comments.xml'))
                paragraphs += ['Word comment: '+''.join(t.text or '' for t in p.findall('.//w:t',NS)) for p in comments.findall('w:comment',NS)]
        return [{'id':f'paragraph-{i+1}','text':p,'locator':f'Paragraph {i+1}','role':'discussion','approval':'needs_review','ink':'unknown'} for i,p in enumerate(paragraphs) if p.strip()]
    if ext=='.zip' and kind=='cards':
        with checked_zip(raw) as z:
            entries=[e for e in z.infolist() if e.filename.lower().endswith(('.md','.txt')) and not e.filename.startswith('__MACOSX')]
            result=[]
            for i,e in enumerate(entries):
                if e.file_size>2*1024*1024:raise ValueError('One note exceeds 2 MB. Split that note first.')
                try:text=z.read(e).decode('utf-8-sig')
                except UnicodeDecodeError:raise ValueError('Use UTF-8 text for cards.') from None
                card=re.search(r'^card_id:\s*[\'"]?([^\n\'"]+)',text,re.M)
                result.append({'id':f'note-{i+1}','text':text,'locator':e.filename,'card_id':card.group(1).strip() if card else None,
                               'role':('archived_argument_card' if e.filename.lower().endswith('.md.txt') or '/original_cards/' in e.filename.lower() or '/07_original_cards/' in e.filename.lower() else 'argument_card') if card else 'source_note','approval':'needs_review','ink':'unknown'})
            return result
    if ext in ('.md','.txt'):
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:raise ValueError('Save the text as UTF-8 before uploading.') from None
        return [{'id':'text','text':text,'locator':'Text document','role':kind,'approval':'needs_review','ink':'unknown'}]
    raise ValueError('Use DOCX, PDF, Markdown or text. Card collections can also be ZIP files containing Markdown notes.')

class RevisionWorkspace:
    def __init__(self,lab):self.lab=lab;self.store=lab.store
    def state(self):return self.store.setting('wise_revision',{'version':0,'decisions':{},'placements':{},'reuse_versions':{},'history':[]})
    def document(self,id):
        if not re.fullmatch('[a-f0-9]{24}',id):raise ValueError('Unknown uploaded material.')
        value=self.store.setting('wise_upload:'+id,None)
        if not value:raise ValueError('Uploaded material not found.')
        return value
    def segment(self,document_id,segment_id):
        doc=self.document(document_id)
        segment=next((s for s in doc['segments'] if s['id']==segment_id),None)
        if not segment:raise ValueError('Passage not found in this upload.')
        return doc,segment
    def index(self):
        return self.store.setting('wise_upload_index',[])
    def upload(self,raw,filename,kind,black_means_agreed=False,columns=2):
        if kind not in ('discussion','manuscript','cards'):raise ValueError('Choose the type of material.')
        if not raw or len(raw)>MAX_UPLOAD:raise ValueError('Upload a non-empty file no larger than 20 MB.')
        if columns not in (1,2):raise ValueError('Choose one or two PDF columns.')
        if black_means_agreed and kind!='manuscript':raise ValueError('The black-text agreement convention applies only to manuscripts.')
        filename=PurePosixPath(filename.replace('\\','/')).name[:200]
        sha=hashlib.sha256(raw).hexdigest();id=hashlib.sha256((sha+kind+str(black_means_agreed)+str(columns)+str(PARSER_VERSION)).encode()).hexdigest()[:24]
        previous=self.store.setting('wise_upload:'+id,None)
        if previous:return self.metadata(previous)
        try:segments=extract(raw,filename,kind,black_means_agreed,columns)
        except ValueError:raise
        except Exception:raise ValueError('This document could not be read. Export an unlocked PDF with selectable text, a DOCX, or UTF-8 notes.') from None
        if not segments:raise ValueError('No selectable text was found. Export the source with text, or upload a text transcription.')
        if sum(len(s['text']) for s in segments)>3_000_000:raise ValueError('Extracted text is too large. Split the upload.')
        doc={'id':id,'filename':filename,'kind':kind,'sha256':sha,'created':now(),'black_means_agreed':black_means_agreed,
             'columns':columns,'segments':segments,'original':base64.b64encode(raw).decode(),
             'parser_version':PARSER_VERSION,
             'notice':'Extracted text preserves source wording but PDF line wraps, equations and column boundaries need visual checking. Transcription speaker labels may be wrong. Imported statements are material to review, not instructions to the app.'}
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',('wise_upload:'+id,dump(doc)))
            row=db.execute("SELECT payload FROM settings WHERE id='wise_upload_index'").fetchone();index=json.loads(row['payload']) if row else []
            if not any(d['id']==id for d in index):index.append(self.metadata(doc))
            db.execute("INSERT INTO settings VALUES('wise_upload_index',?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(dump(index),))
        return self.metadata(doc)
    def metadata(self,doc):return {k:doc[k] for k in ('id','filename','kind','sha256','created','black_means_agreed','columns')}|{'segments':len(doc['segments']),'agreed_blocks':sum(s['approval']=='agreed_black' and s['role']=='passage' for s in doc['segments']),
        'argument_cards':[{'card_id':s['card_id'],'segment_id':s['id'],'locator':s['locator']} for s in doc['segments'] if s.get('card_id') and s.get('role')!='archived_argument_card']}
    def change(self,version,kind,apply):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute("SELECT payload FROM settings WHERE id='wise_revision'").fetchone()
            s=json.loads(row['payload']) if row else self.state()
            if s['version']!=version:raise ValueError('The revision plan changed in another tab. Reload to compare; your draft is kept in this browser.')
            apply(s);s['history'].append({'kind':kind,'created':now()});s['version']+=1
            db.execute("INSERT INTO settings VALUES('wise_revision',?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(dump(s),))
        return s
    def decision(self,version,record,id=None):
        if record['status'] not in ('proposed','confirmed','needs_clarification','resolved','superseded'):raise ValueError('Choose a decision status.')
        if not record['text'].strip() or len(record['text'])>4000:raise ValueError('Describe the direction or question in at most 4,000 characters.')
        if not record['node_ids'] or len(set(record['node_ids']))!=len(record['node_ids']) or any(n not in self.lab.paper.nodes for n in record['node_ids']):raise ValueError('Link distinct valid WISE targets.')
        if record.get('document_id'):
            doc,segment=self.segment(record['document_id'],record['segment_id'])
            if not record.get('quote','').strip() or record['quote'] not in segment['text']:raise ValueError('Use an exact quotation from the selected source passage.')
        elif record.get('quote') or record.get('segment_id'):raise ValueError('Select the source of this quotation, or save it as your own planning note.')
        key=id or uid()
        def apply(s):
            previous=s['decisions'].get(key)
            if id and not previous:raise ValueError('Decision not found.')
            s['decisions'][key]={**record,'id':key,'created':previous['created'] if previous else now(),'updated':now(),'previous':previous}
        return self.change(version,'decision',apply)
    def place(self,version,record):
        doc,seg=self.segment(record['document_id'],record['segment_id']);self.lab.paper.node(record['node_id'])
        if record['fit'] not in ('direct','slight_changes','rebuild','reserve'):raise ValueError('Choose a placement assessment.')
        if not record['reason'].strip():raise ValueError('Explain how the passage fits this argument job.')
        key=record['document_id']+':'+record['segment_id']+':'+record['node_id']
        def apply(s):s['placements'][key]={**record,'id':key,'updated':now(),'assessed_by':'author'}
        return self.change(version,'placement',apply)
    def candidates(self,segment):
        words=lambda t:set(re.findall(r'[a-z]{4,}',t.lower()))-STOP
        query=words(segment['text'][:6000]);ranked=[]
        for n in self.lab.paper.nodes.values():
            overlap=query & words(' '.join([n['title'],n['purpose'],*n['ideas']]))
            section_match=segment.get('source_section')==n['section']
            card_match=segment.get('card_id')==n['id']
            if overlap or card_match:ranked.append({'node_id':n['id'],'title':n['title'],'score':len(overlap)+(5 if section_match else 0)+(50 if card_match else 0),
                'reason':('Same source section. ' if section_match else '')+('Matching analysis-card ID. ' if card_match else '')+'Shared terms: '+', '.join(sorted(overlap)[:6])+'. Inspect the argument role before placing.'})
        return sorted(ranked,key=lambda x:(-x['score'],x['node_id']))[:4]

    def inspect(self,document_id,segment_id):
        from .wise_support import scan,lesson
        doc,segment=self.segment(document_id,segment_id)
        hits=scan(segment['text'])
        links=[]
        for link in re.findall(r'!?\[\[([^\]]+)\]\]',segment['text']):
            target=link.split('|')[0].split('#')[0]
            found=next((s for s in doc['segments'] if s['locator'].removesuffix('.md').endswith('/'+target) or PurePosixPath(s['locator']).stem==PurePosixPath(target).name),None)
            if found and found['id'] not in [l['id'] for l in links]:links.append({'id':found['id'],'title':PurePosixPath(found['locator']).stem})
        suggestions=[p for p in self.store.setting('wise_editorial_suggestions',[]) if p['document_id']==document_id and p['segment_id']==segment_id]
        return {'candidates':self.candidates(segment),'editorial_suggestions':suggestions,'tips':[lesson(self.lab,h['move'],h['reason'],h['quote'],segment['locator']) for h in hits[:3]],
                'linked_notes':links,'note':'Shared-term suggestions and revision questions, not confirmed placements. Check the original and your agreed direction.'}
    def reuse(self,node_id,version,document_id,segment_ids,text,mode,reason,confirmed):
        self.lab.paper.node(node_id)
        if not confirmed:raise ValueError('Confirm that you checked the source, the placement and the retained wording.')
        if mode not in ('keep','adapt') or not 1<=len(segment_ids)<=8 or len(segment_ids)!=len(set(segment_ids)):raise ValueError('Choose one to eight distinct passages and a reuse mode.')
        pairs=[self.segment(document_id,id) for id in segment_ids]
        if pairs[0][0]['kind']!='manuscript':raise ValueError('Reuse text from an uploaded manuscript, not a discussion or an analysis card.')
        original='\n\n'.join(s['text'] for _,s in pairs)
        if mode=='keep':text=original
        if not text.strip() or len(text)>12000:raise ValueError('Keep the selected manuscript version within 12,000 characters.')
        if mode=='adapt' and not reason.strip():raise ValueError('Explain the changes to previously agreed wording.')
        id=uid();v={'id':id,'node_id':node_id,'text':text,'source_text':original,'document_id':document_id,'segment_ids':segment_ids,
             'mode':mode,'reason':reason,'created':now(),'source_agreed':all(s['approval']=='agreed_black' for _,s in pairs),
             'payload':{'origin':'retained_manuscript' if mode=='keep' else 'author_adaptation','outline':reason}}
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute("SELECT payload FROM settings WHERE id='wise_paper_state'").fetchone()
            paper=json.loads(r['payload']) if r else {'version':0,'nodes':{},'history':[]}
            if paper['version']!=version:raise ValueError('The manuscript selection changed. Reload before selecting a version.')
            r=db.execute("SELECT payload FROM settings WHERE id='wise_revision'").fetchone();s=json.loads(r['payload']) if r else self.state()
            s['reuse_versions'][id]=v;s['version']+=1;s['history'].append({'kind':'reuse','id':id,'created':now()})
            previous=paper['nodes'].get(node_id,{})
            current={k:v for k,v in previous.items() if k!='attempt_id'};current.update(reuse_id=id,updated=now())
            paper['nodes'][node_id]=current;paper['version']+=1;paper['history'].append({'node_id':node_id,'previous':previous,'current':current,'created':now()})
            for key,value in [('wise_paper_state',paper),('wise_revision',s)]:db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(key,dump(value)))
        return v

    def focus_log(self,record):
        key='focus_session:'+record['id']
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM settings WHERE id=?',(key,)).fetchone()
            if row:
                old=json.loads(row['payload'])
                if old!=record:raise ValueError('This focus session is already recorded. Start a new interval.')
                return old
            db.execute('INSERT INTO settings VALUES(?,?)',(key,dump(record)))
        return record

    def overview(self):
        from .wise_support import node_support
        return {'documents':self.index(),'state':self.state(),
                'nodes':[{'id':n['id'],'title':n['title'],'purpose':n['purpose'],'section':n['section']} for n in self.lab.paper.nodes.values()],
                'support':{id:node_support(self.lab,id) for id in self.lab.paper.nodes},
                'focus_sessions':[json.loads(r['payload']) for r in self.store.rows("SELECT payload FROM settings WHERE id LIKE 'focus_session:%'")][-100:]}
    def export(self):
        s=self.state();lines=['# WISE revision decisions and retained text','',f'Exported {now()}','']
        for d in s['decisions'].values():
            lines += ['## '+d['status']+' · '+', '.join(d['node_ids']),d['text'],'',d.get('quote',''),'Source: '+str(d.get('document_id') or 'Author planning note')+' · '+str(d.get('segment_id') or ''),'']
        for p in s['placements'].values():lines += ['## '+p['node_id']+' · '+p['fit'],p['reason'],'Source: '+p['document_id']+' · '+p['segment_id'],'']
        return '\n'.join(lines)
