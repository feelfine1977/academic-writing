from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import io
import uuid

import pytest

from backend.workspace import Workspace, Conflict, frontmatter
from backend.outline_import import prepare, apply, history


def fixture(tmp_path):
    vault = tmp_path/'Vault'; (vault/'.obsidian').mkdir(parents=True)
    data = tmp_path/'data'; data.mkdir()
    ws = Workspace(SimpleNamespace(vault=vault,store=SimpleNamespace(directory=data)))
    ws.configure(str(vault))
    plan = ws.create('My study','## Section: Introduction\n#### Argument: Previous opening\n### Manuscript prose\nMy earlier prose.\n')
    return ws, plan, plan['nodes'][-1]


def package(plan, old, *, paper_id=None, missing=False, collision=False):
    section = str(uuid.uuid4()); argument = old['id'] if collision else str(uuid.uuid4())
    paper_id = paper_id or plan['id']
    def card(id, kind, title, body):
        return frontmatter({'awl_schema':1,'awl_kind':'card','awl_id':id,'paper_id':paper_id,'card_type':kind,'status':'planned'})+'# '+kind.capitalize()+' - '+title+'\n\n'+body
    files = {
        'Paper_outline.md':'# Revised outline\n\n## Introduction\n[Section](Cards/section.md)\n- [Opening](Cards/opening.md)\n',
        'Cards/section.md':card(section,'section','Introduction','## Purpose\n\nGive the new opening a clear job.\n'),
        'Cards/opening.md':card(argument,'argument','A clearer opening','[Plan](../Paper_outline.md)\n\n## Purpose\n\nState the observation.\n\n## Main message\n\nKeep the observed scope.\n\n## Writing task\n\nWrite two clear sentences.\n\n## Notes and bullet points\n\n- Name the observed scope.\n\n## Source mapping\n\n[Decision](../Guide/decision.md)\n\n## Supervisor comments and editing consequences\n\nA proposal, not recorded approval.\n\n## Manuscript prose\n\n## Relationship to the previous cards\n\nprevious card ID: `'+old['id']+'`.\n'),
        'Guide/decision.md':'# Decision\n\n[New argument](../Cards/opening.md)\n'
    }
    if missing: files.pop('Guide/decision.md')
    raw=io.BytesIO()
    with ZipFile(raw,'w') as archive:
        for name,text in files.items():archive.writestr('Uploaded cards/'+name,text)
    return raw.getvalue(), argument


def test_import_keeps_prose_and_full_guidance_with_readable_links(tmp_path):
    ws,plan,old=fixture(tmp_path);raw,id=package(plan,old)
    original=Path(old['path']).read_bytes()
    before=set(ws.lab.vault.rglob('*'))
    preview=prepare(ws,plan['id'],raw,'September proposal')
    assert set(ws.lab.vault.rglob('*'))==before
    result=apply(ws,preview)
    current=ws.get(plan['id'])
    assert len(current['nodes'])==2 and current['nodes'][-1]['id']==id
    assert current['nodes'][0]['filename']=='Section - Introduction - September proposal.md'
    assert Path(old['path']).read_bytes()==original
    assert current['unplaced'][-1]['fields']['Manuscript prose']=='My earlier prose.'
    card=ws.card(plan['id'],id)
    assert card['fields']['Manuscript prose']==''
    assert card['fields']['Writing task']=='Write two clear sentences.'
    assert card['meta']['previous_card_ids']==[old['id']]
    assert card['filename']=='Argument - A clearer opening.md'
    assert 'Revision%20materials/September%20proposal/Guide/decision.md' in card['fields']['Source mapping']
    linked=Path(plan['path']).parent/'Revision materials/September proposal/Guide/decision.md'
    assert '../../../Cards/Argument%20-%20A%20clearer%20opening.md' in linked.read_text()
    prior=history(ws,plan['id'],result['earlier_outline_id'])
    assert prior['nodes'][-1]['fields']['Manuscript prose']=='My earlier prose.'
    assert len(ws.catalogue()['papers'])==1
    assert 'Proposal' in current['fields']['Outline revision']
    assert 'My earlier prose.' not in ws.export(plan['id'])


def test_reimport_does_not_reset_new_writing_or_duplicate_cards(tmp_path):
    ws,plan,old=fixture(tmp_path);raw,id=package(plan,old)
    apply(ws,prepare(ws,plan['id'],raw,'September proposal'))
    card=ws.card(plan['id'],id)
    ws.save(plan['id'],id,card['hash'],{'Manuscript prose':'My revised prose.'})
    again=apply(ws,prepare(ws,plan['id'],raw,'September proposal'))
    assert again['already_imported']
    assert ws.card(plan['id'],id)['fields']['Manuscript prose']=='My revised prose.'
    assert len(history(ws,plan['id']))==1


@pytest.mark.parametrize('options',[{'missing':True},{'collision':True},{'paper_id':'another-paper'}])
def test_bad_packages_do_not_change_the_paper(tmp_path,options):
    ws,plan,old=fixture(tmp_path);raw,_=package(plan,old,**options)
    before={str(p):p.read_bytes() for p in ws.lab.vault.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):prepare(ws,plan['id'],raw,'September proposal')
    assert {str(p):p.read_bytes() for p in ws.lab.vault.rglob('*') if p.is_file()}==before


def test_zip_traversal_and_changed_outline_are_rejected(tmp_path):
    ws,plan,old=fixture(tmp_path)
    raw=io.BytesIO()
    with ZipFile(raw,'w') as archive:archive.writestr('../escape.md','untrusted')
    with pytest.raises(ValueError,match='Unsafe'):prepare(ws,plan['id'],raw.getvalue(),'Bad archive')
    raw,_=package(plan,old);preview=prepare(ws,plan['id'],raw,'September proposal')
    ws.save(plan['id'],plan['id'],plan['hash'],{'Research question':'A newer author decision.'})
    with pytest.raises(Conflict,match='changed after'):apply(ws,preview)
    assert not (Path(plan['path']).parent/'Outline versions').exists()


def test_snapshot_waits_for_complete_sync_and_retains_prior_text(tmp_path):
    ws,plan,old=fixture(tmp_path);raw,id=package(plan,old)
    result=apply(ws,prepare(ws,plan['id'],raw,'September proposal'))
    snapshot=history(ws,plan['id'],result['earlier_outline_id'])
    saved=Path(snapshot['nodes'][-1]['path']);original=saved.read_bytes()
    saved.unlink()
    with pytest.raises(ValueError,match='incomplete'):history(ws,plan['id'],result['earlier_outline_id'])
    saved.write_bytes(original)
    assert history(ws,plan['id'],result['earlier_outline_id'])['nodes'][-1]['fields']['Manuscript prose']=='My earlier prose.'
    assert ws.get(plan['id'])['nodes'][-1]['id']==id
