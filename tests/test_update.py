import subprocess

import pytest

import update


def git(folder, *args):
    return subprocess.run(['git','-C',str(folder),*args],check=True,capture_output=True,text=True).stdout.strip()


@pytest.fixture
def clone(tmp_path, monkeypatch):
    monkeypatch.setattr(update,'running_apps',lambda:[])
    origin=tmp_path/'origin';origin.mkdir()
    git(origin,'init','-b','main')
    git(origin,'config','user.name','Test fixture');git(origin,'config','user.email','test@example.invalid')
    (origin/'app.txt').write_text('first\n')
    git(origin,'add','.');git(origin,'commit','-m','Initial fixture')
    copy=tmp_path/'app'
    subprocess.run(['git','clone',str(origin),str(copy)],check=True,capture_output=True)
    return origin,copy


def test_clean_update_fast_forwards_without_touching_vault(clone,tmp_path):
    origin,copy=clone
    vault=tmp_path/'vault';vault.mkdir();(vault/'draft.md').write_text('My writing')
    (origin/'app.txt').write_text('second\n');git(origin,'commit','-am','Updated fixture')
    result=update.update(copy,install_dependencies=False)
    assert result['updated'] and not result['vault_changed']
    assert (copy/'app.txt').read_text()=='second\n'
    assert (vault/'draft.md').read_text()=='My writing'


def test_local_changes_are_not_overwritten(clone):
    _,copy=clone;(copy/'app.txt').write_text('local edits\n')
    with pytest.raises(RuntimeError,match='local changes'):update.update(copy,install_dependencies=False)
    assert (copy/'app.txt').read_text()=='local edits\n'


def test_running_service_blocks_before_source_changes(clone,monkeypatch):
    origin,copy=clone
    (origin/'app.txt').write_text('second\n');git(origin,'commit','-am','Updated fixture')
    monkeypatch.setattr(update,'running_apps',lambda:[8765])
    with pytest.raises(RuntimeError,match='still running'):update.update(copy,install_dependencies=False)
    assert (copy/'app.txt').read_text()=='first\n'


def test_updater_refuses_subdirectory_of_private_repo(clone):
    _,copy=clone;inner=copy/'private-app';inner.mkdir()
    with pytest.raises(RuntimeError,match='larger private'):update.update(inner,install_dependencies=False)


def test_updater_refuses_zip_directory(tmp_path):
    with pytest.raises(RuntimeError,match='not a Git clone'):update.update(tmp_path,install_dependencies=False)


def test_find_git_uses_github_desktop_bundle_when_path_is_missing(tmp_path,monkeypatch):
    monkeypatch.setattr(update.shutil,'which',lambda _:None)
    older=tmp_path/'GitHubDesktop/app-3.9.1/resources/app/git/cmd/git.exe'
    latest=tmp_path/'GitHubDesktop/app-3.10.2/resources/app/git/cmd/git.exe'
    for path in (older,latest):path.parent.mkdir(parents=True);path.write_bytes(b'fixture')
    assert update.find_git(windows=True,environment={'LOCALAPPDATA':str(tmp_path)})==str(latest)
    latest.unlink()
    assert update.find_git(windows=True,environment={'LOCALAPPDATA':str(tmp_path)})==str(older)


def test_find_git_prefers_installed_path_and_reports_missing_git(tmp_path,monkeypatch):
    executable=tmp_path/'git.exe';executable.write_bytes(b'fixture')
    monkeypatch.setattr(update.shutil,'which',lambda _:str(executable))
    assert update.find_git(windows=True,environment={})==str(executable)
    executable.unlink()
    with pytest.raises(RuntimeError,match='Git was not found'):update.find_git(windows=True,environment={})


def test_missing_git_is_not_reported_as_a_broken_clone(tmp_path,monkeypatch):
    def unavailable():raise RuntimeError('Git was not found. Install Git for Windows.')
    monkeypatch.setattr(update,'find_git',unavailable)
    with pytest.raises(RuntimeError,match='Git was not found'):update.update(tmp_path,install_dependencies=False)


def test_git_output_is_decoded_as_utf8_for_unicode_windows_folders(tmp_path,monkeypatch):
    executable=tmp_path/'git.exe';executable.write_bytes(b'fixture');seen={}
    monkeypatch.setattr(update,'find_git',lambda:str(executable))
    def run(command,**kwargs):
        seen.update(kwargs);seen['command']=command
        return type('Result',(),{'stdout':'C:/Users/Żaneta/Writing Lab\n'})()
    monkeypatch.setattr(update.subprocess,'run',run)
    assert update.git(tmp_path,'rev-parse','--show-toplevel')=='C:/Users/Żaneta/Writing Lab'
    assert seen['encoding']=='utf-8' and seen['command'][0]==str(executable)
