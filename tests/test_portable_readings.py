"""Private PDF links survive copying a vault between Mac and Windows."""
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.main import create_app
from backend.readings import ATTACHMENT_MAP, ReadingUnavailable, resolve_reading


def pdf(path, text=b'private fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'%PDF-1.4\n'+text)
    return path


def map_readings(vault, readings):
    path=vault/ATTACHMENT_MAP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Reading attachments\n\n```json\n'+json.dumps({'version':1,'readings':readings})+'\n```\n',encoding='utf-8')


def test_relative_pdf_resolves_on_copied_vault_with_either_separator(tmp_path):
    vault=tmp_path/'Vault with spaces and Ż';vault.mkdir()
    reading=pdf(vault/'Learning materials/Clarity & style.pdf')
    for stored in ['Learning materials/Clarity & style.pdf',r'Learning materials\Clarity & style.pdf']:
        assert resolve_reading('STYLE',{'STYLE':stored},vault)==reading


def test_existing_registered_absolute_pdf_still_works_on_original_computer(tmp_path):
    vault=tmp_path/'vault';vault.mkdir()
    original=pdf(tmp_path/'Downloads/Style.pdf')
    assert resolve_reading('STYLE',{'STYLE':str(original)},vault)==original


@pytest.mark.parametrize('foreign',[
    r'C:\Users\Author\Documents\Style.pdf',
    r'\\old-computer\Documents\Style.pdf',
    r'C:Style.pdf',
])
def test_private_id_map_overrides_old_windows_path_on_any_platform(tmp_path,foreign):
    vault=tmp_path/'vault';vault.mkdir()
    reading=pdf(vault/'Reading attachments/Style.pdf')
    map_readings(vault,{'STYLE':'Reading attachments/Style.pdf'})
    assert resolve_reading('STYLE',{'STYLE':foreign},vault)==reading


@pytest.mark.skipif(os.name=='nt',reason='On Windows the fixture path is native rather than foreign')
def test_windows_drive_path_is_not_a_relative_mac_filename(tmp_path):
    vault=tmp_path/'vault';vault.mkdir()
    windows=r'C:\Users\Author\Style.pdf'
    pdf(vault/windows)  # A misleading filename must not satisfy the old Windows path.
    with pytest.raises(ReadingUnavailable,match='not available on this computer'):
        resolve_reading('STYLE',{'STYLE':windows},vault)


@pytest.mark.parametrize('relative',['../private.pdf','nested/../../private.pdf',r'..\private.pdf',r'C:\private.pdf','/private.pdf','file:///private.pdf'])
def test_mapping_cannot_escape_configured_vault(tmp_path,relative):
    vault=tmp_path/'vault';vault.mkdir()
    pdf(tmp_path/'private.pdf')
    map_readings(vault,{'STYLE':relative})
    with pytest.raises(ReadingUnavailable,match='inside your selected Obsidian vault'):
        resolve_reading('STYLE',{'STYLE':'legacy.pdf'},vault)


def test_relative_catalogue_traversal_is_rejected(tmp_path):
    vault=tmp_path/'vault';vault.mkdir();pdf(tmp_path/'private.pdf')
    with pytest.raises(ReadingUnavailable,match='inside your selected Obsidian vault'):
        resolve_reading('STYLE',{'STYLE':'../private.pdf'},vault)


def test_synced_mapping_does_not_fall_back_to_outdated_local_pdf(tmp_path):
    vault=tmp_path/'vault';vault.mkdir()
    old=pdf(tmp_path/'old.pdf');map_readings(vault,{'STYLE':'New version.pdf'})
    with pytest.raises(ReadingUnavailable,match='Obsidian Sync'):
        resolve_reading('STYLE',{'STYLE':str(old)},vault)


def test_symlink_cannot_expose_pdf_outside_vault(tmp_path):
    vault=tmp_path/'vault';vault.mkdir();outside=pdf(tmp_path/'outside/private.pdf')
    try:(vault/'linked').symlink_to(outside.parent,target_is_directory=True)
    except (OSError,NotImplementedError):pytest.skip('Symlink creation is not permitted on this host')
    with pytest.raises(ReadingUnavailable,match='inside your selected Obsidian vault'):
        resolve_reading('STYLE',{'STYLE':'linked/private.pdf'},vault)


def test_incomplete_synced_map_has_helpful_message(tmp_path):
    vault=tmp_path/'vault';map_readings(vault,{})
    (vault/ATTACHMENT_MAP).write_text('# Reading attachments\n```json\n{',encoding='utf-8')
    with pytest.raises(ReadingUnavailable,match='Let Obsidian Sync finish'):
        resolve_reading('STYLE',{'STYLE':'Style.pdf'},vault)


def test_reading_route_serves_only_registered_pdfs_and_reports_missing_files(tmp_path):
    vault=tmp_path/'vault';vault.mkdir();first=pdf(vault/'Books/Style.pdf')
    app=create_app(data_dir=tmp_path/'data',vault_root=vault,auto_tutor=False)
    lab=app.state.lab
    lab.paper.blueprint={'books':[{'id':'STYLE','path':'Books/Style.pdf'},{'id':'MISSING','path':r'C:\Users\Author\missing.pdf'}]}
    lab.teaching.advanced={'books':[]}
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        result=client.get('/api/paper/readings/STYLE')
        assert result.status_code==200 and result.content==first.read_bytes()
        assert result.headers['content-type']=='application/pdf'
        unknown=client.get('/api/paper/readings/not-registered')
        assert unknown.status_code==404 and 'not registered' in unknown.json()['detail']
        missing=client.get('/api/paper/readings/MISSING')
        assert missing.status_code==404 and 'Obsidian Sync' in missing.json()['detail']
        # Vault selection is live; no path remains pinned to the original machine.
        second_vault=tmp_path/'other-vault';second=pdf(second_vault/'Books/Style.pdf',b'new synced copy')
        lab.vault=second_vault
        assert client.get('/api/paper/readings/STYLE').content==second.read_bytes()
