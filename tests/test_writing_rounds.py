import asyncio
import shutil
import uuid
from types import SimpleNamespace

import pytest

from backend.storage import Store
from backend.workspace import Workspace, Conflict
from backend.writing_rounds import checkpoint, intentional_practice, practice_root


@pytest.fixture
def paper(tmp_path):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=SimpleNamespace(vault=vault,store=Store(tmp_path/'data'))
    ws=Workspace(lab);ws.configure(str(vault))
    plan=ws.create('Study','## Section: Introduction\n### Argument: First idea')
    sid=next(n['id'] for n in plan['nodes'] if n['type']=='section')
    return ws,plan['id'],sid


def save(paper,text):
    ws,pid,sid=paper;n=ws.card(pid,sid)
    return ws.save(pid,sid,n['hash'],{'Manuscript prose':text})


def record(paper,origin='own_attempt',request_id=None):
    ws,pid,sid=paper
    return checkpoint(ws,pid,sid,{'base_hash':ws.card(pid,sid)['hash'],
        'request_id':request_id or str(uuid.uuid4()),'reflection':'I explained the connection.', 'origin':origin})


def test_intentional_checkpoints_ignore_autosaves_duplicates_and_model_wording(paper):
    ws,pid,sid=paper
    save(paper,'The results need interpretation.');save(paper,'The results need interpretation!')
    assert intentional_practice(*paper)['meaningful_attempts']==0
    request_id=str(uuid.uuid4());assert record(paper,request_id=request_id)['meaningful_attempts']==1
    assert record(paper,request_id=request_id)['checkpoint_count']==1
    save(paper,'The results need interpretation.');assert record(paper)['meaningful_attempts']==1
    save(paper,'Goals make the results interpretable.');assert record(paper,'model_assisted')['meaningful_attempts']==1
    save(paper,'Goals guide interpretation.');assert record(paper)['meaningful_attempts']==2
    assert 'text' not in intentional_practice(*paper)['checkpoints'][0]


def test_checkpoint_refuses_unchanged_scaffold_or_stale_base(paper):
    ws,pid,sid=paper;n=save(paper,'[Explain the connection.]')
    ws.save(pid,sid,n['hash'],{'Writing scaffold':'[Explain the connection.]'})
    with pytest.raises(ValueError,match='scaffold'):record(paper)
    save(paper,'I explain what follows from this result.')
    with pytest.raises(Conflict):checkpoint(ws,pid,sid,{'base_hash':'old','request_id':str(uuid.uuid4()),'reflection':'Changed.','origin':'own_attempt'})
    assert intentional_practice(*paper)['checkpoint_count']==0


def test_private_markdown_roundtrip_works_on_another_machine_without_local_db(paper,tmp_path):
    ws,pid,sid=paper;n=save(paper,'A draft with ``` fences and a reason.')
    ws.save(pid,sid,n['hash'],{'Writing intention':'Connect two ideas.','Next writing action':'Write the example.'})
    record(paper)
    other=tmp_path/'Windows vault';shutil.copytree(ws.lab.vault,other)
    lab=SimpleNamespace(vault=other,store=Store(tmp_path/'Windows data'))
    second=Workspace(lab);second.configure(str(other))
    result=intentional_practice(second,pid,sid)
    assert result['meaningful_attempts']==1
    assert result['checkpoints'][0]['goal']=='Connect two ideas.'
    assert result['checkpoints'][0]['next_action']=='Write the example.'
    assert second.card(pid,sid)['fields']['Manuscript prose']=='A draft with ``` fences and a reason.'


def test_a_synced_copy_does_not_count_twice_and_paths_cannot_escape_vault(paper):
    ws,pid,sid=paper;save(paper,'An actual attempt.');record(paper)
    root=practice_root(*paper);path=next(root.glob('*.md'));shutil.copyfile(path,root/'sync-copy.md')
    assert intentional_practice(*paper)['meaningful_attempts']==1
    with pytest.raises(ValueError):checkpoint(ws,pid,sid,{'base_hash':ws.card(pid,sid)['hash'],'request_id':'../../bad','reflection':'x'})


def test_malformed_sync_record_cannot_break_valid_practice(paper):
    import json
    save(paper,'A saved independent attempt.');record(paper)
    root=practice_root(*paper);p=next(root.glob('*.md'))
    data=json.loads(p.read_text().split('```json\n')[1].split('\n```')[0]);data['id']=[]
    (root/'malformed.md').write_text('```json\n'+json.dumps(data)+'\n```')
    assert intentional_practice(*paper)['meaningful_attempts']==1
