"""Import a linked card package as a paper's next working outline.

The package is data. Its prose is never executed, and earlier cards are retained.
"""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote
from zipfile import ZipFile, BadZipFile
import hashlib
import io
import json
import os
import re
import stat
import uuid

from .workspace import Conflict, atomic_write, fields_of, frontmatter, sha, split_note
from scripts.create_paper_workspace import portable_name

LINK = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)')


def binary_write(path, raw):
    """Publish new material only; a retry cannot replace edited material."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('An existing import file differs: '+path.name)
        return
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def relative_link(path, base):
    return quote(os.path.relpath(path, base).replace(os.sep, '/'), safe='/')


def local_target(source, target):
    raw = unquote(target.split('#', 1)[0])
    if not raw or '://' in raw or raw.startswith('#'):
        return None
    if ':' in raw or '\\' in raw or raw.startswith('/'):
        raise ValueError('Use relative file links in the package: '+target)
    parts = list(PurePosixPath(source).parent.parts)
    for part in raw.split('/'):
        if part == '..':
            if not parts: raise ValueError('A package link leaves its folder: '+target)
            parts.pop()
        elif part not in ('', '.'):
            parts.append(part)
    return '/'.join(parts)


def unpack(raw):
    if len(raw) > 16_000_000: raise ValueError('The card ZIP must be smaller than 16 MB.')
    files = {}
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > 64_000_000:
                raise ValueError('The card ZIP expands beyond the import limit.')
            for e in entries:
                path = PurePosixPath(e.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in e.filename or ':' in e.filename:
                    raise ValueError('Unsafe archive path.')
                if stat.S_ISLNK(e.external_attr >> 16): raise ValueError('Archive links are not supported.')
                if e.is_dir() or '__MACOSX' in path.parts or path.name == '.DS_Store': continue
                if e.file_size > 16_000_000: raise ValueError('A package file is too large.')
                if e.filename.casefold() in {p.casefold() for p in files}: raise ValueError('Duplicate archive filename.')
                files[e.filename] = archive.read(e)
    except BadZipFile as error:
        raise ValueError('Choose a valid ZIP of argument cards.') from error
    if files and all('/' in name for name in files) and len({name.split('/')[0] for name in files}) == 1:
        files = {name.split('/', 1)[1]:value for name,value in files.items()}
    return files


def prepare(workspace, paper_id, raw, label):
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 120:
        raise ValueError('Name the outline revision in 1–120 characters.')
    root = workspace.locate(paper_id)
    plan = workspace.read(root)
    workspace.tree(plan)
    digest = hashlib.sha256(raw).hexdigest()
    receipt_path = workspace.safe(root.parent/'Outline versions'/('Import '+digest[:16]+'.json'))
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('package_hash') != digest: raise ValueError('Import identity mismatch.')
        return {'already_imported':True, 'receipt':receipt}
    files = unpack(raw)
    roots = [name for name in files if '/' not in name and name.casefold().replace('_',' ') == 'paper outline.md']
    if len(roots) != 1: raise ValueError('Include one Paper outline.md or Paper_outline.md at the package root.')
    source_root = roots[0]
    cards = {}
    used_ids = {workspace.read(p)['id'] for p in (root.parent/'Cards').glob('*.md')}
    used_names = {p.name.casefold() for p in (root.parent/'Cards').glob('*.md')}
    for name, value in files.items():
        if PurePosixPath(name).parent != PurePosixPath('Cards') or not name.endswith('.md'): continue
        meta, body = split_note(value.decode('utf-8'))
        fields_of(body)
        if meta.get('awl_kind') != 'card' or meta.get('card_type') not in ('argument','section','subsection'):
            raise ValueError('Unsupported card type: '+name)
        id = meta.get('awl_id')
        if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',id): raise ValueError('Invalid card identity.')
        if id in used_ids: raise ValueError('A card identity is already present. Import fresh revision cards: '+name)
        if meta.get('paper_id') != paper_id: raise ValueError('The package belongs to a different paper.')
        used_ids.add(id)
        title_match = re.search(r'^# (.+)$',body,re.M)
        if not title_match: raise ValueError('A card needs a title: '+name)
        title = re.sub(r'^(Argument|Paragraph|Section|Subsection)\s*[-·]\s*','',title_match[1]).replace(' - ',' · ',1)
        stem = portable_name(meta['card_type'].capitalize()+' - '+title)
        filename = stem+'.md'
        if filename.casefold() in used_names:
            suffix = ' - '+portable_name(label)[:35]
            revision_stem = stem[:90-len(suffix)].rstrip()+suffix
            filename = revision_stem+'.md'
            number = 2
            while filename.casefold() in used_names:
                suffix = ' ('+str(number)+')'
                filename = revision_stem[:90-len(suffix)]+suffix+'.md'
                number += 1
        used_names.add(filename.casefold())
        body = body[:title_match.start(1)]+title+body[title_match.end(1):]
        previous = re.findall(r'previous card ID:\s*`([A-Za-z0-9_-]+)`',body)
        meta = {**meta,'outline_revision':label.strip(),'source_package_hash':digest,'previous_card_ids':previous}
        meta.pop('awl_revision',None)
        cards[name] = {'meta':meta,'body':body,'filename':filename,'title':title}
    if not cards: raise ValueError('The package has no argument cards.')
    # The supplied outline orders the section link and its argument links.
    order = []; seen = set(); parent = None
    for _, target in LINK.findall(files[source_root].decode('utf-8')):
        name = local_target(source_root,target)
        if name not in cards: continue
        if name in seen: raise ValueError('A card is repeated in the outline: '+name)
        seen.add(name); kind = cards[name]['meta']['card_type']
        if kind == 'section': depth = 0; parent = 'section'
        elif kind == 'subsection':
            if parent not in ('section','subsection'): raise ValueError('A subsection needs a section.')
            depth = 1; parent = 'subsection'
        else: depth = 2 if parent == 'subsection' else 1 if parent else 0
        order.append((depth,name))
    if seen != set(cards): raise ValueError('Every package card must have one link in its root outline.')
    for name, value in files.items():
        if name.endswith('.md'):
            for _, target in LINK.findall(value.decode('utf-8')):
                linked = local_target(name,target)
                if linked is not None and linked not in files: raise ValueError('A linked package file is missing: '+linked)
    return {'already_imported':False,'root':root,'base_hash':plan['hash'],'plan':plan,'files':files,
            'cards':cards,'order':order,'source_root':source_root,'package_hash':digest,
            'label':label.strip(),'raw':raw,'receipt_path':receipt_path}


def snapshot(workspace, plan, label, digest):
    root = Path(plan['path']); folder = root.parent
    destination = workspace.safe(folder/'Outline versions'/('Before '+portable_name(label)))
    if destination.exists(): raise ValueError('An outline snapshot with this name already exists. Choose a different revision name.')
    originals = {root:root.read_bytes(), **{p:p.read_bytes() for p in (folder/'Cards').glob('*.md')}}
    records = {str(p.relative_to(folder)):hashlib.sha256(raw).hexdigest() for p,raw in originals.items()}
    for path, raw in originals.items():
        target = destination/path.relative_to(folder)
        text = raw.decode('utf-8')
        def rewrite(match):
            old = match[2]
            if '://' in old or old.startswith('#'): return match[0]
            resolved = (path.parent/unquote(old.split('#',1)[0])).resolve()
            if resolved in originals: resolved = destination/resolved.relative_to(folder)
            return '['+match[1]+']('+relative_link(resolved,target.parent)+('#'+old.split('#',1)[1] if '#' in old else '')+')'
        text = LINK.sub(rewrite,text)
        if path == root:
            meta,body = split_note(text)
            text = frontmatter({**meta,'awl_kind':'outline_snapshot'})+body
        binary_write(target,text.encode('utf-8'))
    backup = io.BytesIO()
    with ZipFile(backup,'w') as archive:
        for path, raw in originals.items(): archive.writestr(str(path.relative_to(folder)),raw)
    binary_write(destination/'Original cards and outline.zip',backup.getvalue())
    manifest = {'schema':'awl.outline-snapshot.v1','id':str(uuid.uuid5(uuid.NAMESPACE_URL,plan['id']+digest)),
                'paper_id':plan['id'],'label':'Before '+label,'created':datetime.now(timezone.utc).isoformat(),
                'root':root.name,'original_hashes':records,
                'files':{str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*.md')}}
    binary_write(destination/'manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    return destination, manifest


def apply(workspace, prepared):
    if prepared['already_imported']: return {**prepared['receipt'],'already_imported':True}
    p = prepared; root = p['root']; folder = root.parent
    with workspace.lock:
        plan = workspace.get(p['plan']['id'])
        if plan['hash'] != p['base_hash']: raise Conflict('The outline changed after import preview. Preview it again.')
        if plan['conflict']: raise Conflict('Compare the existing outline versions before importing.')
        snapshot_dir, before = snapshot(workspace,plan,p['label'],p['package_hash'])
        material = workspace.safe(folder/'Revision materials'/portable_name(p['label']))
        destinations = {name:material/name for name in p['files']}
        destinations[p['source_root']] = root
        destinations.update({name:folder/'Cards'/card['filename'] for name,card in p['cards'].items()})
        def rewritten(name, text):
            def replace(match):
                source = local_target(name,match[2])
                if source is None: return match[0]
                link = relative_link(destinations[source],destinations[name].parent)
                if '#' in match[2]: link += '#'+match[2].split('#',1)[1]
                return '['+match[1]+']('+link+')'
            return LINK.sub(replace,text)
        for name, raw in p['files'].items():
            if name == p['source_root']: continue
            if name in p['cards']:
                card = p['cards'][name]
                raw = (frontmatter(card['meta'])+rewritten(name,card['body'])).encode('utf-8')
            elif name.endswith('.md'):
                raw = rewritten(name,raw.decode('utf-8')).encode('utf-8')
            binary_write(workspace.safe(destinations[name]),raw)
        binary_write(material/'Original card package.zip',p['raw'])
        # Detect any author edit made while the snapshot was being prepared.
        for relative, checksum in before['original_hashes'].items():
            if hashlib.sha256((folder/relative).read_bytes()).hexdigest() != checksum:
                raise Conflict('Writing changed during import. Earlier text and imported files are kept; the new outline was not activated.')
        outline = '\n'.join('    '*depth+'- ['+p['cards'][name]['meta']['card_type'].capitalize()+': '+p['cards'][name]['title']+']('+relative_link(destinations[name],folder)+')' for depth,name in p['order'])
        resources = ['[Earlier outline]('+relative_link(snapshot_dir/root.name,folder)+')',
                     '[Original card package]('+relative_link(material/'Original card package.zip',folder)+')']
        for name in p['files']:
            if name.startswith('Guide/') and name.endswith('.md'):
                resources.append('['+PurePosixPath(name).stem.replace('_',' ')+']('+relative_link(destinations[name],folder)+')')
        changes = {'Argument order':outline,'Outline revision':p['label']+' · Proposal; agreement is not recorded by this import.',
                   'Revision resources':' · '.join(resources)}
        saved = workspace.save(plan['id'],plan['id'],plan['hash'],changes)
        receipt = {'paper_id':plan['id'],'package_hash':p['package_hash'],'label':p['label'],
                   'created':datetime.now(timezone.utc).isoformat(),'outline_hash':saved['hash'],
                   'earlier_outline_id':before['id'],'arguments':sum(c['meta']['card_type']=='argument' for c in p['cards'].values()),
                   'sections':sum(c['meta']['card_type']=='section' for c in p['cards'].values())}
        binary_write(p['receipt_path'],json.dumps(receipt,ensure_ascii=False,indent=2).encode('utf-8'))
        return receipt


def history(workspace, paper_id, version_id=None):
    folder = workspace.locate(paper_id).parent
    versions = []
    for file in workspace.safe(folder/'Outline versions').glob('*/manifest.json'):
        manifest = json.loads(workspace.safe(file).read_text())
        if manifest.get('schema') != 'awl.outline-snapshot.v1' or manifest.get('paper_id') != paper_id: continue
        if version_id is not None and manifest['id'] != version_id: continue
        value = {key:manifest[key] for key in ('id','label','created')}
        if version_id is not None:
            for name, checksum in manifest['files'].items():
                path = workspace.safe(file.parent/name)
                if not path.resolve().is_relative_to(file.parent.resolve()): raise ValueError('Invalid snapshot path.')
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                    raise ValueError('This earlier outline is incomplete or changed. Let Sync finish or check its backup.')
            root = workspace.safe(file.parent/manifest['root'])
            if root.parent != file.parent: raise ValueError('Invalid snapshot root.')
            note = workspace.read(root)
            value.update(outline=workspace.public(note),nodes=[workspace.public(n) for n in workspace.tree(note)])
        versions.append(value)
    if version_id is not None:
        if len(versions) != 1: raise ValueError('Earlier outline not found or duplicated.')
        return versions[0]
    return sorted(versions,key=lambda v:v['created'],reverse=True)
