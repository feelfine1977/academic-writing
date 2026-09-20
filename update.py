"""Update a clean source installation; the user's synced vault stays separate."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent


def running_apps():
    # The portable launcher may select another port if the default is occupied.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    found = []
    for port in range(8765, 8780):
        try:
            with opener.open(f'http://127.0.0.1:{port}/api/health', timeout=.25) as response:
                value = json.loads(response.read(4000))
            if value.get('application') == 'academic-writing-lab': found.append(port)
        except (OSError, ValueError): pass
    return found


def find_git(*, windows=None, environment=None):
    """GitHub Desktop does not normally add its bundled Git to PATH."""
    environment = os.environ if environment is None else environment
    windows = os.name == 'nt' if windows is None else windows
    candidates = [shutil.which('git')]
    if windows:
        for variable, relative in [('PROGRAMFILES', 'Git/cmd/git.exe'),
                                   ('LOCALAPPDATA', 'Programs/Git/cmd/git.exe')]:
            if environment.get(variable):
                candidates.append(Path(environment[variable])/relative)
        if environment.get('LOCALAPPDATA'):
            desktop = Path(environment['LOCALAPPDATA'])/'GitHubDesktop'
            def version(path):
                return tuple(int(part) for part in re.findall(r'\d+', path.name))
            for folder in sorted(desktop.glob('app-*'), key=version, reverse=True):
                candidates.append(folder/'resources/app/git/cmd/git.exe')
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    raise RuntimeError('Git was not found. Install Git for Windows from git-scm.com, reopen this window, and try again. If you use GitHub Desktop, its Fetch origin / Pull origin action can update a clean checkout instead.')


def git(root, *args):
    executable = find_git()
    return subprocess.run([executable, '-C', str(root), *args], check=True,
                          capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()


def update(root=ROOT, *, install_dependencies=True):
    root = Path(root).resolve()
    try: top = Path(git(root, 'rev-parse', '--show-toplevel')).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError('This folder is not a Git clone. Clone your public repository with GitHub Desktop or Git, then install it. ZIP downloads can be replaced manually; keep your vault and local data outside the app folder.') from error
    if top != root: raise RuntimeError('Run the updater from the public app repository root, not from a larger private development repository.')
    if git(root, 'status', '--porcelain'):
        raise RuntimeError('The app checkout has local changes. Keep them and review them in GitHub Desktop before updating; no files were overwritten.')
    try: git(root, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    except subprocess.CalledProcessError as error: raise RuntimeError('This branch has no upstream. Clone the published repository or set its intended upstream in Git before updating.') from error
    active = running_apps()
    if active:
        raise RuntimeError('Writing Lab is still running on port '+', '.join(map(str, active))+'. Save your writing and let Obsidian Sync finish. Restart this computer, then run Update before opening Writing Lab. Closing the browser does not stop the background server. No app files were changed.')
    before = git(root, 'rev-parse', 'HEAD')
    git(root, 'pull', '--ff-only')
    after = git(root, 'rev-parse', 'HEAD')
    if install_dependencies:
        python = root/('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
        if not python.is_file(): raise RuntimeError('The source is up to date. Run Install on Windows.cmd or Install on Mac.command to create this computer’s Python environment.')
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root/'requirements.txt')], check=True)
    return {'updated':before != after, 'revision':after, 'vault_changed':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Show the local source revision and running app ports, without downloading changes.')
    args = parser.parse_args()
    try:
        if args.check: print(json.dumps({'revision':git(ROOT, 'rev-parse', 'HEAD'), 'running_ports':running_apps()}, indent=2))
        else:
            result = update()
            print(('Updated to ' if result['updated'] else 'Already at ')+result['revision'][:12]+'. Open your Writing Lab shortcut. Your Obsidian vault and local settings were left in place.')
    except Exception as error:
        print('Update could not finish: '+str(error), file=sys.stderr); sys.exit(1)
