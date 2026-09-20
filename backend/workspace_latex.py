"""Read-only, version-checked export of author-approved manuscript prose.

This module never imports a manuscript into a card, compiles TeX, or updates a
vault revision. Bibliography keys come only from the supplied BibTeX text.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import uuid

from .workspace import Conflict, atomic_write, note_content, sha, split_note
from .springer_template import BIBLIOGRAPHY_FILENAME, TEMPLATE_ID, springer_document


KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/+\-]*\Z')
CITE = re.compile(r'\\(?:citep|citet|cite)\*?(?![A-Za-z])')
ESCAPES = {'&': r'\&', '%': r'\%', '_': r'\_', '#': r'\#', '$': r'\$',
           '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
           '^': r'\textasciicircum{}', '\\': r'\textbackslash{}'}
UNICODE = {'–': '--', '—': '---', '’': "'", '‘': '`', '“': '``', '”': "''",
           '\u00a0': '~', '…': r'\ldots{}'}


def escaped(text, pos):
    i = pos - 1
    while i >= 0 and text[i] == '\\':
        i -= 1
    return (pos - i - 1) % 2 == 1


def group(text, start, opener='{', closer='}'):
    """Return one balanced group, retaining all original bytes."""
    if start >= len(text) or text[start] != opener:
        raise ValueError('Expected '+opener+' in LaTeX or BibTeX text.')
    depth = 1
    for i in range(start + 1, len(text)):
        if escaped(text, i):
            continue
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if not depth:
                return text[start:i+1], i+1
    raise ValueError('An unclosed '+opener+' group needs correction before export.')


def citation(text, start):
    match = CITE.match(text, start)
    if not match:
        return None
    i = match.end()
    while i < len(text) and text[i].isspace():
        i += 1
    for _ in range(2):
        if i < len(text) and text[i] == '[':
            _, i = group(text, i, '[', ']')
            while i < len(text) and text[i].isspace():
                i += 1
    if i >= len(text) or text[i] != '{':
        raise ValueError('A citation needs braces containing its bibliography key, for example \\cite{key}.')
    keys, end = group(text, i)
    keys = [key.strip() for key in keys[1:-1].split(',')]
    if not keys or any(not KEY.fullmatch(key) for key in keys):
        raise ValueError('A citation contains an empty or unsupported bibliography key. Use the exact key from your .bib file.')
    return text[start:end], end, keys


def citation_keys(tex):
    """Ignore TeX comments and verbatim passages when finding citations."""
    keys = set(); i = 0
    while i < len(tex):
        if tex[i] == '%' and not escaped(tex, i):
            end = tex.find('\n', i)
            i = len(tex) if end < 0 else end + 1
            continue
        if tex.startswith(r'\begin{verbatim}', i) or tex.startswith(r'\begin{verbatim*}', i):
            opener = r'\begin{verbatim*}' if tex.startswith(r'\begin{verbatim*}', i) else r'\begin{verbatim}'
            closer = opener.replace('begin', 'end')
            end = tex.find(closer, i + len(opener))
            i = len(tex) if end < 0 else end + len(closer)
            continue
        verb = re.match(r'\\verb\*?(?![A-Za-z])', tex[i:])
        if verb and i + verb.end() < len(tex):
            delimiter = i + verb.end()
            end = tex.find(tex[delimiter], delimiter + 1)
            i = len(tex) if end < 0 else end + 1
            continue
        found = citation(tex, i) if tex[i] == '\\' and not escaped(tex, i) else None
        if found:
            _, i, cited = found
            keys.update(cited)
        else:
            i += 1
    return sorted(keys)


def literal(text):
    return ''.join(ESCAPES.get(char, UNICODE.get(char, char)) for char in text)


def publication_heading(title):
    """Remove only clearly marked outline numbering and draft-state suffixes."""
    clean = re.sub(r'^(?:[IVXLCDM]+(?:-[A-Z])?|\d+(?:\.\d+)*)\s*·\s*', '', title)
    clean = re.sub(r'\s+[—–]\s+meeting draft\s*$', '', clean, flags=re.I).strip()
    return clean or title


def plain_to_latex(text):
    """Escape prose while retaining explicit citations, math and safe escapes."""
    output = []; i = 0
    while i < len(text):
        found = citation(text, i) if text[i] == '\\' else None
        if found:
            raw, i, _ = found
            output.append(raw)
            continue
        math_open = next((m for m in (r'\(', r'\[', '$$', '$') if text.startswith(m, i)), None)
        if math_open:
            closer = {r'\(': r'\)', r'\[': r'\]', '$$': '$$', '$': '$'}[math_open]
            end = i + len(math_open)
            while True:
                end = text.find(closer, end)
                if end < 0 or not escaped(text, end):
                    break
                end += len(closer)
            if end >= 0:
                output.append(text[i:end+len(closer)])
                i = end + len(closer)
                continue
            if math_open != '$':
                raise ValueError('Close the '+math_open+' mathematics before exporting this passage.')
        if text[i] == '\\':
            if i + 1 < len(text) and text[i+1] in '&%_#$\u007b\u007d':
                output.append(text[i:i+2]); i += 2
                continue
            command = re.match(r'\\[A-Za-z]+', text[i:])
            if command or text.startswith((r'\)', r'\]'), i):
                raise ValueError('Plain-text export cannot interpret '+(command.group() if command else text[i:i+2])+'. Choose LaTeX mode for prose that already contains other LaTeX commands.')
        output.append(literal(text[i])); i += 1
    return ''.join(output)


class BibParser:
    """A bounded BibTeX parser with balanced values and duplicate-key checks.

    Values may contain braced/quoted strings, numbers, macros and # joins. Raw
    entries are retained for export; no metadata or citation keys are invented.
    """
    def __init__(self, text):
        if not isinstance(text, str) or len(text) > 2_000_000:
            raise ValueError('Supply BibTeX text up to two million characters.')
        self.text = text.lstrip('\ufeff'); self.pos = 0

    def whitespace(self):
        while self.pos < len(self.text):
            if self.text[self.pos].isspace():
                self.pos += 1
            elif self.text[self.pos] == '%':
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end < 0 else end + 1
            else:
                break

    def token(self, pattern, explanation):
        self.whitespace()
        match = re.match(pattern, self.text[self.pos:])
        if not match:
            raise ValueError('BibTeX near character '+str(self.pos+1)+': '+explanation)
        self.pos += match.end()
        return match.group()

    def value(self):
        parts = []; raw_start = self.pos
        while True:
            self.whitespace()
            if self.pos == len(self.text):
                raise ValueError('A BibTeX value is missing or unfinished.')
            char = self.text[self.pos]
            if char == '{':
                raw, self.pos = group(self.text, self.pos)
                parts.append(('literal', raw[1:-1]))
            elif char == '"':
                start = self.pos; self.pos += 1; depth = 0
                while self.pos < len(self.text):
                    current = self.text[self.pos]
                    if not escaped(self.text, self.pos):
                        if current == '{': depth += 1
                        elif current == '}': depth -= 1
                        elif current == '"' and depth == 0: break
                        if depth < 0: raise ValueError('A quoted BibTeX value has an unmatched brace.')
                    self.pos += 1
                if self.pos == len(self.text):
                    raise ValueError('A quoted BibTeX value is not closed.')
                parts.append(('literal', self.text[start+1:self.pos])); self.pos += 1
            else:
                atom = self.token(r'[A-Za-z0-9_:\-]+', 'expected a braced, quoted, numeric or macro value.')
                parts.append(('literal' if atom.isdigit() else 'macro', atom))
            self.whitespace()
            if self.pos < len(self.text) and self.text[self.pos] == '#':
                self.pos += 1
                continue
            break
        return parts, self.text[raw_start:self.pos]

    def parse(self):
        entries = {}; directives = []; macros = {}
        while True:
            self.whitespace()
            if self.pos == len(self.text): break
            start = self.pos
            kind = self.token(r'@[A-Za-z]+', 'expected @article, @book or another BibTeX entry.')[1:].lower()
            self.whitespace()
            if self.pos >= len(self.text) or self.text[self.pos] not in '{(':
                raise ValueError('A BibTeX entry needs { or ( after its type.')
            opener = self.text[self.pos]; closer = '}' if opener == '{' else ')'; self.pos += 1
            if kind == 'comment':
                _, self.pos = group(self.text, self.pos-1, opener, closer)
                continue
            if kind == 'preamble':
                self.value(); self.whitespace()
                if self.pos >= len(self.text) or self.text[self.pos] != closer:
                    raise ValueError('A BibTeX @preamble is not closed.')
                self.pos += 1
                directives.append(self.text[start:self.pos]); continue
            if kind == 'string':
                name = self.token(r'[A-Za-z][A-Za-z0-9_:\-]*', 'expected a BibTeX string name.').lower()
                self.token(r'=', 'expected = after the string name.')
                value, _ = self.value()
                if name in macros: raise ValueError('Duplicate BibTeX string definition: '+name)
                macros[name] = value
                if self.pos < len(self.text) and self.text[self.pos] == ',': self.pos += 1
                self.whitespace()
                if self.pos >= len(self.text) or self.text[self.pos] != closer:
                    raise ValueError('A BibTeX @string is not closed.')
                self.pos += 1; directives.append(self.text[start:self.pos]); continue
            key = self.token(r'[^\s,{}()]+', 'expected a bibliography key.')
            if not KEY.fullmatch(key): raise ValueError('Unsupported BibTeX key: '+key)
            if key in entries: raise ValueError('Duplicate BibTeX key: '+key+'. Resolve it before inserting or exporting citations.')
            self.token(r',', 'expected a comma after bibliography key '+key+'.')
            fields = {}
            while True:
                self.whitespace()
                if self.pos < len(self.text) and self.text[self.pos] == closer:
                    self.pos += 1; break
                name = self.token(r'[A-Za-z][A-Za-z0-9_\-]*', 'expected a field name or closing '+closer+'.').lower()
                if name in fields: raise ValueError('Duplicate BibTeX field '+name+' in '+key+'.')
                self.token(r'=', 'expected = after BibTeX field '+name+'.')
                fields[name], _ = self.value()
                if self.pos < len(self.text) and self.text[self.pos] == ',':
                    self.pos += 1
                elif self.pos >= len(self.text) or self.text[self.pos] != closer:
                    raise ValueError('A comma or closing '+closer+' is missing in BibTeX entry '+key+'.')
            entries[key] = {'key': key, 'kind': kind, 'raw': self.text[start:self.pos], 'fields': fields}
        return entries, directives, macros


def bibliography_subset(text, keys):
    entries, directives, macros = BibParser(text).parse()
    missing = sorted(set(keys)-entries.keys()); wanted = set(keys)-set(missing)
    warnings = []
    def value(parts, seen=None):
        seen = set(seen or ())
        result = ''
        for kind, item in parts:
            if kind == 'literal': result += item
            elif item.lower() in macros and item.lower() not in seen:
                result += value(macros[item.lower()], seen | {item.lower()})
            else: raise ValueError('Cannot resolve the BibTeX dependency macro '+item+'. Supply its @string definition.')
        return result.strip()
    todo = list(wanted)
    while todo:
        current = entries[todo.pop()]
        for field in ('crossref', 'xref', 'xdata'):
            if field not in current['fields']: continue
            for dependency in value(current['fields'][field]).split(','):
                dependency = dependency.strip()
                if dependency not in entries:
                    raise ValueError('BibTeX entry '+current['key']+' needs missing '+field+' entry '+dependency+'.')
                if dependency not in wanted:
                    wanted.add(dependency); todo.append(dependency)
    if any(raw.lower().startswith('@preamble') for raw in directives):
        warnings.append('The bibliography contains a supplied @preamble; it is retained as text and has not been executed.')
    subset = '\n\n'.join(directives + [entry['raw'] for key, entry in entries.items() if key in wanted])
    return (subset+'\n' if subset else ''), missing, warnings


def bibliography_path(workspace, paper_id):
    workspace.locate(paper_id)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', paper_id):
        raise ValueError('Invalid paper identity.')
    return Path(workspace.lab.store.directory)/'paper-bibliographies'/(paper_id+'.bib')


def shared_bibliography_path(workspace, paper_id):
    return workspace.safe(workspace.locate(paper_id).parent/'Bibliography'/'references.bib')


def shared_bibliography_guide(workspace, paper_id, path, filename):
    """Create navigation once; never replace the writer's edits to the note."""
    guide = workspace.safe(path.parent/'00_BIBLIOGRAPHY.md')
    if not guide.exists():
        raw = ('# Paper bibliography\n\n'
               '**Add a reference:** [Open this paper in Academic Writing Lab]'
               '(http://127.0.0.1:8765/#papers/'+paper_id+'). Open **References**, choose **Add BibTeX**, '
               'paste the entry, then save. For Google Scholar, use **Cite → BibTeX** and copy the entry.\n\n'
               '**One shared file:** [references.bib](references.bib) is the bibliography used by the Lab. '
               'New entries and edits in that file are read when References or export is opened.\n\n'
               '**File in this vault:** `'+path.relative_to(workspace.lab.vault).as_posix()+'`\n\n'
               '**Overleaf bibliography filename:** `'+filename+'`. Download or copy approved LaTeX '
               'and the needed BibTeX entries, then add them to your Overleaf project. No automatic Overleaf update occurs.\n\n'
               'Obsidian does not edit `.bib` files natively. Use the Lab entry form or a text editor; '
               'this Markdown note helps you find the shared file and is not a second editable copy. '
               'Delivery to other devices depends on your vault sync settings.\n\n'
               'Saved prior files are retained under `History/Displaced`. Citation metadata still needs your review '
               'against the paper; adding a BibTeX entry does not verify a quotation.\n')
        try: atomic_write(guide, raw, exclusive=True)
        except FileExistsError: pass
    meta = workspace.safe(path.with_suffix('.json'))
    if not meta.exists():
        try: atomic_write(meta, json.dumps({'filename':filename, 'source':'Shared paper bibliography in the Obsidian vault'}, ensure_ascii=False, indent=2)+'\n', exclusive=True)
        except FileExistsError: pass
    return guide


def check_bibliography_recovery(workspace, path):
    recovery = workspace.safe(path.parent/'History'/'Displaced')
    for marker in recovery.glob('*.json'):
        try:
            meta = json.loads(workspace.safe(marker).read_text(encoding='utf-8'))
            kept = workspace.safe(marker.with_suffix('.bib'))
            if not kept.is_file() or sha(kept.read_text(encoding='utf-8')) != meta['expected_hash']:
                raise Conflict('A recovered bibliography contains an external edit. Compare it before continuing.', kept_path=str(kept))
        except (ValueError, KeyError) as error:
            if isinstance(error, Conflict): raise
            raise ValueError('A bibliography recovery record needs review: '+marker.name) from error
    if not path.exists() and any(recovery.glob('*.bib')):
        raise Conflict('The shared bibliography is missing after an interrupted save. Its previous file is retained in Bibliography/History/Displaced.')


def bibliography_catalogue(workspace, paper_id):
    with workspace.lock:
        shared = shared_bibliography_path(workspace, paper_id)
        check_bibliography_recovery(workspace, shared)
        path = shared if shared.is_file() else bibliography_path(workspace, paper_id)
        if not path.is_file():
            return {'bibtex': '', 'filename': '', 'source': None, 'entries': [], 'basis': 'none',
                    'storage': 'none', 'hash': None, 'path': None, 'vault_path': None, 'uri': None}
        if path.stat().st_size > 8_000_000:
            raise ValueError('The stored bibliography is too large. Load a bibliography up to two million characters.')
        raw = path.read_text(encoding='utf-8')
        entries, _, macros = BibParser(raw).parse()
        meta = {}
        if path.with_suffix('.json').is_file():
            try:
                meta_path = workspace.safe(path.with_suffix('.json')) if path == shared else path.with_suffix('.json')
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                if not isinstance(meta, dict): meta = {}
            except (ValueError, OSError): pass
        # A human-readable catalogue is only a display of supplied metadata.
        # Unresolved macros stay visible rather than becoming guessed metadata.
        def display(parts, seen=()):
            return ''.join(item if kind == 'literal' else display(macros[item.lower()], (*seen, item.lower()))
                           if item.lower() in macros and item.lower() not in seen else item
                           for kind, item in parts)
        rows = [{'key': key, **{name: display(entry['fields'][name]) for name in ('title','author','year','doi','journal','booktitle','url') if name in entry['fields']}}
                for key, entry in entries.items()]
        guide = workspace.safe(path.parent/'00_BIBLIOGRAPHY.md') if path == shared else None
        return {'bibtex': raw, 'filename': meta.get('filename', path.name),
                'source': 'Shared paper bibliography in the Obsidian vault' if path == shared else meta.get('source'),
                'entries': rows, 'basis': 'shared' if path == shared else 'stored', 'hash': sha(raw),
                'storage': 'vault' if path == shared else 'local', 'path': str(path),
                'vault_path': path.relative_to(workspace.lab.vault).as_posix() if path == shared else None,
                'uri': workspace.uri(guide) if guide and guide.is_file() else None,
                'bib_uri': workspace.uri(path) if path == shared else None,
                'guide_path': str(guide) if guide and guide.is_file() else None}


def publish_shared_bibliography(workspace, path, raw, old_hash):
    """Publish without overwriting an external writer's recreated file.

    Moving the old inode into history retains writes through already-open
    handles. A marker lets subsequent reads detect later edits to that inode.
    """
    path = workspace.safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = None
    if old_hash is not None:
        if not path.is_file() or sha(path.read_text(encoding='utf-8')) != old_hash:
            raise Conflict('The shared bibliography changed. Reload it before adding entries.')
        history = workspace.safe(path.parent/'History'/'Displaced')
        history.mkdir(parents=True, exist_ok=True)
        kept = workspace.safe(history/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%f')+'-'+uuid.uuid4().hex+'.bib'))
        os.rename(path, kept)
        atomic_write(workspace.safe(kept.with_suffix('.json')), json.dumps({'expected_hash':old_hash})+'\n', exclusive=True)
        if sha(kept.read_text(encoding='utf-8')) != old_hash:
            if not path.exists():
                try: os.link(kept, path)
                except OSError: pass
            raise Conflict('An external bibliography edit arrived during save. It is retained in History/Displaced.', kept_path=str(kept))
    try:
        atomic_write(workspace.safe(path), raw, exclusive=True)
    except Exception as error:
        if kept is not None and not path.exists():
            try: os.link(kept, path)
            except OSError: pass
        raise Conflict('The bibliography could not be saved without replacing another file. Existing versions were retained; reload before trying again.', kept_path=str(kept) if kept else None) from error
    if kept is not None and sha(kept.read_text(encoding='utf-8')) != old_hash:
        raise Conflict('An external bibliography edit arrived during publication. It is retained in History/Displaced.', kept_path=str(kept))


def merge_bibliography(workspace, paper_id, body):
    if not isinstance(body, dict) or set(body)-{'bibtex','base_hash'} or not isinstance(body.get('bibtex', ''), str):
        raise ValueError('Paste BibTeX entries and include the bibliography hash you last read.')
    if 'base_hash' not in body or (body['base_hash'] is not None and not isinstance(body['base_hash'], str)):
        raise ValueError('Reload the bibliography and include its current hash before adding entries.')
    additions, directives, macros = BibParser(body.get('bibtex', '')).parse()
    with workspace.lock:
        current = bibliography_catalogue(workspace, paper_id)
        if current['hash'] != body['base_hash']:
            raise Conflict('The bibliography changed. Reload it before adding entries.')
        existing, prior_directives, prior_macros = BibParser(current['bibtex']).parse()
        conflicts = [key for key, entry in additions.items() if key in existing and
                     (entry['kind'] != existing[key]['kind'] or entry['fields'] != existing[key]['fields'])]
        if conflicts:
            raise Conflict('These citation keys already identify different entries: '+', '.join(conflicts)+'. Keep the existing key or deliberately correct the bibliography in Obsidian.', conflicting_keys=conflicts)
        macro_conflicts = [key for key in macros if key in prior_macros and macros[key] != prior_macros[key]]
        if macro_conflicts: raise Conflict('These BibTeX string names already have different definitions: '+', '.join(macro_conflicts)+'.')
        new_directives = []
        for raw in directives:
            match = re.match(r'@string\s*[{(]\s*([A-Za-z][A-Za-z0-9_:\-]*)', raw, re.I)
            if match:
                if match.group(1).lower() not in prior_macros: new_directives.append(raw)
            elif raw not in prior_directives: new_directives.append(raw)
        added = [key for key in additions if key not in existing]
        blocks = new_directives + [additions[key]['raw'] for key in added]
        merged = current['bibtex'] + (('\n\n' if current['bibtex'] else '')+'\n\n'.join(blocks)+'\n' if blocks else '')
        BibParser(merged).parse()
        path = shared_bibliography_path(workspace, paper_id)
        # Also recheck the private seed: an external writer does not hold our lock.
        latest = bibliography_catalogue(workspace, paper_id)
        if latest['hash'] != current['hash'] or latest['basis'] != current['basis']:
            raise Conflict('The bibliography changed while checking the pasted entries. Reload it and try again.')
        if current['basis'] != 'shared' or blocks:
            publish_shared_bibliography(workspace, path, merged, current['hash'] if current['basis']=='shared' else None)
        shared_bibliography_guide(workspace, paper_id, path, current['filename'] or 'references.bib')
        return {**bibliography_catalogue(workspace, paper_id), 'added_keys':added,
                'existing_keys':[key for key in additions if key in existing]}


def save_bibliography(workspace, paper_id, body):
    if not isinstance(body, dict) or set(body)-{'bibtex', 'filename', 'base_hash'} or not isinstance(body.get('bibtex'), str):
        raise ValueError('Supply BibTeX text and its filename.')
    raw = body['bibtex']; BibParser(raw).parse()
    filename = body.get('filename', 'references.bib')
    if not isinstance(filename, str) or len(filename) > 200 or not filename.lower().endswith('.bib') or any(c in filename for c in '/\\\r\n\x00'):
        raise ValueError('Use a .bib filename without a folder path.')
    with workspace.lock:
        shared = shared_bibliography_path(workspace, paper_id)
        current = bibliography_catalogue(workspace, paper_id)
        if current['basis'] == 'shared':
            if body.get('base_hash') != current['hash']:
                raise Conflict('The shared bibliography changed or its version was not supplied. Reload it before replacing the bibliography.')
            if raw != current['bibtex']:
                publish_shared_bibliography(workspace, shared, raw, current['hash'])
            shared_bibliography_guide(workspace, paper_id, shared, current['filename'] or filename)
            return bibliography_catalogue(workspace, paper_id)
        if 'base_hash' in body and body['base_hash'] != current['hash']:
            raise Conflict('The bibliography changed. Reload it before replacing the bibliography.')
        path = bibliography_path(workspace, paper_id)
        if path.is_file():
            old = path.read_text(encoding='utf-8')
            history = path.parent/'history'/paper_id
            backup = history/(sha(old)+'.bib')
            if not backup.exists(): atomic_write(backup, old, exclusive=True)
            if path.with_suffix('.json').is_file() and not backup.with_suffix('.json').exists():
                atomic_write(backup.with_suffix('.json'), path.with_suffix('.json').read_text(encoding='utf-8'), exclusive=True)
        atomic_write(path, raw)
        atomic_write(path.with_suffix('.json'), json.dumps({'filename':filename, 'source':'Supplied by the author in Academic Writing Lab', 'sha256':sha(raw)}, ensure_ascii=False, indent=2)+'\n')
        return bibliography_catalogue(workspace, paper_id)


def check_revisions(workspace, directory, notes):
    """Read revision history without calling Workspace.observe/revisions."""
    records = {n['id']: {} for n in notes}
    for path in workspace.safe(directory/'Revisions').glob('*.md'):
        raw = workspace.safe(path).read_text(encoding='utf-8')
        try: meta, body = split_note(raw)
        except ValueError: continue
        document = meta.get('document_id')
        if document not in records: continue
        marker = '## Saved note\n\n'
        if marker not in body or sha(body.split(marker, 1)[1]) != meta.get('content_hash'):
            raise ValueError('A saved revision is incomplete or changed: '+path.name+'. Let syncing finish before export.')
        rid = meta.get('awl_id'); parents = meta.get('parents')
        if not isinstance(rid, str) or not isinstance(parents, list) or any(not isinstance(p, str) for p in parents):
            raise ValueError('A saved revision has invalid identity or parent information: '+path.name)
        record = {'text': body.split(marker, 1)[1], 'hash': meta['content_hash'], 'parents': parents}
        if rid in records[document] and records[document][rid] != record:
            raise Conflict('Conflicting copies of a saved revision need comparison before export.')
        records[document][rid] = record
    for note in notes:
        history = records[note['id']]; declared = note['meta'].get('awl_revision')
        parents = {parent for record in history.values() for parent in record['parents']}
        if (declared and declared not in history) or parents-history.keys():
            raise ValueError('Saved revisions for '+note['title']+' have not finished syncing. Reopen the card after sync completes.')
        heads = {rid: record for rid, record in history.items() if rid not in parents}
        if history and not heads:
            raise ValueError('The saved revision history needs repair before export: '+note['title'])
        if len({record['hash'] for record in heads.values()}) > 1 or (declared and declared in parents):
            raise Conflict('Compare the competing saved versions of '+note['title']+' before exporting it.')
        if history and not declared and not any(record['hash'] == note['hash'] for record in heads.values()):
            raise Conflict('The current text of '+note['title']+' has no matching saved version. Reopen and compare before export.')
    for path in workspace.safe(directory/'Recovered files').glob('*/*.md'):
        raw = workspace.safe(path).read_text(encoding='utf-8')
        try: meta, _ = split_note(raw)
        except ValueError: continue
        document = meta.get('awl_id')
        if document not in records: continue
        represented = {note_content(record['text']) for record in records[document].values()}
        represented.update(note_content(note['_raw']) for note in notes if note['id'] == document)
        if note_content(raw) not in represented:
            raise Conflict('A recovered version needs comparison before export. Open Compare & recover for the affected card.')


def latex_preview(workspace, paper_id, body):
    if not isinstance(body, dict) or set(body)-{'section_ids', 'card_ids', 'expected_hashes', 'bibtex', 'mode'}:
        raise ValueError('Choose sections or cards, optional version hashes, BibTeX text, and plain or latex mode.')
    mode = body.get('mode', 'plain')
    if mode not in ('plain', 'latex'): raise ValueError('Choose plain or latex export mode.')
    if 'bibtex' in body and not isinstance(body['bibtex'], str):
        raise ValueError('Supply bibliography text, not a file path or another value.')
    for field in ('section_ids', 'card_ids'):
        if field in body and (not isinstance(body[field], list) or any(not isinstance(v, str) for v in body[field]) or len(body[field]) > 1000):
            raise ValueError(field+' must be a list of card identities.')
    expected = body.get('expected_hashes', {})
    if not isinstance(expected, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in expected.items()):
        raise ValueError('Include version hashes as a map from card identity to saved hash.')
    with workspace.lock:
        path = workspace.locate(paper_id); plan = workspace.read(path); nodes = workspace.tree(plan)
        by_id = {node['id']: node for node in nodes}; all_notes = {paper_id: plan, **by_id}
        for node in nodes:
            if node['type'] in ('section','subsection') and node['fields'].get('Section manuscript source','') not in ('','arguments','section'):
                raise ValueError('Choose arguments or section as the manuscript source for '+node['title']+' before export.')
        for cid, known_hash in expected.items():
            if cid not in all_notes: raise ValueError('A requested version does not belong to the current paper outline.')
            if all_notes[cid]['hash'] != known_hash:
                raise Conflict('The saved text or outline changed. Save or reload before previewing LaTeX.', card_id=cid)
        section_ids = set(body.get('section_ids', [])); card_ids = set(body.get('card_ids', []))
        if any(cid not in by_id or by_id[cid]['type'] not in ('section', 'subsection') for cid in section_ids):
            raise ValueError('A selected section is not in the current paper outline.')
        if any(cid not in by_id or by_id[cid]['type'] != 'argument' for cid in card_ids):
            raise ValueError('A selected argument is not in the current paper outline.')
        def ancestors(node):
            result = []; parent = node['parent_id']
            while parent:
                result.append(parent); parent = by_id[parent]['parent_id']
            return result
        def owns_section(node):
            return node['type'] in ('section','subsection') and node['fields'].get('Section manuscript source')=='section'
        def authority(node):
            # The outer whole-section manuscript is authoritative even when it
            # is empty or unapproved. Never silently fall back to older children.
            chain=list(reversed(ancestors(node)))+[node['id']]
            return next((by_id[cid] for cid in chain if owns_section(by_id[cid])),node)
        requested=[node for node in nodes if
                   (node['type']=='argument' or owns_section(node)) and
                   (not ({'section_ids','card_ids'} & body.keys()) or node['id'] in card_ids or
                    node['id'] in section_ids or section_ids.intersection(ancestors(node)))]
        selected_ids={authority(node)['id'] for node in requested}
        selected=[node for node in nodes if node['id'] in selected_ids]
        # Selecting an empty section still selects its explicit manuscript.
        needed_ids = {n['id'] for n in selected} | {a for n in selected for a in ancestors(n)} | section_ids
        check_revisions(workspace, path.parent, [plan]+[n for n in nodes if n['id'] in needed_ids])
        included = []; skipped = []; warnings = []; blocks = []; used_headings = set(); sections = []
        for selected_id in sorted(section_ids | card_ids):
            owner=authority(by_id[selected_id])
            if owner['id']!=selected_id:
                warnings.append(by_id[selected_id]['title']+' is retained as an argument or planning card; the authoritative whole-section draft '+owner['title']+' is used for this export.')
        def brief(node):
            return {'id': node['id'], 'title': node['title'], 'hash': node['hash'], 'writing_status': node['writing_status']}
        for node in selected:
            prose = node['fields'].get('Manuscript prose', '').strip()
            if not prose or node['writing_status'] != 'complete':
                skipped.append({**brief(node), 'reason': 'empty' if not prose else 'not_approved'})
                continue
            lineage = list(reversed(ancestors(node)))+([node['id']] if owns_section(node) else [])
            for aid in lineage:
                if aid in used_headings: continue
                ancestor = by_id[aid]; heading = '\\'+ancestor['type']+'{'+literal(publication_heading(ancestor['title']))+'}'
                blocks.append(heading); used_headings.add(aid)
                sections.append({'id': aid, 'title': ancestor['title'], 'type': ancestor['type'], 'heading_tex': heading})
            try: converted = prose if mode == 'latex' else plain_to_latex(prose)
            except ValueError as error: raise ValueError(node['title']+': '+str(error)) from error
            blocks.append(converted); included.append({**brief(node), 'prose_hash': sha(prose), 'section_ids': lineage})
            if re.search(r'\((?:ref(?:erence)?|citation)(?:\s+[^)]*)?\)|\[(?:citation|reference|ref|source needed|evidence needed|TODO)\b[^]]*\]', prose, re.I):
                warnings.append(node['title']+': unresolved reference or writing placeholder remains in approved text.')
        tex = '\n\n'.join(blocks)+ ('\n' if blocks else '')
        keys = citation_keys(tex)
        subset = None; missing = None
        basis = 'supplied' if body.get('bibtex') else 'none'
        bibtext = body.get('bibtex')
        if 'bibtex' not in body:
            stored = bibliography_catalogue(workspace, paper_id)
            bibtext = stored['bibtex']
            basis = stored['basis']
        if bibtext is not None and not isinstance(bibtext, str):
            raise ValueError('Supply bibliography text, not a file path or another value.')
        if bibtext:
            subset, missing, bib_warnings = bibliography_subset(bibtext, keys)
            warnings.extend(bib_warnings)
            if missing: warnings.append('These citation keys are absent from the supplied bibliography: '+', '.join(missing)+'.')
        elif keys:
            warnings.append('Citation keys have not been checked against your Overleaf bibliography. Supply its .bib text to verify them.')
        if skipped: warnings.append(str(len(skipped))+' selected parts were omitted because their current text is not approved or is empty.')
        if not included: warnings.append('No approved manuscript prose is available in this selection.')
        # An external editor does not share our lock. Check the entire outline
        # and every selected note again before returning this coherent snapshot.
        for note in [plan]+[n for n in nodes if n['id'] in needed_ids or n['id'] in expected]:
            if sha(Path(note['path']).read_text(encoding='utf-8')) != note['hash']:
                raise Conflict('The vault changed while preparing LaTeX. Reload the saved text and preview again.')
        check_revisions(workspace, path.parent, [plan]+[n for n in nodes if n['id'] in needed_ids])
        document = springer_document(tex, literal(plan['title']), bibliography=bool(keys))
        return {'paper_id': paper_id, 'plan_hash': plan['hash'], 'mode': mode,
                'sections': sections, 'tex': tex, 'included': included, 'skipped': skipped,
                'document_tex': document, 'document_filename': 'main.tex',
                'template': TEMPLATE_ID, 'bibliography_filename': BIBLIOGRAPHY_FILENAME,
                'citation_keys': keys, 'missing_keys': missing, 'bibtex': subset,
                'bibliography_basis': basis,
                'warnings': warnings}
