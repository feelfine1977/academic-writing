import hashlib
import io
import zipfile
from pathlib import Path
import pytest
import setup_voice as voice


def test_checksum_failure_preserves_existing_file(tmp_path, monkeypatch):
    target = tmp_path/'model.bin'; target.write_bytes(b'previous')
    monkeypatch.setattr(voice.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(b'wrong'))
    with pytest.raises(ValueError, match='checksum'):
        voice.download('https://example.org/model', target, hashlib.sha256(b'right').hexdigest(), 100)
    assert target.read_bytes() == b'previous'
    assert not list(tmp_path.glob('*.download'))


def test_valid_download_is_reused_without_network(tmp_path, monkeypatch):
    target = tmp_path/'model.bin'; target.write_bytes(b'valid')
    monkeypatch.setattr(voice.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('unnecessary download'))
    assert voice.download('https://example.org/model', target, hashlib.sha256(b'valid').hexdigest(), 100) == target


@pytest.mark.parametrize('entry', ['../outside', '/absolute', 'Release/../../outside', 'C:/outside', 'Release\\..\\outside'])
def test_engine_archive_rejects_unsafe_paths_before_extracting(tmp_path, entry):
    archive = tmp_path/'engine.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('Release/whisper-cli.exe', b'example')
        zipped.writestr(entry, b'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        voice.unpack_engine(archive, tmp_path/'installed')
    assert not (tmp_path/'installed').exists()


def test_engine_keeps_runtime_libraries(tmp_path):
    archive = tmp_path/'engine.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('Release/whisper-cli.exe', b'example')
        zipped.writestr('Release/ggml.dll', b'library')
    engine = voice.unpack_engine(archive, tmp_path/'installed')
    assert engine.is_file() and (engine.parent/'ggml.dll').is_file()


def test_data_location_obeys_explicit_then_env_then_existing_install(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, 'ROOT', tmp_path)
    monkeypatch.setenv('AWL_DATA_DIR', str(tmp_path/'env'))
    assert voice.data_directory(tmp_path/'explicit') == tmp_path/'explicit'
    assert voice.data_directory() == tmp_path/'env'
    monkeypatch.delenv('AWL_DATA_DIR')
    (tmp_path/'data').mkdir(); (tmp_path/'data/lab.sqlite3').touch()
    assert voice.data_directory() == tmp_path/'data'


def test_setup_keeps_stable_package_manager_symlink(tmp_path):
    versioned = tmp_path/'version-one'; versioned.write_bytes(b'executable')
    stable = tmp_path/'ffmpeg'
    try:
        stable.symlink_to(versioned)
    except OSError:
        pytest.skip('Creating symbolic links is unavailable on this machine.')
    assert voice.existing_executable(str(stable), 'unavailable-example-command') == str(stable)
