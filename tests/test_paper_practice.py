from backend.main import create_app
from backend.paper_practice import prepare,apply_attempt
from backend.workspace import Conflict
import pytest


def test_tutor_copy_can_return_only_to_its_unchanged_argument(tmp_path):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=create_app(tmp_path/'data',vault,auto_tutor=False).state.lab;lab.workspace.configure(str(vault))
    p=lab.workspace.create('A paper','## Argument: A bounded claim\n### Purpose\nState what was observed.\n### Manuscript prose\nAn initial sentence.')
    card=lab.workspace.card(p['id'],p['nodes'][0]['id']);review=prepare(lab,p['id'],card['id'])
    attempt=lab.save_attempt(review['exercise_key'],'A revised sentence.','revision',session_id=review['session_id'])
    result=apply_attempt(lab,p['id'],card['id'],attempt['id'])
    assert result['fields']['Manuscript prose']=='A revised sentence.'
    exercise=lab.exercise(lab.store.one('SELECT * FROM exercises WHERE id=?',(review['exercise_key'],)))
    from backend.feedback_context import task_context
    assert task_context(lab,exercise)['paper_context']['purpose']=='State what was observed.'
    with pytest.raises(Conflict):apply_attempt(lab,p['id'],card['id'],review['attempt_id'])


def test_review_freezes_the_outline_revision_and_argument_scope(tmp_path):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=create_app(tmp_path/'data',vault,auto_tutor=False).state.lab;lab.workspace.configure(str(vault))
    p=lab.workspace.create('A paper','## Argument: A bounded claim\n### Purpose\nState the observation.\n### Manuscript prose\nAn initial sentence.')
    card=lab.workspace.card(p['id'],p['nodes'][0]['id'])
    lab.workspace.save(p['id'],card['id'],card['hash'],{'Main message':'Report the observation.','Scope and boundaries':'Do not infer cause.'})
    first=prepare(lab,p['id'],card['id'])
    p=lab.workspace.get(p['id'])
    lab.workspace.save(p['id'],p['id'],p['hash'],{'Outline revision':'September proposal'})
    second=prepare(lab,p['id'],card['id'])
    assert first['exercise_key']!=second['exercise_key']
    payload=lab.exercise(lab.store.one('SELECT * FROM exercises WHERE id=?',(second['exercise_key'],)))
    assert payload['workspace_context']['outline_revision']=='September proposal'
    assert payload['workspace_context']['scope_and_boundaries']=='Do not infer cause.'
    prior=lab.exercise(lab.store.one('SELECT * FROM exercises WHERE id=?',(first['exercise_key'],)))
    assert prior['workspace_context']['outline_revision']==''
