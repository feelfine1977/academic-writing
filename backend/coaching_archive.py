"""Portable, immutable copies of writer questions; local jobs never migrate as work."""
import json
import re

from .storage import digest, dump


def portable_question(job):
    result = dict(job)
    if result.get('status') in ('queued', 'running'):
        result.update(status='interrupted', result=None, error='This question was saved on another device while its reading was unfinished. A completed reading will appear after it syncs; no model job was started here.')
        result.pop('stage', None)
    return result


def import_question(db, job):
    if not isinstance(job, dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', str(job.get('id', ''))):
        raise ValueError('Invalid writing question identity.')
    if job.get('status') not in ('complete', 'failed', 'interrupted'):
        raise ValueError('Only saved question records can be imported, never live jobs.')
    for name in ('text', 'text_hash', 'question', 'exercise_key', 'created'):
        if not isinstance(job.get(name), str): raise ValueError('Incomplete writing question: '+name)
    if digest(job['text']) != job['text_hash']: raise ValueError('The writing question text does not match its saved hash.')
    if not db.execute('SELECT id FROM exercises WHERE id=?', (job['exercise_key'],)).fetchone():
        raise ValueError('Waiting for this question’s exercise context to sync.')
    key = 'writing_question:'+job['id']
    old = db.execute('SELECT payload FROM settings WHERE id=?', (key,)).fetchone()
    if old:
        previous = json.loads(old['payload'])
        identity = ('id', 'text', 'text_hash', 'question', 'exercise_key', 'created', 'original_text', 'context')
        if any(previous.get(k) != job.get(k) for k in identity):
            raise ValueError('Conflicting writing question copies are kept in the vault; the local record was not replaced.')
        if previous == job: return
        # Device clocks cannot turn completed feedback back into an interrupted
        # request. A local running job retains ownership until it finishes.
        if previous.get('status') in ('queued', 'running'): return
        if previous.get('status') == 'complete':
            if job['status'] == 'complete': raise ValueError('Two completed readings share one identity. Both vault records are kept for comparison.')
            return
        if job['status'] != 'complete': return
    db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (key, dump(job)))


def question_history(store, *, exercise_key='', paper_id='', card_id=''):
    if not exercise_key and not (paper_id and card_id):
        raise ValueError('Choose one exercise or a paper and argument to see its writing questions.')
    if bool(paper_id) != bool(card_id) or (exercise_key and paper_id):
        raise ValueError('Choose one writing context.')
    result = []
    for row in store.rows("SELECT payload FROM settings WHERE id LIKE 'writing_question:%'"):
        job = json.loads(row['payload'])
        context = (job.get('context') or {}).get('paper_context') or {}
        if exercise_key and job.get('exercise_key') != exercise_key: continue
        if paper_id and (context.get('paper_id') != paper_id or context.get('argument_id') != card_id): continue
        result.append({k:job.get(k) for k in ('id', 'question', 'created', 'status', 'exercise_key')})
    return sorted(result, key=lambda j:(j.get('created') or '', j['id']), reverse=True)[:50]
