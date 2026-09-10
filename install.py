"""Install a local Python environment and per-user desktop shortcut. No administrator access."""
from pathlib import Path
import json
import os
import plistlib
import shlex
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent


def ps_literal(value):return "'"+str(value).replace("'","''")+"'"


def install():
    if sys.version_info<(3,12):raise RuntimeError('Install Python 3.12 or newer from python.org, then run setup again.')
    if os.name!='nt' and sys.platform!='darwin':raise RuntimeError('This shortcut installer supports Windows and macOS. On Linux, use the local-start instructions.')
    environment=ROOT/'.venv';python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    from desktop import user_directory
    local=user_directory();local.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':
        pythonw=environment/'Scripts/pythonw.exe'
        script="$desktop=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject WScript.Shell; $link=$shell.CreateShortcut((Join-Path $desktop 'Academic Writing Lab.lnk')); "
        script+='$link.TargetPath='+ps_literal(pythonw)+'; $link.Arguments='+ps_literal(subprocess.list2cmdline([str(ROOT/'desktop.py')]))+'; $link.WorkingDirectory='+ps_literal(ROOT)+'; $link.Description='+ps_literal('Open your local writing and learning workspace')+'; $link.Save()'
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],check=True)
        shortcut='Desktop → Academic Writing Lab'
    else:
        app=Path.home()/'Applications'/'Academic Writing Lab Portable.app';contents=app/'Contents';binary=contents/'MacOS';binary.mkdir(parents=True,exist_ok=True)
        launcher=binary/'WritingLab';launcher.write_text('#!/bin/sh\nexec '+shlex.quote(str(python))+' '+shlex.quote(str(ROOT/'desktop.py'))+'\n',encoding='utf-8');launcher.chmod(0o755)
        info={'CFBundleExecutable':'WritingLab','CFBundleIdentifier':'local.academicwritinglab.portable','CFBundleName':'Academic Writing Lab','CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'0.16','LSUIElement':True}
        (contents/'Info.plist').write_bytes(plistlib.dumps(info));shortcut=str(app)
    (local/'installation.json').write_text(json.dumps({'application_folder':str(ROOT),'shortcut':shortcut},indent=2),encoding='utf-8')
    print('Installed. Open '+shortcut+'. Keep the application folder at '+str(ROOT)+'.')
    print('Choose your local Obsidian vault in My papers. Ollama is optional for writing; select an installed model in Settings for tutor feedback.')


if __name__=='__main__':
    try:install()
    except Exception as error:print('Setup could not finish: '+str(error),file=sys.stderr);sys.exit(1)
