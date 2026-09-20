import asyncio
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from backend.reading import Reading, Create, Save, ReviewRequest, TEMPLATES
from backend.literature import Literature
from backend.workspace import Conflict, Workspace
from backend.storage import Store


def reading(tmp_path, name='Mac'):
    vault=tmp_path/name/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=SimpleNamespace(store=Store(tmp_path/name/'data'),vault=vault,semaphore=asyncio.Semaphore(1))
    lab.workspace=Workspace(lab);lab.workspace.configure(str(vault))
    return Reading(lab,Literature(lab.workspace))


def test_books_and_chapters_are_linked_documents_synced_without_database(tmp_path):
    mac=reading(tmp_path)
    book=mac.create(Create(title='Reading organisational change',kind='book'))
    child=mac.create(Create(title='Evidence and interpretation',kind='chapter',parent_id=book['id'],pages='3, pp. 42–65'))
    saved=mac.save(child['id'],Save(base_hash=child['hash'],fields={'My summary':'My own account of the chapter.','Quotations with context':'> Exact source text.\n\nPage 42.'}))
    assert Path(book['path']).parent.name=='Reading organisational change'
    assert Path(child['path']).name=='01 - Evidence and interpretation.md'
    assert 'Chapters/01%20-%20Evidence%20and%20interpretation.md' in Path(book['path']).read_text()
    assert '../Book%20overview.md' in Path(child['path']).read_text()
    win=reading(tmp_path,'Windows');shutil.copytree(mac.root,win.root,dirs_exist_ok=True)
    reopened=win.get(child['id'])
    assert reopened['fields']==saved['fields'] and reopened['parent']['id']==book['id']
    assert win.get(book['id'])['children'][0]['id']==child['id']
    assert not list(win.root.rglob('*.sqlite3'))


def test_actual_template_and_source_note_are_preserved(tmp_path):
    app=reading(tmp_path)
    template=app.lab.vault/TEMPLATES['reading'][1];template.parent.mkdir(parents=True)
    template.write_text('# Template\n\n## My critical questions\n\nTemplate instructions\n')
    source=app.lab.vault/'02_Shared/Literature/Sources/An actual source.md';source.parent.mkdir(parents=True)
    original='---\nlibrary_schema: 1\nlibrary_id: source-one\ntitle: An actual source\nauthor: A. Writer\n---\n\n## In brief\n\nEarlier notes, possibly machine-written.\n'
    source.write_text(original)
    note=app.create(Create(title='My new reading',source_id='source-one'))
    assert 'My critical questions' in note['fields']
    assert note['fields']['My summary']==''
    assert 'Earlier notes' in note['fields']['Source note (reference copy)']
    assert source.read_text()==original
    with pytest.raises(ValueError): app.save(note['id'],Save(base_hash=note['hash'],fields={'Source note (reference copy)':'Different source'}))


def test_external_changes_and_stale_summary_are_both_retained(tmp_path):
    app=reading(tmp_path);note=app.create(Create(title='A summary'))
    path=Path(note['path']);path.write_text(path.read_text()+'\n## My custom field\n\nKeep my convention.\n')
    latest=app.get(note['id'])
    changed=app.save(note['id'],Save(base_hash=latest['hash'],fields={'My summary':'Written on another device.'}))
    with pytest.raises(Conflict):app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My browser draft.'}))
    current=app.get(note['id']);assert current['conflict']
    assert current['fields']['My summary']=='Written on another device.'
    assert any(v['fields']['My summary']=='My browser draft.' for v in app.history(note['id']))
    merged=app.save(note['id'],Save(base_hash=current['hash'],fields={'My summary':'My compared summary.'},merge_heads=[v['id'] for v in current['heads']]))
    assert not merged['conflict'] and merged['fields']['My custom field']=='Keep my convention.'


def test_invalid_chapter_heading_injection_and_symlink_are_rejected(tmp_path):
    app=reading(tmp_path);note=app.create(Create(title='A summary'))
    with pytest.raises(ValueError):app.create(Create(title='Chapter',kind='chapter',parent_id=note['id']))
    with pytest.raises(ValueError):app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My words\n## Chapters\nInjected'}))
    source=app.lab.vault/TEMPLATES['source'][1];source.parent.mkdir(parents=True)
    outside=tmp_path/'other-template.md';outside.write_text('## Private\n')
    source.symlink_to(outside)
    with pytest.raises(ValueError):app.templates()


ADVICE={'meaning':'You distinguish the finding from the broader claim.',
        'strengths':[{'quote':'My own summary.','explanation':'The central point is clear.'}],
        'priorities':[{'quote':'','explanation':'The evidence is not supplied.','tip':'Add a source excerpt before checking fidelity.'}],
        'source_questions':['Which passage supports the claim?'],'next_step':'Find one supporting passage with its page number.'}


def test_tutor_snapshot_survives_editing_and_feedback_sync(tmp_path,monkeypatch):
    async def scenario():
        app=reading(tmp_path);note=app.create(Create(title='My review'))
        note=app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My own summary.'}))
        app.store.set_setting('profile',{'model':'test-local-model'})
        started=asyncio.Event();release=asyncio.Event();seen={}
        async def generate(profile,payload,mode,output_model):
            seen.update(payload);assert mode=='reading_tutor';started.set();await release.wait()
            return ADVICE,{'model':'test-local-model'}
        monkeypatch.setattr('backend.reading.providers.generate',generate)
        job=await app.review(note['id'],ReviewRequest(base_hash=note['hash']))
        await started.wait()
        app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My revised summary while the tutor reads.'}))
        release.set();await asyncio.gather(*list(app.tasks.values()))
        result=app.reviews(note['id'])[0]
        assert result['status']=='done' and result['reviewed_text']=='My own summary.'
        assert 'No source excerpts' in result['scope'] and seen['source_excerpts']==''
        assert app.get(note['id'])['fields']['My summary'].startswith('My revised')
        win=reading(tmp_path,'Windows');shutil.copytree(app.root,win.root,dirs_exist_ok=True)
        assert win.reviews(note['id'])[0]['result']==ADVICE
        assert win.reviews(note['id'])[0]['id']==job['id']
    asyncio.run(scenario())


def test_tutor_uses_excerpts_only_and_rejects_invented_quotes(tmp_path,monkeypatch):
    async def scenario():
        app=reading(tmp_path);note=app.create(Create(title='My review'))
        note=app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My own summary.','Quotations with context':'> Quoted source.\n\nPage 42.\nMy interpretation is separate.'}))
        app.store.set_setting('profile',{'model':'test-local-model'})
        async def generate(profile,payload,mode,output_model):
            assert payload['source_scope'].startswith('Only the quoted excerpts')
            assert '> Quoted source.' in payload['source_excerpts']
            result=json.loads(json.dumps(ADVICE));result['strengths'][0]['quote']='Words I never wrote.'
            return result,{}
        monkeypatch.setattr('backend.reading.providers.generate',generate)
        await app.review(note['id'],ReviewRequest(base_hash=note['hash']))
        await asyncio.gather(*list(app.tasks.values()))
        result=app.reviews(note['id'])[0]
        assert result['status']=='failed' and 'quotation' in result['error']
        assert not list(app.root.rglob('Feedback/*.md'))
    asyncio.run(scenario())


def test_api_routes_connect_reading_and_planner(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    app=create_app(tmp_path/'data',vault,auto_tutor=False);app.state.lab.workspace.configure(str(vault))
    with TestClient(app,base_url='http://localhost') as client:
        token=client.get('/api/bootstrap').json()['token'];headers={'X-AWL-Token':token}
        response=client.post('/api/reading',json={'title':'API chapter book','kind':'book'},headers=headers)
        assert response.status_code==200
        note=response.json();assert client.get('/api/reading').json()['documents'][0]['id']==note['id']
        assert client.get('/api/planner').json()['enabled']
        response=client.post('/api/planner/tasks',headers=headers,json={'request_id':'fe2f88cc-ff61-4a72-a463-f272f3a9dbcb','title':'Review the chapter','day':'2026-09-17','source_path':note['vault_path'],'route':'#reading/'+note['id']})
        assert response.status_code==200 and response.json()['saved']
        assert not response.json()['device_synced']


def test_ipad_requests_use_saved_snapshot_and_stable_jobs(tmp_path,monkeypatch):
    from backend.workspace import frontmatter,sha
    import uuid
    async def scenario():
        app=reading(tmp_path);note=app.create(Create(title='Synced chapter'))
        note=app.save(note['id'],Save(base_hash=note['hash'],fields={'My summary':'My own summary.'}))
        app.store.set_setting('profile',{'model':'test-local-model'})
        count=0
        async def generate(*args,**kwargs):
            nonlocal count
            count+=1
            return ADVICE,{}
        monkeypatch.setattr('backend.reading.providers.generate',generate)
        def request(summary_hash):
            ident=str(uuid.uuid4());folder=Path(note['path']).parent/'Tutor requests';folder.mkdir(exist_ok=True)
            payload={'id':ident,'document_id':note['id'],'summary_hash':summary_hash,'question':'Help with clarity.','created':'2026-09-16T20:00:00Z'}
            (folder/(ident+'.md')).write_text(frontmatter({'awl_schema':1,'awl_kind':'reading-tutor-request','awl_id':ident,'document_id':note['id']})+'# Request\n\n## Request\n\n```json\n'+json.dumps(payload)+'\n```\n')
            return folder/(ident+' - status.md')
        receipt=request(sha('My own summary.'))
        await app.process_ipad_requests();await asyncio.gather(*list(app.tasks.values()))
        await app.process_ipad_requests();await app.process_ipad_requests()
        assert count==1 and 'Feedback is ready' in receipt.read_text()
        stale=request(sha('Earlier words.'));await app.process_ipad_requests()
        assert count==1 and 'summary changed' in stale.read_text()
    asyncio.run(scenario())
