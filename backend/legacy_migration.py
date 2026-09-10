"""Non-destructive adoption of the existing paper into readable argument cards."""
from pathlib import Path
from urllib.parse import quote
import base64
import gzip
import hashlib
import json
import os
import uuid

from .workspace import atomic_write,frontmatter,split_note
from .storage import dump,now
from .workspace_sources import PaperSources
from scripts.create_paper_workspace import create_paper,portable_name,unique_name,link_label


class LegacyMigration:
    def __init__(self,lab):self.lab=lab;self.workspace=lab.workspace

    def run(self):
        ws=self.workspace;ws.require_enabled()
        existing=ws.config().get('legacy_paper_id')
        if existing:return ws.get(existing)
        paper=self.lab.paper
        if not paper.nodes:raise ValueError('No bundled private paper is present on this installation. Open its synced Obsidian folder instead.')
        summary=paper.summary();revision=self.lab.store.setting('wise_revision',{});cards=[];legacy_ids=[]
        for section,title in paper.blueprint['sections'].items():
            parent=len(cards);cards.append({'kind':'section','title':section+' · '+title,'Purpose':'Organise the arguments in '+title+'.'});legacy_ids.append(None)
            order=summary['workbench']['orders'].get(section,[n['id'] for n in paper.nodes.values() if n['section']==section])
            for id in order:
                node=paper.nodes[id];plan=summary['workbench']['plans'].get(id,{})
                draft=summary['drafts'].get(id);selected=summary['selected'].get(id)
                notes='\n'.join('- '+idea for idea in node['ideas'])
                if plan.get('scratchpad'):notes+='\n\n### My saved notes\n\n'+plan['scratchpad']
                reasoning=['Planning guidance: '+node['boundary']]
                for field,value in plan.items():
                    if field not in ('scratchpad','updated') and value:reasoning.append(field.replace('_',' ').title()+': '+value)
                for d in revision.get('decisions',{}).values():
                    if id in d.get('node_ids',[]):reasoning.append('Supervisor direction ('+d['status']+'): '+d.get('text','')+'\nSource quotation: '+d.get('quote',''))
                if selected:reasoning.append('The separately selected manuscript version is preserved in Selected manuscript.md and the migration archive. Editing this working prose does not change that historical selection.')
                cards.append({'kind':'argument','parent_index':parent,'title':id+' · '+node['title'],'Purpose':node['purpose'],
                              'Notes and bullet points':notes,'Manuscript prose':(draft or selected or {}).get('text',''),
                              'Reasoning and decisions':'\n\n'.join(reasoning),'Next step':plan.get('next_action','')})
                legacy_ids.append(id)
        ws.root.mkdir(parents=True,exist_ok=True)
        destination=ws.root/unique_name('WISE',{p.name.casefold() for p in ws.root.iterdir()})
        stage=ws.root/('.Preparing WISE '+str(uuid.uuid4())[:8])
        snapshot=self.lab.store.snapshot()
        result=create_paper(stage,'WISE',cards)
        archive=stage/'Migration archive';archive.mkdir()
        raw=dump(snapshot).encode('utf-8');packed=gzip.compress(raw,mtime=0)
        parts=[]
        for start in range(0,len(packed),2_800_000):
            chunk=packed[start:start+2_800_000];name='Backup part '+str(len(parts)+1).zfill(2)+'.md';parts.append({'file':name,'sha256':hashlib.sha256(chunk).hexdigest()})
            atomic_write(archive/name,'# Complete legacy backup · part '+str(len(parts))+'\n\n```base64\n'+base64.b64encode(chunk).decode()+'\n```\n',exclusive=True)
        manifest={'schema':'awl.legacy-migration.v1','created':now(),'paper_id':result['paper_id'],'raw_sha256':hashlib.sha256(raw).hexdigest(),'parts':parts,
                  'counts':{k:len(v) for k,v in snapshot['tables'].items()},'source_cards':len(paper.cards),'arguments':len(paper.nodes),'mapping':{old:new for old,new in zip(legacy_ids,result['card_ids']) if old}}
        atomic_write(archive/'Migration manifest.md','# WISE migration manifest\n\n```json\n'+json.dumps(manifest,ensure_ascii=False,indent=2)+'\n```\n',exclusive=True)
        source_names={};used={};source_index=['# WISE source cards','','These are preserved research/source cards, separate from the planned arguments.','']
        for source in paper.cards.values():
            section=portable_name(source.get('section_title','Research notes'));folder=stage/'Source cards'/section;folder.mkdir(parents=True,exist_ok=True)
            name=unique_name(source['title'],used.setdefault(section,set()))+'.md';path=folder/name
            atomic_write(path,source['raw'],exclusive=True);source_names[source['id']]=path.relative_to(stage).as_posix()
            source_index.append('- ['+link_label(source['title'])+']('+quote(path.relative_to(stage/'Source cards').as_posix(),safe='/')+')')
        atomic_write(stage/'Source cards'/'Source cards index.md','\n'.join(source_index),exclusive=True)
        for old,new,filename in zip(legacy_ids,result['card_ids'],result['filenames']):
            if not old:continue
            path=stage/'Cards'/filename;meta,body=split_note(path.read_text(encoding='utf-8'));meta['legacy_argument_id']=old
            selected_ids=summary['state']['nodes'].get(old,{}).get('source_ids',[])
            candidates=list(dict.fromkeys(selected_ids+paper.nodes[old]['source_card_ids']))
            links=['- '+('Selected source: ' if id in selected_ids else 'Suggested source, not confirmed: ')+'['+link_label(paper.cards[id]['title'])+'](../'+quote(source_names[id],safe='/')+')' for id in candidates if id in source_names]
            from .workspace import update_fields
            body=update_fields(body,{'Source mapping':'\n'.join(links)})
            atomic_write(path,frontmatter(meta)+body)
        selected=['# WISE — previously selected manuscript','','Historical selections at migration. The working argument cards may contain later drafts.','']
        for section,title in paper.blueprint['sections'].items():
            selected+=['## '+title,'']
            for n in paper.nodes.values():
                if n['section']==section and n['id'] in summary['selected']:selected += [summary['selected'][n['id']]['text'],'']
        atomic_write(stage/'Selected manuscript.md','\n'.join(selected),exclusive=True)
        atomic_write(archive/'Argument planning history.md',paper.workbench.export(),exclusive=True)
        atomic_write(archive/'Decisions and source mappings.md','# Preserved revision records\n\n```json\n'+json.dumps(revision,ensure_ascii=False,indent=2)+'\n```\n',exclusive=True)
        # Preserve originals and already extracted locators without reinterpreting
        # PDF colours or changing the identity used by prior supervisor decisions.
        for row in self.lab.store.rows("SELECT payload FROM settings WHERE id LIKE 'wise_upload:%'"):
            doc=json.loads(row['payload']);directory=stage/'Sources'/portable_name(Path(doc['filename']).stem)
            if directory.exists():directory=directory.with_name(directory.name+' '+doc['id'][:6])
            directory.mkdir(parents=True);original='Original - '+portable_name(Path(doc['filename']).stem)+Path(doc['filename']).suffix.lower()
            binary=base64.b64decode(doc['original']);(directory/original).write_bytes(binary)
            index=json.dumps(doc['segments'],ensure_ascii=False,indent=2)
            atomic_write(directory/'Passage index.md','# Passage index\n\n```json\n'+index+'\n```\n',exclusive=True)
            passages=['# '+doc['filename'],'','[Original file]('+quote(original)+')','']
            for seg in doc['segments']:passages += ['## '+seg['id'],'',seg['locator'],'',seg['text'],'']
            atomic_write(directory/'Passages.md','\n'.join(passages),exclusive=True)
            meta={'awl_schema':1,'awl_kind':'paper_source','awl_id':doc['id'],'title':doc['filename'],'original':original,'sha256':hashlib.sha256(binary).hexdigest(),
                  'index_sha256':hashlib.sha256(index.encode()).hexdigest(),'segment_count':len(doc['segments']),'black_means_agreed':doc.get('black_means_agreed',False),'columns':doc.get('columns',2)}
            atomic_write(directory/'Source.md',frontmatter(meta)+'# '+doc['filename']+'\n\n[Read passages](Passages.md)\n',exclusive=True)
        root=stage/'Paper outline.md';text=root.read_text(encoding='utf-8')+'\n\n## Preserved material\n\n[Source cards](Source%20cards/Source%20cards%20index.md) · [Previously selected manuscript](Selected%20manuscript.md) · [Migration records](Migration%20archive/Migration%20manifest.md)\n'
        atomic_write(root,text)
        # Check exact migrated prose and raw source copies before publishing folder.
        for item,filename in zip(cards,result['filenames']):
            parsed=ws.read(stage/'Cards'/filename)
            if item.get('Manuscript prose','')!=parsed['fields'].get('Manuscript prose',''):raise ValueError('Migration prose verification failed; the original database is unchanged.')
        for id,filename in source_names.items():
            if (stage/filename).read_text(encoding='utf-8')!=paper.cards[id]['raw']:raise ValueError('Source-card verification failed.')
        os.rename(stage,destination)
        config=ws.config();config['legacy_paper_id']=result['paper_id'];atomic_write(ws.config_path,json.dumps(config,indent=2))
        return ws.get(result['paper_id'])
