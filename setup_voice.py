"""Optional, machine-local speech setup. Run with the Writing Lab's Python environment."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
MODEL_URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin'
MODEL_SHA = '1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b'
ENGINE_URL = 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.2/whisper-bin-x64.zip'
ENGINE_SHA = '49dcc16de826f20bd53d44f947a1ae49dfa81f86cad67a64d80820cb192d674a'


def data_directory(explicit=None):
    from desktop import user_directory
    return Path(explicit or os.environ.get('AWL_DATA_DIR') or
                (ROOT/'data' if (ROOT/'data/lab.sqlite3').exists() else user_directory()/'data')).expanduser().resolve()


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def download(url, target, expected_sha, max_bytes):
    target = Path(target)
    if target.exists() and digest(target) == expected_sha:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name+'.', suffix='.download', delete=False) as pending:
        temporary = Path(pending.name)
    try:
        total = 0
        with urllib.request.urlopen(url, timeout=60) as source, temporary.open('wb') as output:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError('The speech download exceeded its expected size.')
                output.write(chunk)
        if digest(temporary) != expected_sha:
            raise ValueError('Speech download checksum did not match. Try setup again.')
        os.replace(temporary, target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def unpack_engine(archive, folder):
    """Validate the entire archive before extracting; keep the DLLs beside the CLI."""
    folder = Path(folder)
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if sum(e.file_size for e in entries) > 150_000_000:
            raise ValueError('Speech engine archive is too large.')
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or
                    ':' in entry.filename or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Unsafe path in speech engine archive.')
        if 'Release/whisper-cli.exe' not in zipped.namelist():
            raise ValueError('The speech archive does not contain the expected executable.')
        folder.mkdir(parents=True, exist_ok=True)
        if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob('*')):
            raise ValueError('Speech engine folder must not contain symbolic links.')
        zipped.extractall(folder)
    return folder/'Release/whisper-cli.exe'


def existing_executable(value, name):
    candidates = [value, shutil.which(name)]
    if sys.platform == 'darwin':
        candidates += ['/opt/homebrew/bin/'+name, '/usr/local/bin/'+name]
    # Keep stable package-manager symlinks; resolving into a versioned Cellar
    # directory breaks the next time Homebrew replaces that package version.
    return next((str(Path(p).expanduser().absolute()) for p in candidates if p and Path(p).expanduser().is_file()), None)


def setup(data=None):
    local = data_directory(data)/'speech'
    config_file = local/'config.json'
    try:
        config = json.loads(config_file.read_text(encoding='utf-8'))
    except FileNotFoundError:
        config = {}
    except ValueError as error:
        raise RuntimeError('Check the speech configuration JSON at '+str(config_file)) from error
    if not isinstance(config, dict):
        raise RuntimeError('Speech configuration must be a JSON object: '+str(config_file))
    engine = existing_executable(os.environ.get('AWL_WHISPER_CLI') or config.get('whisper_cli'), 'whisper-cli')
    decoder = existing_executable(os.environ.get('AWL_FFMPEG') or config.get('ffmpeg'), 'ffmpeg')
    print('Setting up local transcription. The multilingual model download is about 488 MB. No recordings are uploaded.', flush=True)
    if os.name == 'nt':
        if not engine:
            if platform.machine().lower() not in ('amd64', 'x86_64'):
                raise RuntimeError('Automatic Windows setup supports x64. Install whisper.cpp for this processor and set AWL_WHISPER_CLI.')
            archive = download(ENGINE_URL, local/'downloads/whisper-bin-x64-v1.9.2.zip', ENGINE_SHA, 10_000_000)
            engine = str(unpack_engine(archive, local/'engines/whisper-v1.9.2'))
        if not decoder:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', 'imageio-ffmpeg==0.6.0'], check=True)
            import imageio_ffmpeg
            decoder = imageio_ffmpeg.get_ffmpeg_exe()
    elif sys.platform == 'darwin':
        if not engine or not decoder:
            brew = existing_executable(None, 'brew')
            if not brew:
                raise RuntimeError('Install Homebrew from brew.sh, then run this setup again; or configure AWL_WHISPER_CLI and AWL_FFMPEG.')
            packages = ([] if engine else ['whisper-cpp']) + ([] if decoder else ['ffmpeg'])
            subprocess.run([brew, 'install', *packages], check=True, env={**os.environ, 'HOMEBREW_NO_AUTO_UPDATE':'1'})
            engine = existing_executable(engine, 'whisper-cli')
            decoder = existing_executable(decoder, 'ffmpeg')
    elif not engine or not decoder:
        raise RuntimeError('Install whisper.cpp and FFmpeg, then run setup again.')
    if not engine or not decoder:
        raise RuntimeError('Speech engine or audio decoder is still missing.')
    configured_model = os.environ.get('AWL_WHISPER_MODEL') or config.get('model')
    if configured_model and Path(configured_model).expanduser().is_file():
        model = Path(configured_model).expanduser().resolve()
    else:
        model = download(MODEL_URL, local/'models/ggml-small.bin', MODEL_SHA, 490_000_000)
    local.mkdir(parents=True, exist_ok=True)
    config.update(whisper_cli=str(engine), ffmpeg=str(decoder), model=str(model))
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=local, delete=False) as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    os.replace(temporary, config_file)
    print('Ready. Open a paper section and choose Speak my idea. Configuration: '+str(config_file))
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', help='The data folder used by this Writing Lab instance.')
    args = parser.parse_args()
    try:
        setup(args.data)
    except Exception as error:
        print('Voice setup could not finish: '+str(error), file=sys.stderr)
        sys.exit(1)
