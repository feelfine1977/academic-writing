import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from backend.storage import Store,dump,digest
from backend.content import import_pack,build_pack
from backend.workspace import Workspace
from backend.learning_sync import LearningSync


def setup(root):
    vault=root/'vault';(vault/'.obsidian').mkdir(parents=True)
    store=Store(root/'data');ws=Workspace(SimpleNamespace(store=store,vault=vault));ws.configure(str(vault))
    return store,ws,LearningSync(ws)


def test_learning_roundtrip_preserves_answers_feedback_and_completion(tmp_path):
    store,ws,sync=setup(tmp_path/'Mac')
    pack,answers=build_pack('Synthetic practice','A bounded claim.',[],'S03');import_pack(store,pack,answers)
    exercise=pack['pack_id']+'@1:'+pack['exercises'][-1]['id']
    store.execute('INSERT INTO sessions(id,exercise_id,updated,payload) VALUES(?,?,?,?)',('session',exercise,'2026-09-10T10:00:00',dump({'origin':'learner'})))
    text='My original answer: café → 心, with α and β.'
    store.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)' if False else 'INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',('attempt','session',None,text,digest(text),'2026-09-10T10:01:00','request',dump({'outline':'My reasoning.','reason':'Make scope explicit.'})))
    store.event('session','check',{'attempt_id':'attempt','correct':True})
    store.set_setting('writing_completion_reviews',{'attempt':{'attempt_id':'attempt','basis':'learner_criteria_review','reviewed_at':'2026-09-10T10:02:00','reflection':'I checked the scope.'}})
    assert sync.sync()['state']=='saved'
    win,ww,ss=setup(tmp_path/'Windows');shutil.copytree(ws.lab.vault/'06_Academic_Writing_Lab',ww.lab.vault/'06_Academic_Writing_Lab',dirs_exist_ok=True)
    first=ss.sync();assert first['state']=='saved',first
    assert win.one('SELECT text FROM attempts')['text']==text
    assert win.one('SELECT text FROM sessions')['text']==text
    assert win.setting('writing_completion_reviews')['attempt']['reflection']=='I checked the scope.'
    assert ss.sync()['state']=='saved'
    assert len(win.rows('SELECT * FROM attempts'))==1
    assert len(win.rows('SELECT * FROM events'))==1
    assert not list(ww.lab.vault.rglob('*.sqlite3'))


def question_job(exercise, **changes):
    return {'id':'question-1','exercise_key':exercise,'text':'My paragraph.','text_hash':digest('My paragraph.'),
            'question':'How can I clarify the link?','original_text':'My paragraph.','created':'2026-09-10T10:00:00Z',
            'context':{'paper_context':{'paper_id':'study','argument_id':'intro'}},
            'status':'complete','result':{'answer':'Explain what connects the two ideas.'},**changes}


def test_question_archive_roundtrip_and_history_are_scoped(tmp_path):
    from backend.coaching_archive import question_history
    store,ws,sync=setup(tmp_path/'one')
    pack,answers=build_pack('Synthetic practice','A bounded claim.',[],'S03');import_pack(store,pack,answers)
    exercise=pack['pack_id']+'@1:'+pack['exercises'][-1]['id']
    store.set_setting('writing_question:question-1',question_job(exercise))
    store.set_setting('profile',{'provider':'ollama','model':'private-device-model','local_confirmed':True})
    assert sync.sync()['state']=='saved'
    second,ww,ss=setup(tmp_path/'two')
    shutil.copytree(ws.lab.vault/'06_Academic_Writing_Lab',ww.lab.vault/'06_Academic_Writing_Lab',dirs_exist_ok=True)
    assert ss.sync()['state']=='saved'
    assert second.setting('writing_question:question-1')==question_job(exercise)
    assert not second.setting('profile')
    assert len(question_history(second,paper_id='study',card_id='intro'))==1
    assert question_history(second,paper_id='other-study',card_id='intro')==[]
    assert question_history(second,exercise_key='another-exercise')==[]
    assert len(question_history(second,exercise_key=exercise))==1
    assert ss.sync()['state']=='saved'


def test_unfinished_question_does_not_start_job_and_complete_wins(tmp_path):
    from backend.coaching_archive import import_question,portable_question
    store,ws,sync=setup(tmp_path)
    pack,answers=build_pack('Synthetic practice','A bounded claim.',[],'S03');import_pack(store,pack,answers)
    exercise=pack['pack_id']+'@1:'+pack['exercises'][-1]['id']
    pending=portable_question(question_job(exercise,status='running',result=None))
    with store.connect() as db:import_question(db,pending)
    assert store.setting('writing_question:question-1')['status']=='interrupted'
    complete=question_job(exercise)
    with store.connect() as db:import_question(db,complete)
    with store.connect() as db:import_question(db,pending)
    assert store.setting('writing_question:question-1')==complete
    assert not store.rows('SELECT * FROM jobs')


def test_question_import_rejects_conflicting_identity(tmp_path):
    import pytest
    from backend.coaching_archive import import_question
    store,_,_=setup(tmp_path)
    pack,answers=build_pack('Synthetic practice','A bounded claim.',[],'S03');import_pack(store,pack,answers)
    exercise=pack['pack_id']+'@1:'+pack['exercises'][-1]['id']
    original=question_job(exercise)
    with store.connect() as db:import_question(db,original)
    with pytest.raises(ValueError,match='Conflicting'):
        with store.connect() as db:import_question(db,question_job(exercise,question='Changed question'))
    with pytest.raises(ValueError,match='Two completed'):
        with store.connect() as db:import_question(db,question_job(exercise,result={'answer':'Different reading'}))
    assert store.setting('writing_question:question-1')==original
