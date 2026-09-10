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
    text='My original answer.'
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
