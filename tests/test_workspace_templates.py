import io
from pathlib import Path
import shutil
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.storage import Store
from backend.workspace import Workspace
from backend.workspace_templates import paper_template, TEMPLATE_ROOT


@pytest.fixture
def ws(tmp_path):
    vault = tmp_path/'Vault'; (vault/'.obsidian').mkdir(parents=True)
    workspace = Workspace(SimpleNamespace(vault=vault, store=Store(tmp_path/'data')))
    workspace.configure(str(vault))
    return workspace


def snapshot(root):
    return {str(path.relative_to(root)):path.read_bytes() for path in root.rglob('*') if path.is_file()}


def place_template(ws, title='My new paper', key='my-study'):
    raw, _ = paper_template(title, key)
    with ZipFile(io.BytesIO(raw)) as archive:
        archive.extractall(ws.root)
    return ws.root/title


def test_manual_root_is_discovered_without_read_time_changes(ws):
    folder = place_template(ws)
    before = snapshot(ws.lab.vault)
    catalogue = ws.catalogue()
    assert catalogue['issues'] == [] and len(catalogue['papers']) == 1
    assert catalogue['papers'][0]['id'] == 'my-study'
    assert Path(catalogue['papers'][0]['path']).name == 'root.md'
    assert (folder/'START_HERE.md').is_file()
    assert snapshot(ws.lab.vault) == before
    nodes = ws.tree(ws.read(folder/'root.md'))
    assert len(nodes) == 4
    assert all(node['fields']['Manuscript prose'] == '' for node in nodes if node['type']=='argument')
    assert all(node['writing_status'] == 'empty' for node in nodes)
    assert snapshot(ws.lab.vault) == before


def test_user_fills_manual_argument_and_opens_existing_text(ws):
    folder = place_template(ws)
    path = folder/'Cards'/'02_Introduction_argument.md'
    raw = path.read_text().replace('## Manuscript prose\n', '## Manuscript prose\n\nMy own opening paragraph.\n')
    path.write_text(raw)
    opened = ws.card('my-study', 'my-study-introduction-argument')
    assert opened['fields']['Manuscript prose'] == 'My own opening paragraph.'
    assert opened['writing_status'] == 'draft'
    assert Path(opened['path']) == path


def test_unfilled_template_and_missing_root_properties_have_actionable_errors(ws):
    folder = ws.root/'Unfilled'; shutil.copytree(TEMPLATE_ROOT, folder)
    before = snapshot(ws.lab.vault)
    result = ws.catalogue()
    assert not result['papers']
    assert any('Replace any <paper-key>' in issue for issue in result['issues'])
    assert snapshot(ws.lab.vault) == before
    (folder/'root.md').write_text('# My manual root\n\n## Argument order\n')
    result = ws.catalogue()
    assert any('awl_kind: paper' in issue and 'awl_id' in issue for issue in result['issues'])


def test_copied_paper_identity_is_not_silently_reassigned(ws):
    folder = place_template(ws)
    shutil.copytree(folder, ws.root/'Another copied folder')
    before = snapshot(ws.lab.vault)
    result = ws.catalogue()
    assert not result['papers']
    assert any('Duplicate paper identity' in issue and 'fresh blank template' in issue for issue in result['issues'])
    assert snapshot(ws.lab.vault) == before


def test_template_download_keys_are_unique_and_not_fixed_uuids(ws):
    for title, key in [('First paper','first-study'), ('Second paper','second-study')]:
        place_template(ws, title, key)
    result = ws.catalogue()
    assert not result['issues'] and {paper['id'] for paper in result['papers']} == {'first-study','second-study'}
    with pytest.raises(ValueError, match='already in your workspace'):
        paper_template('Third paper', 'first-study', [paper['id'] for paper in result['papers']])
    for key in ('../escape', '<paper-key>', 'contains a space', ''):
        with pytest.raises(ValueError, match='paper key'): paper_template('Paper', key)


def test_unrelated_frontmatter_notes_are_not_paper_errors(ws):
    folder = place_template(ws)
    (folder/'Meeting notes.md').write_text('---\ntype: meeting\n---\n\n# Private notes\n')
    assert ws.catalogue()['issues'] == []


def test_template_endpoint_downloads_only_and_rejects_existing_key(tmp_path):
    vault = tmp_path/'Vault'; (vault/'.obsidian').mkdir(parents=True)
    app = create_app(tmp_path/'data', vault, auto_tutor=False)
    workspace = app.state.lab.workspace; workspace.configure(str(vault))
    client = TestClient(app, base_url='http://127.0.0.1:8765', headers={'Origin':'http://127.0.0.1:8765'})
    before = snapshot(vault)
    response = client.get('/api/workspace/paper-template', params={'title':'My study', 'key':'my-study'})
    assert response.status_code == 200 and response.headers['content-type'] == 'application/zip'
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert 'My study/root.md' in archive.namelist()
        assert 'My study/START_HERE.md' in archive.namelist()
        assert 'awl_id: "my-study"' in archive.read('My study/root.md').decode()
        assert 'Completed prose hash' not in archive.read('My study/Cards/02_Introduction_argument.md').decode()
    assert snapshot(vault) == before
    assert client.get('/api/workspace/manual-paper-guide').status_code == 200
    place_template(workspace, 'Existing', 'my-study')
    response = client.get('/api/workspace/paper-template', params={'title':'Copied', 'key':'my-study'})
    assert response.status_code == 400 and 'already in your workspace' in response.json()['detail']
