"""Obsidian Sync companion: append-only exports and previewed learner imports.

The local registry, not editable Markdown metadata, identifies an exercise.
No research sources, answer sheets, or existing browser sessions are overwritten.
"""
import json
import re
from pathlib import Path
from threading import RLock
from urllib.parse import quote, urlencode
from .storage import digest, dump, now, uid
from .content import safe_source

FOLDER = '06_Academic_Writing_Lab/Companion'
HEADINGS = ['## Your answer', '## Your idea outline (optional)',
            '## What I practised (optional)', '## End of editable answers']


def fields(text):
    text = text.replace('\r\n', '\n')
    matches = [list(re.finditer(r'^'+re.escape(h)+r'[ \t]*$', text, re.M)) for h in HEADINGS]
    if any(len(m) != 1 for m in matches):
        raise ValueError('Keep each of the four answer headings exactly once. Resolve any Obsidian conflict copies first.')
    spans = [m[0].span() for m in matches]
    if spans != sorted(spans):
        raise ValueError('The answer headings changed order. Restore the worksheet headings before importing.')
    values = [text[spans[i][1]:spans[i+1][0]].strip() for i in range(3)]
    if any(len(v) > limit for v, limit in zip(values, [12000, 8000, 2500])):
        raise ValueError('Use up to 12,000 answer characters, 8,000 outline characters and 2,500 reflection characters.')
    fixed = text[:spans[0][1]] + '\n'.join(HEADINGS[1:3]) + text[spans[3][0]:]
    return values, digest(fixed)


class Companion:
    def __init__(self, lab):
        self.lab = lab
        self.store = lab.store
        self.lock = RLock()

    def registry(self):
        return self.store.setting('obsidian_companion_v1', {'notes': {}, 'modules': {}, 'snapshots': []})

    def path(self, relative):
        root = self.lab.vault.resolve()
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:2] != tuple(FOLDER.split('/')):
            raise ValueError('Companion files must stay in their dedicated vault folder.')
        candidate = root/relative
        # Reject symlinks even if they currently point inside the vault.
        if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root and p.is_relative_to(root)):
            raise ValueError('A companion path is a symbolic link. Use a normal folder inside the vault.')
        if not candidate.resolve().is_relative_to(root):
            raise ValueError('The companion path is outside the vault.')
        return candidate

    def uri(self, relative):
        return 'obsidian://open?' + urlencode({'vault': self.lab.vault.name, 'file': relative}, quote_via=quote)

    def write_new(self, relative, text):
        if not self.lab.vault.is_dir():
            raise ValueError('The configured vault is unavailable. Open it in Obsidian before exporting.')
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as f:
            f.write(text)

    def status(self):
        r = self.registry()
        return {'vault': self.lab.vault.name, 'folder': FOLDER,
                'modules': list(r['modules'].values()), 'notes': len(r['notes']),
                'snapshots': r['snapshots'][-8:][::-1],
                'sync_note': 'Obsidian handles device sync. The lab cannot see whether your iPad has finished syncing.'}

    def worksheet(self, e, note_id, module_path):
        example = self.lab.teaching.example(e['key'])['example']
        lines = ['---', 'type: awl-companion-exercise', f'awl_note: {note_id}',
                 f'exercise_key: {json.dumps(e["key"])}', 'text_origin: learner_answer_below', '---', '',
                 f'# {e["title"]}', '', f'[[{module_path}|Back to this module]]', '',
                 'Write only beneath the three answer headings at the end. Keep the task and headings unchanged. '
                 'Your answer comes back to the Mac through Obsidian Sync; nothing is submitted while you type.', '',
                 '## Task', '', e['prompt'], '']
        if e.get('parts'):
            lines += [f'- {p["id"]}: {p["text"]}' for p in e['parts']] + ['', 'You can type A B C or A > B > C; arrow symbols are unnecessary.', '']
        if e.get('choices'):
            lines += ['Choices: ' + ' / '.join(str(x) for x in e['choices']), '']
        lines += ['## Check these criteria', ''] + ['- '+c for c in e['criteria']]
        if e.get('teaching_note'):
            lines += ['', '## Principle', '', e['teaching_note']]
        lines += ['', '## Worked example from another area', '',
                  f'**{example["subject"]}**', '', example['task'], '', '**Example response:**', '', example['answer'], '',
                  '**Why it works:**', ''] + ['- '+m for m in example.get('moves', [])]
        lines += ['', '**Now apply the structure:** '+example['transfer'], '',
                  'This is a constructed teaching example, not evidence for your paper.', '',
                  HEADINGS[0], '', '', HEADINGS[1], '', '', HEADINGS[2], '', '', HEADINGS[3], '',
                  'On the Mac: open Writing Lab → Obsidian & iPad → Preview synced answers. '
                  'Select this answer to save it. Open writing still needs a tutor review or your own criteria review for completion.', '',
                  f'[Open the activity on this Mac](http://127.0.0.1:8765/#practice/{quote(e["key"], safe="")})', '',
                  'The localhost link works on the Mac only. On the iPad, use these notes offline.', '']
        return '\n'.join(lines)

    def export_module(self, module_id):
        with self.lock:
            learning = self.lab.curriculum.snapshot()
            m = next((m for m in learning['modules'] if m['id'] == module_id), None)
            if not m:
                raise ValueError('Choose an existing learning module.')
            r = self.registry()
            signature = digest(dump(m['exercise_keys']))[:12]
            key = module_id + ':' + signature
            if key in r['modules']:
                return {**r['modules'][key], 'already_exported': True}
            export_id = uid()[:8]
            directory = FOLDER+'/Modules/'+re.sub(r'[^a-zA-Z0-9_-]', '-', module_id)+'-'+export_id
            index = directory+'/00 Module.md'
            notes = []
            for i, exercise_key in enumerate(m['exercise_keys']):
                row = self.store.one('SELECT * FROM exercises WHERE id=?', (exercise_key,))
                e = self.lab.exercise(row)
                note_id = uid()
                filename = f'{i+1:02d} '+re.sub(r'[^\w -]', '', e['title'])[:75]+'.md'
                relative = directory+'/'+filename
                text = self.worksheet(e, note_id, index)
                _, fixed_hash = fields(text)
                self.write_new(relative, text)
                r['notes'][note_id] = {'id': note_id, 'exercise_key': exercise_key, 'title': e['title'],
                                      'path': relative, 'fixed_hash': fixed_hash, 'module_id': module_id}
                notes.append((relative, e['title'], learning['exercise_status'][exercise_key]))
            lines = [f'# {m["title"]}', '', m['goal'], '',
                     '## A session on your iPad', '',
                     '1. Let Obsidian Sync finish on both devices before leaving. Open this module on the iPad once.',
                     '2. Try two or three activities. Use the outside-field example to understand the task.',
                     '3. Type your answer beneath **Your answer**. Put your own idea outline and reflection in their sections.',
                     '4. When back online, let both devices sync. On the Mac, preview and import your answers in the lab.',
                     '5. Review the feedback, then use the skill in one WISE paragraph.', '',
                     'Answer sheets are never overwritten by re-export. Do not rename or move them until after importing. '
                     'Do not edit the same answer on both devices before syncing. '
                     'Progress below is a dated snapshot, not live grading.', '', f'Exported: {now()}', '']
            for path, title, status in notes:
                lines += [f'- [[{path}|{title}]] — '+('completed in lab' if status['completed'] else 'ready to practise')]
            self.write_new(index, '\n'.join(lines)+'\n')
            result = {'id': key, 'module_id': module_id, 'title': m['title'], 'count': len(notes),
                      'path': index, 'uri': self.uri(index), 'created': now()}
            r['modules'][key] = result
            self.store.set_setting('obsidian_companion_v1', r)
            return {**result, 'already_exported': False}

    def read_note(self, note):
        path = self.path(note['path'])
        conflicts = list(path.parent.glob(path.stem+' (Conflicted copy*.md'))
        if conflicts:
            raise ValueError('An Obsidian conflict copy exists. Compare and resolve both versions before importing.')
        if not path.is_file():
            raise ValueError('Note missing: let Obsidian finish syncing, or restore its original name and folder.')
        if path.stat().st_size > 160000:
            raise ValueError('The worksheet is too large to import.')
        text = path.read_text(encoding='utf-8')
        values, fixed_hash = fields(text)
        if fixed_hash != note['fixed_hash']:
            raise ValueError('The task or fixed instructions changed. Restore them using Obsidian version history; keep your answer.')
        answer, outline, reason = values
        request_key = 'obsidian:'+note['id']+':'+digest(dump(values))
        previous = self.store.one('SELECT id FROM attempts WHERE request_key=?', (request_key,))
        return {**note, 'text': answer, 'outline': outline, 'reason': reason,
                'file_hash': digest(text), 'request_key': request_key,
                'status': 'empty' if not answer else 'imported' if previous else 'ready',
                'attempt_id': previous['id'] if previous else None}

    def preview(self):
        rows = []
        for note in self.registry()['notes'].values():
            try:
                result = self.read_note(note)
                rows.append({k:v for k,v in result.items() if k not in ('fixed_hash', 'request_key')})
            except (ValueError, OSError, UnicodeError) as error:
                rows.append({**note, 'status': 'needs_attention', 'error': str(error)})
        return {'notes': rows, 'checked': now()}

    def import_answers(self, selected):
        if not 1 <= len(selected) <= 30 or len({s['note_id'] for s in selected}) != len(selected):
            raise ValueError('Select 1–30 distinct answers from a fresh preview.')
        with self.lock:
            r = self.registry()
            prepared = []
            # Validate the entire preview before creating any attempts.
            for item in selected:
                note = r['notes'].get(item['note_id'])
                if not note:
                    raise ValueError('This note is not in the local export registry.')
                p = self.read_note(note)
                if p['file_hash'] != item['file_hash']:
                    raise ValueError('An answer changed after the preview. Preview again to review the synced version.')
                if not p['text']:
                    raise ValueError('Write an answer before importing.')
                prepared.append(p)
            results = []
            for p in prepared:
                if p['attempt_id']:
                    a = self.store.one('SELECT * FROM attempts WHERE id=?', (p['attempt_id'],))
                else:
                    # Each import is a separate saved session: an unsaved browser draft stays intact.
                    session = self.lab.session(p['exercise_key'], fresh=True)
                    example = self.lab.teaching.example(p['exercise_key'])
                    self.store.event(session['id'], 'offline_example_available',
                                     {'version': example['version'], 'example_id': example['example']['id'],
                                      'record_basis': 'included_in_offline_worksheet; actual viewing not measured'})
                    a = self.lab.save_attempt(p['exercise_key'], p['text'], p['request_key'],
                                              session_id=session['id'], outline=p['outline'], reason=p['reason'])
                    self.store.event(session['id'], 'obsidian_answer_imported',
                                     {'note_id': p['id'], 'path': p['path'], 'file_hash': p['file_hash'],
                                      'assistance': 'Worksheet includes a constructed outside-field worked example.'})
                check = self.lab.check(a)
                results.append({'note_id': p['id'], 'exercise_key': p['exercise_key'], 'attempt_id': a['id'],
                                'already_imported': bool(p['attempt_id']), 'check': check})
            return {'results': results}

    def snapshot(self):
        """Create a new visual WISE map + progress note; editable copies never written back."""
        with self.lock:
            r = self.registry()
            directory = FOLDER+'/Snapshots/'+now()[:10]+'-'+uid()[:8]
            learning = self.lab.curriculum.snapshot()
            s = learning['summary']
            lines = ['# My Writing Lab on iPad', '', f'Snapshot from the Mac: {now()}', '',
                     f'**{s["completed"]}/{s["total"]} activities complete · {s["points"]} practice points**', '',
                     f'{s["correct"]} correct checked tasks; {s["tutor_met"]} tutor criteria met; {s["reviewed"]} learner self-reviews.', '',
                     'These are practice records, not a language qualification. Points update after importing and reviewing in the Mac lab.', '',
                     f'[[{directory}/WISE argument map.canvas|Open the visual WISE argument map]]', '',
                     '## My offline modules', '']
            lines += [f'- [[{m["path"]}|{m["title"]}]] ({m["count"]} activities)' for m in r['modules'].values()]
            lines += ['', '## A useful writing cycle', '',
                      'Check the agreed argument direction → place an existing agreed passage if it fits → practise one language move only if needed → '
                      'keep or adapt the wording, or draft a missing passage → read in context → check evidence and transitions.', '',
                      'Keep imported paper claims separate from your own inference. A connective cannot supply a missing reason.', '',
                      '## When you return to the Mac', '',
                      'Open the lab → Obsidian & iPad → Preview synced answers → select answers → Save selected answers. '
                      'Then request tutor feedback or record a criteria self-review. Use Save note to Obsidian to carry feedback back.', '',
                      'Sync notes before switching devices. Work on a given worksheet on one device at a time. '
                      'The lab does not sync its SQLite database, run an offline iPad model, or import Canvas edits.', '']
            nodes = []; edges = []; sections = []
            plans = self.lab.paper.workbench.state()['plans']
            paper=self.lab.paper.summary()
            self.write_new(directory+'/WISE revision decisions.md',self.lab.revision.export())
            lines+=['','[[WISE revision decisions|Read the discussion directions and passage placements]]','']
            for n in self.lab.paper.blueprint['nodes']:
                if n['section'] not in sections: sections.append(n['section'])
                section_index = sections.index(n['section'])
                row = sum(1 for x in nodes if x.get('section') == n['section'])
                plan = plans.get(n['id'], {})
                lines_node = [f'# {n["id"]} · {n["title"]}', '', '**Paragraph job:** '+n['purpose'], '',
                              '## Ideas to preserve', ''] + ['- '+x for x in n['ideas']]
                lines_node += ['', '**Boundary:** '+n['boundary'], '', '## Your saved argument plan', '']
                lines_node += [f'**{k.replace("_", " ").title()}:** {plan.get(k) or "Not yet planned"}' for k in ['contribution', 'bridge', 'handover', 'open_question', 'next_action', 'scratchpad']]
                for decision in paper.get('revision_decisions',[]):
                    if n['id'] in decision['node_ids']:lines_node += ['','Discussion direction ('+decision['status']+'): '+decision['text']]
                if n['id'] in paper['selected']:
                    version=paper['selected'][n['id']]
                    lines_node += ['','## Selected manuscript version', 'Origin: '+version['payload'].get('origin','learner'),'',version['text'],'']
                lines_node += ['', '## Scratch ideas on iPad', '',
                               'Add notes here. This snapshot does not update the lab automatically. '
                               'For a paragraph you want imported, use the matching WISE module worksheet.', '',
                               f'[Open target on the Mac](http://127.0.0.1:8765/#paper/{n["id"]})', '']
                relative = directory+'/WISE/'+n['id']+'.md'
                self.write_new(relative, '\n'.join(lines_node))
                nodes.append({'id': n['id'], 'type': 'file', 'file': relative, 'x': section_index*530,
                              'y': row*390+180, 'width': 450, 'height': 300, 'color': str(section_index%6+1), 'section': n['section']})
                if n.get('next_id'):
                    edges.append({'id':'next-'+n['id'], 'fromNode':n['id'], 'toNode':n['next_id'],
                                  'fromSide':'bottom', 'toSide':'top', 'label':'overview sequence · check the handover'})
            for n in nodes: n.pop('section')
            nodes.insert(0, {'id':'legend','type':'text','text':'# WISE argument map\nOverview order, not a validated causal chain or your experimental app order.\nOpen a card for the paragraph job, evidence boundary and your saved plan.\nCanvas moves and scratch notes stay in this snapshot; they are not imported as manuscript prose.',
                             'x':0,'y':-100,'width':1000,'height':230})
            self.write_new(directory+'/WISE argument map.canvas', json.dumps({'nodes':nodes,'edges':edges}, ensure_ascii=False, indent=2))
            self.write_new(directory+'/00 Start here.md', '\n'.join(lines))
            result = {'path':directory+'/00 Start here.md', 'created':now(), 'title':'Learning & WISE snapshot'}
            result['uri'] = self.uri(result['path'])
            r['snapshots'].append(result)
            self.store.set_setting('obsidian_companion_v1', r)
            return result

    def source_status(self, source):
        try:
            path = safe_source(source['path'], self.lab.vault)
            return {'available':True, 'changed':digest(path.read_text(encoding='utf-8')) != source['hash'],
                    'uri':self.uri(str(path.relative_to(self.lab.vault.resolve())))}
        except (OSError, ValueError, UnicodeError):
            return {'available':False, 'changed':False, 'uri':None}
