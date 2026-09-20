import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from urllib.parse import unquote
import re

import pytest

from backend.storage import Store
from backend.workspace import Workspace, Conflict, fields_of, split_note, sha


def workspace(tmp_path, name='Mac'):
    vault=tmp_path/name/'Vault';(vault/'.obsidian').mkdir(parents=True)
    service=Workspace(SimpleNamespace(store=Store(tmp_path/name/'data'),vault=vault))
    service.configure(str(vault))
    return service


OUTLINE='## Section: Introduction\n### Subsection: Motivation\n#### Argument: Business objective\n- Our intended claim\n### Manuscript prose\nInitial prose.\n'


def make(service):
    plan=service.create('A readable paper',OUTLINE)
    card=service.card(plan['id'],plan['nodes'][-1]['id'])
    return plan,card


def test_readable_outline_links_every_type_and_second_computer_reopens(tmp_path):
    mac=workspace(tmp_path);plan,card=make(mac)
    assert Path(card['path']).name=='Argument - Business objective.md'
    assert Path(plan['path']).parent.name=='A readable paper'
    for target in re.findall(r'\]\(([^)]+)\)',Path(plan['path']).read_text()):
        assert (Path(plan['path']).parent/unquote(target)).exists()
    result=mac.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'A revised argument.','Reasoning and decisions':'Preserve the qualification.'})
    win=workspace(tmp_path,'Windows')
    shutil.copytree(mac.root,win.root,dirs_exist_ok=True)
    reopened=win.card(plan['id'],card['id'])
    assert reopened['fields']['Manuscript prose']=='A revised argument.'
    assert reopened['fields']['Reasoning and decisions']=='Preserve the qualification.'
    assert reopened['hash']==result['hash']
    assert not list(win.root.rglob('*.sqlite3'))


def test_external_edits_and_unknown_properties_survive(tmp_path):
    service=workspace(tmp_path);plan,card=make(service);path=Path(card['path'])
    raw=path.read_text().replace('awl_schema: 1','custom_date: 2026-09-10\nawl_schema: 1')+'\n## My private convention\n\nKeep these exact words.\n'
    path.write_text(raw)
    current=service.card(plan['id'],card['id'])
    service.save(plan['id'],card['id'],current['hash'],{'Notes and bullet points':'Changed notes.'})
    meta,body=split_note(path.read_text())
    assert str(meta['custom_date'])=='2026-09-10'
    assert fields_of(body)['My private convention']=='Keep these exact words.'
    assert fields_of(body)['Manuscript prose']=='Initial prose.'


def test_stale_editor_is_kept_without_overwriting_external_text(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    service.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'Edited elsewhere.'})
    with pytest.raises(Conflict):service.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'My older editor draft.'})
    current=service.card(plan['id'],card['id'])
    assert current['fields']['Manuscript prose']=='Edited elsewhere.'
    assert current['conflict']
    versions=service.history(plan['id'],card['id'])
    assert any(v['fields']['Manuscript prose']=='My older editor draft.' for v in versions)
    merged=service.save(plan['id'],card['id'],current['hash'],{'Manuscript prose':'A deliberate reconciliation.'},[h['id'] for h in current['heads']])
    assert not merged['conflict']


def test_support_revision_preserves_authored_text_and_review_state(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    authored={'Manuscript prose':'My approved words.', 'Reasoning and decisions':'My judgement.',
              'Completed prose hash':sha('My approved words.'),
              'Selected review attempt':'review-3','Completion note':'Ready for export.'}
    saved=service.save(plan['id'],card['id'],card['hash'],authored)
    updated=service.save(plan['id'],card['id'],saved['hash'],{
        'Academic reviewer guidance':'### Evidence\n\nA bounded claim with page references.',
        'Flow and wording notes':'Connect this finding to the next argument.'})
    assert all(updated['fields'][key]==value for key,value in authored.items())
    assert updated['revision_id']!=saved['revision_id']
    assert any(item['awl_id']==saved['revision_id'] for item in service.history(plan['id'],card['id']))
    with pytest.raises(Conflict):
        service.save(plan['id'],card['id'],saved['hash'],{'Academic reviewer guidance':'An older proposal.'})
    reopened=service.card(plan['id'],card['id'])
    assert reopened['fields']['Academic reviewer guidance']==updated['fields']['Academic reviewer guidance']
    assert all(reopened['fields'][key]==value for key,value in authored.items())


def test_title_revision_keeps_identity_path_fields_and_outline(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    plan_before=Path(plan['path']).read_text()
    updated=service.save(plan['id'],card['id'],card['hash'],{},title='Current argument title')
    assert updated['title']=='Current argument title'
    assert updated['id']==card['id'] and updated['path']==card['path']
    assert updated['fields']==card['fields']
    assert Path(plan['path']).read_text()==plan_before
    with pytest.raises(ValueError):
        service.save(plan['id'],card['id'],updated['hash'],{},title='Title\n## Manuscript prose\nOverwrite')
    assert service.card(plan['id'],card['id'])['hash']==updated['hash']


def test_offline_sibling_revisions_are_detected_after_sync(tmp_path):
    mac=workspace(tmp_path);plan,card=make(mac);win=workspace(tmp_path,'Windows')
    shutil.copytree(mac.root,win.root,dirs_exist_ok=True)
    wc=win.card(plan['id'],card['id'])
    mac.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'Mac branch.'})
    win.save(plan['id'],card['id'],wc['hash'],{'Manuscript prose':'Windows branch.'})
    wdir=Path(win.locate(plan['id'])).parent
    mdir=Path(mac.locate(plan['id'])).parent
    shutil.copytree(wdir/'Revisions',mdir/'Revisions',dirs_exist_ok=True)
    current=mac.card(plan['id'],card['id'])
    assert current['conflict'] and len(current['heads'])==2
    with pytest.raises(Conflict):mac.save(plan['id'],card['id'],current['hash'],{'Next step':'Do not hide the conflict.'})


def test_partial_arrival_does_not_become_a_new_baseline(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    saved=service.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'Saved.'})
    revision_path=Path(next(r['path'] for r in service.history(plan['id'],card['id']) if r['awl_id']==saved['revision_id']))
    revision_path.rename(revision_path.with_suffix('.pending'))
    before=Path(card['path']).read_text()
    with pytest.raises(ValueError,match='arrived before'):service.card(plan['id'],card['id'])
    assert Path(card['path']).read_text()==before


def test_add_empty_structure_and_argument_cards_updates_actual_links(tmp_path):
    service=workspace(tmp_path);plan=service.create('Blank paper')
    section=service.add_card(plan['id'],'Results','section')
    sub=service.add_card(plan['id'],'Limits','subsection',section['id'])
    argument=service.add_card(plan['id'],'Open question','argument',sub['id'])
    assert argument['fields']['Manuscript prose']==''
    updated=service.get(plan['id'])
    assert len(updated['nodes'])==4
    assert updated['nodes'][-1]['parent_id']==sub['id']
    assert 'Subsection - Limits.md' in service.card(plan['id'],sub['id'])['path']


def test_unsafe_links_duplicate_identity_and_reserved_names(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    path=Path(plan['path']);raw=path.read_text()
    path.write_text(raw.replace('Cards/Section%20-%20Introduction.md','../outside.md'))
    with pytest.raises(ValueError,match='Cards folder'):service.get(plan['id'])
    path.write_text(raw)
    shutil.copy2(card['path'],Path(card['path']).with_name('Conflict copy.md'))
    with pytest.raises(ValueError,match='same identity'):service.get(plan['id'])
    reserved=service.create('CON')
    assert Path(reserved['path']).parent.name=='Paper - CON'


def test_field_heading_cannot_silently_remove_prose_from_export(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    with pytest.raises(ValueError,match='###'):service.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'Part one.\n## Surprise\nPart two.'})
    assert service.card(plan['id'],card['id'])['fields']['Manuscript prose']=='Initial prose.'


def test_api_roundtrip_and_conflict_status(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    vault=tmp_path/'vault';(vault/'.obsidian').mkdir(parents=True)
    app=create_app(tmp_path/'app',vault,auto_tutor=False)
    with TestClient(app,base_url='http://localhost') as client:
        token=client.get('/api/bootstrap').json()['token'];headers={'X-AWL-Token':token}
        assert client.post('/api/workspace/configure',json={'vault':str(vault)},headers=headers).status_code==200
        plan=client.post('/api/workspace/papers',json={'title':'API paper'},headers=headers).json()
        card=client.get(f"/api/workspace/papers/{plan['id']}/cards/{plan['nodes'][0]['id']}").json()
        url=f"/api/workspace/papers/{plan['id']}/notes/{card['id']}"
        body={'base_hash':card['hash'],'fields':{'Manuscript prose':'Written in the app.'}}
        assert client.patch(url,json=body,headers=headers).status_code==200
        assert client.patch(url,json=body,headers=headers).status_code==409
        export=client.get(f"/api/workspace/papers/{plan['id']}/export")
        assert export.status_code==200 and 'Written in the app.' in export.text


def test_repeated_observed_obsidian_edits_are_sequential(tmp_path):
    service=workspace(tmp_path);plan,card=make(service);path=Path(card['path'])
    for text in ('First external edit.','Second external edit.'):
        from backend.workspace import update_fields,frontmatter
        meta,body=split_note(path.read_text());path.write_text(frontmatter(meta)+update_fields(body,{'Manuscript prose':text}))
        current=service.card(plan['id'],card['id'])
        assert not current['conflict']
        assert current['fields']['Manuscript prose']==text


def test_unplaced_card_is_visible_and_never_deleted(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    current=service.get(plan['id'])
    service.save(plan['id'],plan['id'],current['hash'],{'Argument order':'\n'.join(current['fields']['Argument order'].splitlines()[:-1])})
    reopened=service.get(plan['id'])
    assert reopened['unplaced'][0]['id']==card['id']
    assert Path(card['path']).exists()


def test_source_import_search_and_mapping_do_not_change_manuscript(tmp_path):
    from backend.workspace_sources import PaperSources
    service=workspace(tmp_path);plan,card=make(service);sources=PaperSources(service)
    tex=b'\\section{Introduction}\n\nExisting objective evidence.\n\n\\input{/private/never-read}\n\nA separate qualification.'
    source=sources.upload(plan['id'],'My latest paper.tex',tex)
    found=sources.search(plan['id'],'objective evidence')
    assert found['total']==1 and found['results'][0]['before']=='\\section{Introduction}'
    assert sources.search(plan['id'],'never-read')['total']==1
    link=sources.mapping(plan['id'],source['awl_id'],found['results'][0]['id'],'adapt','Establishes the goal.')
    saved=service.save(plan['id'],card['id'],card['hash'],{'Source mapping':link})
    assert saved['fields']['Manuscript prose']=='Initial prose.'
    assert 'My latest paper.tex' in saved['fields']['Source mapping']
    target=re.search(r'\]\(([^)]+)\)',link).group(1).split('#')[0]
    assert (Path(card['path']).parent/unquote(target)).exists()
    win=workspace(tmp_path,'Windows');shutil.copytree(service.root,win.root,dirs_exist_ok=True)
    assert PaperSources(win).search(plan['id'],'objective')['total']==1


def test_edit_arriving_at_publication_is_preserved(tmp_path,monkeypatch):
    service=workspace(tmp_path);plan,card=make(service)
    import backend.workspace as module
    original=module.os.rename
    fired=False
    def raced_rename(src,dst):
        nonlocal fired
        if Path(src)==Path(card['path']) and not fired:
            fired=True
            raw=Path(src).read_text().replace('Initial prose.','External text at the exact race window.')
            Path(src).write_text(raw)
        return original(src,dst)
    monkeypatch.setattr(module.os,'rename',raced_rename)
    with pytest.raises(Conflict,match='external edit'):service.save(plan['id'],card['id'],card['hash'],{'Manuscript prose':'App proposal.'})
    versions=service.history(plan['id'],card['id'])
    assert any(v['fields']['Manuscript prose']=='External text at the exact race window.' for v in versions)
    assert service.card(plan['id'],card['id'])['conflict']


def test_paper_rename_and_incomplete_unrelated_revision(tmp_path):
    service=workspace(tmp_path);plan,card=make(service)
    path=Path(plan['path']);renamed=path.with_name('My research plan.md');path.rename(renamed)
    assert service.catalogue()['papers'][0]['filename']=='My research plan.md'
    (path.parent/'Revisions'/'arriving file.md').write_text('---\nnot complete')
    assert service.card(plan['id'],card['id'])['fields']['Manuscript prose']=='Initial prose.'


def test_late_external_write_through_first_adoption_handle_is_a_conflict(tmp_path):
    service=workspace(tmp_path);plan=service.create('A readable paper',OUTLINE)
    argument=plan['nodes'][-1];path=Path(argument['path']);raw=path.read_text()
    assert 'awl_revision:' not in raw
    with path.open('r+',encoding='utf-8') as external:
        adopted=service.card(plan['id'],argument['id'])
        assert not adopted['conflict']
        external.seek(0)
        external.write(raw.replace('Initial prose.','External text written after first adoption.'))
        external.truncate();external.flush()
    current=service.card(plan['id'],argument['id'])
    assert current['conflict']
    histories=service.history(plan['id'],argument['id'])
    external_revision=next(v for v in histories if v['fields']['Manuscript prose']=='External text written after first adoption.')
    assert external_revision['origin']=='displaced_external_edit' and external_revision['parents']==[]


def test_source_reserved_names_and_modified_original_are_reported(tmp_path):
    from backend.workspace_sources import PaperSources
    service=workspace(tmp_path);plan,card=make(service);sources=PaperSources(service)
    s=sources.upload(plan['id'],'Source.md',b'Original evidence.')
    original=sources.root(plan['id'])/s['folder']/s['original'];original.write_text('Contradictory replacement.')
    result=sources.catalogue(plan['id'])
    assert result['issues'] and not result['sources']


def test_open_folder_outside_managed_papers_registers_a_project(tmp_path):
    service=workspace(tmp_path)
    from scripts.create_paper_workspace import create_paper,read_outline
    folder=service.lab.vault/'My research'/'Ocean study'
    result=create_paper(folder,'Ocean study',read_outline('## Section: Introduction\n### Argument: A question\n- One premise'))
    opened=service.open_folder(str(folder))
    assert opened['id']==result['paper_id'] and opened['nodes'][1]['fields']['Notes and bullet points']=='- One premise'
    assert service.open_folder(str(folder))['id']==opened['id']
    win=workspace(tmp_path,'Windows');shutil.copytree(service.lab.vault,win.lab.vault,dirs_exist_ok=True)
    assert win.catalogue()['papers'][0]['title']=='Ocean study'
    assert len(list((service.lab.vault/'06_Academic_Writing_Lab'/'Projects').glob('*.md')))==1


def test_active_writing_idea_travels_with_section_without_modifying_prose(tmp_path):
    mac=workspace(tmp_path);plan,_=make(mac)
    section=mac.card(plan['id'],next(n['id'] for n in plan['nodes'] if n['type']=='section'))
    steps=json.dumps([{'id':'opening','title':'Introduce the topic','points':['State the setting.']}])
    saved=mac.save(plan['id'],section['id'],section['hash'],{'Section writing plan':steps,'Active writing idea':'opening','Writing intention':'Introduce the topic in my own words.'})
    win=workspace(tmp_path,'Windows')
    shutil.copytree(mac.root,win.root,dirs_exist_ok=True)
    reopened=win.card(plan['id'],section['id'])
    assert reopened['fields']['Active writing idea']=='opening'
    assert reopened['fields'].get('Manuscript prose','')==section['fields'].get('Manuscript prose','')
    with pytest.raises(ValueError,match='existing idea'):
        mac.save(plan['id'],section['id'],saved['hash'],{'Active writing idea':'unknown'})
