"""Readable paper records shared through a user-selected Obsidian vault.

The current Markdown and immutable revisions live together. A local process lock
serializes writes; base hashes and revision parents detect external/concurrent edits.
No SQLite file is placed in the vault.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlencode
import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
import yaml

from scripts.create_paper_workspace import (ALL_FIELDS, CARD_FIELDS, STRUCTURE_FIELDS,
    create_paper, link_label, portable_name, read_outline, unique_name)

# These optional side notes use the same revision and conflict protection as prose.
# Keep them out of the empty-paper template so a new paper stays uncluttered.
SUPPORT_FIELDS = ('Supervisor comments and editing consequences',
                  'Academic reviewer guidance', 'Flow and wording notes', 'Opening options',
                  'Writing outline', 'Section writing plan', 'Section writing stage',
                  'Section manuscript source', 'Writing scaffold', 'Outline provenance', 'Outline figures',
                  'Writing intention', 'Next writing action', 'Active writing idea', 'Writing goal origin', 'Writing goal stage')


def frontmatter(values):
    return '---\n'+yaml.safe_dump(values,sort_keys=False,allow_unicode=True).rstrip()+'\n---\n\n'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def note_content(text):
    meta,body=split_note(text)
    meta.pop('awl_revision',None)
    return sha(frontmatter(meta)+body.lstrip('\n'))


class Conflict(ValueError):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


class NoteLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError('Duplicate or invalid note property. Resolve it in Obsidian before saving.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


NoteLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def split_note(text):
    text = text.replace('\r\n', '\n')
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise ValueError('The note needs its document properties at the top.')
    try:
        meta = yaml.load(match.group(1), Loader=NoteLoader)
    except yaml.YAMLError as error:
        raise ValueError('The note properties could not be read. Check them in Obsidian.') from error
    if not isinstance(meta, dict) or meta.get('awl_schema') != 1:
        raise ValueError('Unsupported workspace note version.')
    return meta, text[match.end():]


def section_spans(body):
    """Recognise headings outside fenced code; preserve unknown sections verbatim."""
    headings = []; offset = 0; fence = None
    for line in body.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None: fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip(): fence = None
        elif fence is None:
            match = re.fullmatch(r'## (.+?)\s*\n?', line)
            if match: headings.append((match.group(1).strip(), offset, offset + len(line)))
        offset += len(line)
    spans = {}
    for i, (name, start, content_start) in enumerate(headings):
        if name in spans: raise ValueError('Duplicate section heading: '+name+'. Keep both texts but give each heading a distinct name.')
        spans[name] = (start, content_start, headings[i+1][1] if i+1 < len(headings) else len(body))
    return spans


def fields_of(body):
    return {name: body[start:end].strip() for name, (_, start, end) in section_spans(body).items()}


def update_fields(body, changes):
    for name, value in changes.items():
        spans = section_spans(body)
        if name in spans:
            _, start, end = spans[name]
            body = body[:start] + '\n' + value.strip() + '\n\n' + body[end:]
        else:
            body = body.rstrip() + '\n\n## ' + name + '\n\n' + value.strip() + '\n\n'
    return body


def atomic_write(path, text, *, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        if exclusive:os.link(name,path)
        else:os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
    if os.name != 'nt':
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)


class Workspace:
    folder = '06_Academic_Writing_Lab/Papers'

    def __init__(self, lab):
        self.lab = lab
        self.lock = threading.RLock()
        self.config_path = lab.store.directory/'local-settings.json'

    def config(self):
        try: return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (OSError, ValueError): return {}

    def configure(self, vault):
        path = Path(vault).expanduser().resolve()
        if not path.is_dir(): raise ValueError('Choose an existing Obsidian vault folder on this computer.')
        if not (path/'.obsidian').is_dir(): raise ValueError('This folder is not an Obsidian vault. Select the folder containing .obsidian.')
        self.lab.vault = path
        atomic_write(self.config_path, json.dumps({**self.config(), 'vault':str(path), 'workspace_enabled':True}, indent=2))
        self.safe(path/self.folder).mkdir(parents=True, exist_ok=True)
        return self.status()

    def safe(self, path):
        path = Path(path)
        vault = self.lab.vault.resolve()
        if not path.resolve().is_relative_to(vault): raise ValueError('Workspace files must stay inside the selected vault.')
        for parent in [path, *path.parents]:
            if parent == vault: break
            if parent.is_symlink(): raise ValueError('Symbolic links are not supported inside a paper workspace.')
        return path

    @property
    def root(self):
        return self.safe(self.lab.vault/self.folder)

    def status(self):
        return {'enabled':bool(self.config().get('workspace_enabled')), 'available':self.lab.vault.is_dir(),
                'vault':str(self.lab.vault), 'folder':self.folder,
                'sync':'Files are saved to this local vault. Obsidian Sync delivery to other devices is not verified here.'}

    def require_enabled(self):
        if not self.config().get('workspace_enabled'): raise ValueError('Choose your Obsidian vault in My papers first.')
        if not self.lab.vault.is_dir(): raise ValueError('The selected vault is unavailable. Your editor draft is kept in this browser.')

    def uri(self, path):
        return 'obsidian://open?' + urlencode({'vault':self.lab.vault.name,'file':path.relative_to(self.lab.vault).as_posix()})

    def read(self, path):
        path = self.safe(path)
        if path.stat().st_size > 8_000_000: raise ValueError('This note is too large to edit safely in one card.')
        raw = path.read_text(encoding='utf-8')
        meta, body = split_note(raw)
        title = re.search(r'^# (.+)$', body, re.M)
        value = {'id':meta.get('awl_id'), 'title':title.group(1) if title else path.stem,
                 'type':meta.get('card_type', meta.get('awl_kind')), 'fields':fields_of(body),
                 'hash':sha(raw), 'path':str(path), 'filename':path.name, 'uri':self.uri(path), 'meta':meta,
                 '_raw':raw, '_body':body}
        if value['type'] == 'paragraph': value['type'] = 'argument'
        prose = value['fields'].get('Manuscript prose', '').strip()
        value['writing_status'] = ('complete' if prose and value['fields'].get('Completed prose hash') == sha(prose)
                                   else 'draft' if prose else 'empty')
        value['vault_path'] = path.relative_to(self.lab.vault).as_posix()
        if value['type'] in ('section','subsection','argument'):
            value['title'] = re.sub(r'^(Section|Subsection|Paragraph|Argument)\s*·\s*','',value['title'])
        if not isinstance(value['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value['id']):
            raise ValueError('Set awl_id to a unique stable key, such as coastal-study or coastal-study-introduction (letters, numbers, hyphens or underscores). Replace any <paper-key> template placeholder first.')
        return value

    @staticmethod
    def public(value):
        return {k:v for k,v in value.items() if not k.startswith('_')}

    def catalogue(self):
        status = self.status(); papers = []; issues = []; identities = {}
        if not status['enabled'] or not status['available']: return {**status,'papers':[], 'issues':[]}
        paths=list(self.root.glob('*/*.md'))
        for registration in (self.lab.vault/'06_Academic_Writing_Lab'/'Projects').glob('*.md'):
            try:
                meta,_=split_note(self.safe(registration).read_text(encoding='utf-8'))
                directory=self.safe(self.lab.vault/meta['paper_folder'])
                if not directory.is_dir():raise ValueError('Waiting for the paper folder to sync: '+str(directory))
                paths.extend(directory.glob('*.md'))
            except (ValueError,OSError,KeyError) as error:issues.append(str(error))
        for path in sorted(set(paths)):
            if path.parent.name.startswith('.'):continue
            try:
                raw = self.safe(path).read_text(encoding='utf-8')
                if not raw.startswith('---\n'):
                    if path.name.casefold() in {'root.md','paper outline.md'}:
                        issues.append(str(path)+': Add the paper template properties at the top: awl_kind: paper and a unique awl_id. See the manual paper folder guide.')
                    continue
                header = re.match(r'\A---\n(.*?)\n---\n', raw, re.S)
                if not header: raise ValueError('The note properties are not closed with --- on their own line.')
                try: meta = yaml.load(header.group(1), Loader=NoteLoader)
                except yaml.YAMLError as error: raise ValueError('The note properties could not be read. Check them in Obsidian.') from error
                if not isinstance(meta, dict): continue
                if meta.get('awl_kind') != 'paper':
                    if path.name.casefold() == 'root.md' and meta.get('awl_kind') != 'template':
                        issues.append(str(path)+': Set awl_kind: paper in the root note properties so the folder can appear in Papers.')
                    continue
                note = self.read(path)
                if note['id'] in identities:
                    issues.append('Duplicate paper identity: '+str(path)+'. Keep both folders. For a new paper, use a fresh blank template with another paper key; its cards need the matching paper_id and their own unique awl_id keys.')
                    papers = [p for p in papers if p['id'] != note['id']]; identities[note['id']] = False
                    continue
                identities[note['id']] = True
                papers.append({k:note[k] for k in ('id','title','filename','uri','path')})
            except (ValueError, OSError) as error: issues.append(str(path)+': '+str(error))
        return {**status,'papers':papers,'issues':issues}

    def open_folder(self,folder):
        self.require_enabled()
        directory=Path(folder).expanduser()
        if not directory.is_absolute():directory=self.lab.vault/directory
        directory=self.safe(directory.resolve())
        if not directory.is_dir():raise ValueError('Choose an existing paper folder inside your selected vault.')
        papers=[]
        for path in directory.glob('*.md'):
            raw=self.safe(path).read_text(encoding='utf-8')
            if not raw.startswith('---\n'):continue
            try:note=self.read(path)
            except ValueError:continue
            if note['meta'].get('awl_kind')=='paper':papers.append(note)
        if len(papers)!=1:raise ValueError('The folder needs one root paper card with an outline linking its section and argument cards. Use the supplied Paper outline template, or import a plain outline through New paper.')
        note=papers[0];self.tree(note)
        registrations=self.safe(self.lab.vault/'06_Academic_Writing_Lab'/'Projects');registrations.mkdir(parents=True,exist_ok=True)
        relative=directory.relative_to(self.lab.vault).as_posix()
        for path in registrations.glob('*.md'):
            meta,_=split_note(path.read_text(encoding='utf-8'))
            if meta.get('paper_folder')==relative:return self.get(note['id'])
        filename=unique_name(note['title'],{p.stem.casefold() for p in registrations.glob('*.md')})+'.md'
        text=frontmatter({'awl_schema':1,'awl_kind':'project_link','paper_folder':relative,'paper_id':note['id']})+'# '+note['title']+'\n\n[Open paper outline]('+quote(os.path.relpath(note['path'],registrations).replace(os.sep,'/'))+')\n'
        atomic_write(registrations/filename,text,exclusive=True)
        return self.get(note['id'])

    def replace_note(self,directory,note,raw):
        """Retain the file actually displaced; never overwrite a recreated path.

        Hard links publish only complete files on APFS/NTFS. Keeping the displaced
        inode also retains writes made through an editor's already-open handle.
        A crash between move and publication leaves a recoverable missing note.
        """
        path=self.safe(Path(note['path']))
        recovery=self.safe(directory/'Recovered files'/path.stem)
        recovery.mkdir(parents=True,exist_ok=True)
        kept=recovery/(datetime.now(timezone.utc).strftime('%Y-%m-%d %H%M%S.%f')+' - '+str(uuid.uuid4())[:8]+'.md')
        os.rename(path,kept)
        try:atomic_write(path,raw,exclusive=True)
        except Exception:
            if not path.exists():
                try:os.link(kept,path)
                except OSError:pass
            raise Conflict('The note could not be published safely. The displaced text is in Recovered files; both versions are kept.',kept_path=str(kept))
        if sha(kept.read_text(encoding='utf-8'))!=note['hash']:
            raise Conflict('An external edit arrived during the save. It is retained in Recovered files. Reload and compare before continuing.',kept_path=str(kept))

    def locate(self, paper_id):
        self.require_enabled()
        matches = [p for p in self.catalogue()['papers'] if p['id'] == paper_id]
        if len(matches) != 1: raise ValueError('Paper not found or its identity is duplicated. Check the workspace inbox in My papers.')
        return Path(matches[0]['path'])

    def tree(self, note):
        directory = Path(note['path']).parent
        ordered = note['fields'].get('Argument order', note['fields'].get('Argument outline',''))
        nodes = []; stack = []; seen = set()
        for line in ordered.splitlines():
            match = re.match(r'^( *)(?:[-*]|\d+\.)\s+\[(.*?)\]\(([^)]+)\)\s*$',line)
            if not match:
                if line.strip() and not line.lstrip().startswith('<!--'):
                    raise ValueError('The argument outline needs one linked card per list item. Check: '+line[:120])
                continue
            indent, _, target = match.groups()
            path = self.safe(directory/unquote(target))
            if path.parent != directory/'Cards': raise ValueError('Outline links must point directly to this paper’s Cards folder.')
            if not path.is_file(): raise ValueError('Waiting for a linked card: '+path.name+'. Let Obsidian Sync finish or repair its outline link.')
            card = self.read(path)
            if card['meta'].get('paper_id') != note['id']: raise ValueError('A linked card belongs to another paper: '+path.name)
            if card['id'] in seen: raise ValueError('A card appears more than once in the outline: '+card['title'])
            seen.add(card['id'])
            while stack and stack[-1][0] >= len(indent): stack.pop()
            parent = stack[-1][1] if stack else None
            parent_kind = next((n['type'] for n in nodes if n['id']==parent), None)
            if (card['type']=='section' and parent is not None or
                    card['type']=='subsection' and parent_kind!='section' or
                    card['type']=='argument' and parent_kind not in (None,'section','subsection') or
                    card['type'] not in ('section','subsection','argument')):
                raise ValueError('Check the section → subsection → argument hierarchy for '+card['title'])
            card['parent_id'] = parent; card['depth'] = len(stack)
            nodes.append(card); stack.append((len(indent),card['id']))
        # Duplicate files can arrive through Sync even when only one is linked.
        identities = {}
        for path in (directory/'Cards').glob('*.md'):
            card = self.read(path)
            if card['id'] in identities: raise ValueError('Two card files have the same identity: '+path.name+'. Keep both and resolve the duplicate before editing.')
            identities[card['id']] = path
        return nodes

    def revisions(self, directory, document_id):
        result = {}
        for path in self.safe(directory/'Revisions').glob('*.md'):
            raw = self.safe(path).read_text(encoding='utf-8')
            try:meta, body = split_note(raw)
            except ValueError:
                # A partially synced foreign revision cannot block every card.
                # A referenced missing revision is detected by observe().
                continue
            if meta.get('document_id') != document_id: continue
            marker = '## Saved note\n\n'
            if marker not in body: raise ValueError('An incomplete revision is arriving: '+path.name)
            text = body.split(marker,1)[1]
            if sha(text) != meta.get('content_hash'): raise ValueError('A revision is incomplete or changed: '+path.name)
            record = {**meta,'text':text,'path':str(path)}
            prior = result.get(meta['awl_id'])
            if prior and (prior['text']!=text or prior.get('parents')!=meta.get('parents')):
                raise ValueError('Conflicting copies of one revision were found.')
            result[meta['awl_id']] = record
        represented={note_content(r['text']) for r in result.values()}
        for path in self.safe(directory/'Recovered files').glob('*/*.md'):
            raw=self.safe(path).read_text(encoding='utf-8')
            try:meta,_=split_note(raw)
            except ValueError:continue
            if meta.get('awl_id')!=document_id or note_content(raw) in represented:continue
            # A first-adoption file handle may receive a later external write.
            # Unchanged templates were excluded above; keep changed roots too.
            parent=meta.get('awl_revision')
            note=self.read(path)
            r=self.record(directory,note,raw,[parent] if parent else [],origin='displaced_external_edit')
            result[r['awl_id']]=r
            represented.add(note_content(raw))
        return result

    def record(self, directory, note, raw, parents, origin='app', revision_id=None):
        revision_id = revision_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        meta = {'awl_schema':1,'awl_kind':'revision','awl_id':revision_id,'document_id':note['id'],
                'parents':parents,'content_hash':sha(raw),'created':now.isoformat(),'origin':origin}
        filename = now.strftime('%Y-%m-%d %H%M%S.%f')+' - '+portable_name(note['title'])[:50]+' - '+revision_id[:8]+'.md'
        path = self.safe(directory/'Revisions'/filename)
        text = frontmatter(meta)+'# '+note['title']+' — saved version\n\n## Saved note\n\n'+raw
        atomic_write(path, text, exclusive=True)
        return {**meta,'path':str(path),'text':raw}

    def observe(self, directory, note):
        records = self.revisions(directory, note['id'])
        declared = note['meta'].get('awl_revision')
        if not declared and not records:
            # Adopt an unversioned template once. Subsequent external edits retain
            # this parent marker, distinguishing a sequential edit from a fork.
            revision = str(uuid.uuid4())
            raw = frontmatter({**note['meta'],'awl_revision':revision})+note['_body']
            self.record(directory,note,raw,[],origin='template_adoption',revision_id=revision)
            if sha(Path(note['path']).read_text(encoding='utf-8'))!=note['hash']:
                raise Conflict('The note changed while being opened. Both versions are kept; reload before editing.')
            self.replace_note(directory,note,raw)
            note.update(self.read(Path(note['path'])))
            records = self.revisions(directory,note['id']);declared=revision
        if declared and declared not in records:
            raise ValueError('This note arrived before its saved revision. Let Obsidian Sync finish before editing.')
        matched = [r for r in records.values() if r['content_hash']==note['hash']]
        if not matched:
            # Stamp an observed external edit with its own parent marker. Leaving
            # the old marker here would make a later ordinary Obsidian edit look
            # like an offline sibling of this one.
            revision = str(uuid.uuid4())
            raw = frontmatter({**note['meta'],'awl_revision':revision})+note['_body']
            r = self.record(directory, note, raw, [declared] if declared else [], origin='observed_note', revision_id=revision)
            if sha(Path(note['path']).read_text(encoding='utf-8'))!=note['hash']:
                raise Conflict('The note changed while opening it. Both versions are kept; reload to compare.')
            self.replace_note(directory,note,raw)
            note.update(self.read(Path(note['path'])))
            records[r['awl_id']] = r; matched = [r]
        # Equal observed content is not a disagreement; still retain its records.
        current = next((r for r in matched if r['awl_id']==declared), matched[-1])
        parents = {p for r in records.values() for p in r.get('parents',[])}
        if any(p not in records for p in parents): raise ValueError('Some parent revisions have not arrived yet. Let Sync finish before editing.')
        heads = [r for id,r in records.items() if id not in parents]
        note['revision_id'] = current['awl_id']
        note['heads'] = [{'id':r['awl_id'],'created':r['created'],'hash':r['content_hash'],'path':r['path']} for r in heads]
        note['conflict'] = len({r['content_hash'] for r in heads})>1 or current['awl_id'] in parents
        return note

    def get(self, paper_id):
        with self.lock:
            path = self.locate(paper_id); note = self.read(path)
            nodes = self.tree(note)
            note = self.observe(path.parent, note)
            linked = {n['id'] for n in nodes}
            unplaced = [self.public(self.read(p)) for p in (path.parent/'Cards').glob('*.md') if self.read(p)['id'] not in linked]
            return {**self.public(note),'nodes':[self.public(n) for n in nodes], 'unplaced':unplaced, 'sync':self.status()['sync']}

    def card(self, paper_id, card_id):
        with self.lock:
            path = self.locate(paper_id); plan = self.read(path); nodes = self.tree(plan)
            note = next((n for n in nodes if n['id']==card_id),None)
            if not note: raise ValueError('Argument card not found in this paper outline.')
            note = self.observe(path.parent, note)
            siblings = [n for n in nodes if n['parent_id']==note['parent_id']]
            index = next(i for i,n in enumerate(siblings) if n['id']==card_id)
            brief = lambda n: {k:n[k] for k in ('id','title','type','fields')}
            return {**self.public(note),'paper_title':plan['title'], 'plan_hash':plan['hash'],
                    'before':brief(siblings[index-1]) if index else None,
                    'after':brief(siblings[index+1]) if index+1<len(siblings) else None,
                    'parent':next((brief(n) for n in nodes if n['id']==note['parent_id']),None),
                    'children':[brief(n) for n in nodes if n['parent_id']==card_id]}

    def save(self, paper_id, document_id, base_hash, changes, merge_heads=None, title=None):
        with self.lock:
            if title is not None and (document_id == paper_id or not isinstance(title, str)
                                      or not title.strip() or len(title) > 300
                                      or '\n' in title or '\r' in title):
                raise ValueError('Use a single-line card title of up to 300 characters.')
            if merge_heads is not None and (not isinstance(merge_heads,list) or any(not isinstance(h,str) for h in merge_heads)):
                raise ValueError('Include the list of compared versions.')
            path = self.locate(paper_id); plan = self.read(path)
            note = plan if document_id==paper_id else next((n for n in self.tree(plan) if n['id']==document_id),None)
            if not note: raise ValueError('Card not found.')
            allowed = set(ALL_FIELDS + SUPPORT_FIELDS) if document_id!=paper_id else {'Research question','Intended contribution','Agreed plan and open questions','Next writing session','Argument order','Outline revision','Revision resources'}
            if not isinstance(changes,dict) or set(changes)-allowed or any(not isinstance(v,str) or len(v)>60000 for v in changes.values()):
                raise ValueError('Invalid note fields or field too long.')
            if 'Section manuscript source' in changes:
                if note['type'] not in ('section','subsection') or changes['Section manuscript source'] not in ('arguments','section'):
                    raise ValueError('Choose arguments or section as the manuscript source of a section card.')
            if 'Section writing stage' in changes and changes['Section writing stage'] not in ('connect','rewrite','polish'):
                raise ValueError('Choose connect, rewrite or polish as the section writing stage.')
            if 'Writing goal origin' in changes and changes['Writing goal origin'] not in ('','own','outline'):
                raise ValueError('Choose own or outline as the writing goal origin.')
            if 'Writing goal stage' in changes and changes['Writing goal stage'] not in ('','connect','rewrite','polish'):
                raise ValueError('Choose a valid writing goal stage.')
            if 'Active writing idea' in changes and changes['Active writing idea']:
                from .section_writing import parse_steps
                steps=parse_steps(changes.get('Section writing plan',note['fields'].get('Section writing plan','')))
                if note['type'] not in ('section','subsection') or changes['Active writing idea'] not in {s['id'] for s in steps}:
                    raise ValueError('Choose an existing idea from this section writing plan.')
            if 'Section writing plan' in changes:
                from .section_writing import parse_steps
                parse_steps(changes['Section writing plan'])
            note = self.observe(path.parent, note)
            proposed_body = update_fields(note['_body'],changes)
            if title is not None:
                proposed_body, replaced = re.subn(r'^# [^\n]*', lambda _: '# '+title.strip(),
                                                   proposed_body, count=1, flags=re.M)
                if not replaced: raise ValueError('The card has no title heading to update.')
            parsed_fields = fields_of(proposed_body)
            if any(parsed_fields.get(k) != v.strip() for k,v in changes.items()):
                raise ValueError('Use ### for headings inside a field. A ## heading starts a separate note field; your editor text has been kept.')
            if note['hash'] != base_hash:
                kept = self.record(path.parent,note,frontmatter(note['meta'])+proposed_body,[],origin='stale_editor_proposal')
                raise Conflict('The vault note changed. Your proposed text was kept as a separate version. Compare before replacing anything.', kept_path=kept['path'])
            heads = {r['id'] for r in note['heads']}
            if note['conflict'] and set(merge_heads or [])!=heads:
                raise Conflict('There are competing saved versions. Compare them before choosing a merged version.', heads=note['heads'])
            if merge_heads is not None and set(merge_heads)!=heads: raise Conflict('The competing versions changed. Reload the comparison.')
            if proposed_body==note['_body'] and not note['conflict']: return self.public(note)
            revision = str(uuid.uuid4()); meta = {**note['meta'],'awl_revision':revision}
            raw = frontmatter(meta)+proposed_body
            candidate = {**note,'_raw':raw,'_body':proposed_body,'fields':fields_of(proposed_body)}
            if document_id==paper_id: self.tree(candidate)
            self.record(path.parent,note,raw,sorted(heads) if merge_heads else [note['revision_id']], revision_id=revision)
            # Recheck after the durable revision; an external writer may have intervened.
            if sha(self.safe(Path(note['path'])).read_text(encoding='utf-8')) != base_hash:
                raise Conflict('The vault changed while saving. Both versions are kept; reload and compare.')
            self.replace_note(path.parent,note,raw)
            return self.public(self.observe(path.parent,self.read(Path(note['path']))))

    def history(self, paper_id, document_id):
        path = self.locate(paper_id)
        return sorted([{**{k:r.get(k) for k in ('awl_id','created','origin','parents','path')},
                         'fields':fields_of(split_note(r['text'])[1])} for r in self.revisions(path.parent,document_id).values()], key=lambda r:r['created'], reverse=True)

    def create(self, title, outline=''):
        self.require_enabled()
        with self.lock:
            self.root.mkdir(parents=True,exist_ok=True)
            used = {p.name.casefold() for p in self.root.iterdir()}
            folder = self.safe(self.root/unique_name(title,used))
            result = create_paper(folder,title,read_outline(outline),outline or None)
            return self.get(result['paper_id'])

    def add_card(self, paper_id, title, kind, parent_id=None):
        with self.lock:
            path = self.locate(paper_id); plan = self.observe(path.parent,self.read(path)); nodes = self.tree(plan)
            if plan['conflict']: raise Conflict('Compare the paper outline versions before adding a card.')
            parent = next((n for n in nodes if n['id']==parent_id),None)
            if parent_id and not parent: raise ValueError('Parent card not found.')
            if (kind=='section' and parent or kind=='subsection' and (not parent or parent['type']!='section') or
                    kind=='argument' and parent and parent['type'] not in ('section','subsection') or kind not in ('section','subsection','argument')):
                raise ValueError('Choose a valid parent section or subsection.')
            if not title.strip() or '\n' in title: raise ValueError('Give the card a short title.')
            directory = self.safe(path.parent/'Cards'); directory.mkdir(exist_ok=True)
            filename = unique_name(kind.capitalize()+' - '+title,{p.stem.casefold() for p in directory.iterdir()})+'.md'
            id = str(uuid.uuid4())
            meta = {'awl_schema':1,'awl_kind':'card','awl_id':id,'card_type':kind,'paper_id':paper_id,'status':'planned','aliases':[title]}
            raw = frontmatter(meta)+'# '+kind.capitalize()+' · '+title+'\n\n[Back to paper](../'+quote(path.name)+')\n\n'
            raw += ''.join('## '+f+'\n\n\n' for f in (CARD_FIELDS if kind=='argument' else STRUCTURE_FIELDS))
            atomic_write(self.safe(directory/filename),raw,exclusive=True)
            new = {'id':id,'title':title,'type':kind,'parent_id':parent_id,'path':str(directory/filename)}
            nodes.append(new)
            def outline(parent_id=None,depth=0):
                result=[]
                for n in nodes:
                    if n['parent_id']!=parent_id: continue
                    result.append('    '*depth+'- ['+link_label(n['type'].capitalize()+': '+n['title'])+'](Cards/'+quote(Path(n['path']).name)+')')
                    result.extend(outline(n['id'],depth+1))
                return result
            self.save(paper_id,paper_id,plan['hash'],{'Argument order':'\n'.join(outline())})
            return self.card(paper_id,id)

    def export(self, paper_id):
        path = self.locate(paper_id); plan = self.read(path)
        lines = ['# '+plan['title'],'']
        nodes = self.tree(plan); by_id = {n['id']:n for n in nodes}
        for card in nodes:
            if card['type'] in ('section','subsection') and card['fields'].get('Section manuscript source','') not in ('','arguments','section'):
                raise ValueError('Choose arguments or section as the manuscript source for '+card['title']+' before export.')
        def section_owned(card):
            parent=card['parent_id']
            while parent:
                if by_id[parent]['fields'].get('Section manuscript source')=='section':return True
                parent=by_id[parent]['parent_id']
            return False
        for card in nodes:
            if section_owned(card):continue
            if card['type'] in ('section','subsection'):
                lines += [('#'*(card['depth']+2))+' '+card['title'],'']
                if card['fields'].get('Section manuscript source')=='section':
                    lines += [card['fields'].get('Manuscript prose',''),'']
            elif card['fields'].get('Manuscript prose'):
                lines += [card['fields']['Manuscript prose'],'']
        return '\n'.join(lines)
