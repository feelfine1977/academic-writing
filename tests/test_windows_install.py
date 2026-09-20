"""Windows-specific checks run on Windows CI; they never touch the user's Desktop."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import install


def test_powershell_literal_keeps_paths_with_apostrophes_and_metacharacters():
    assert install.ps_literal("C:\\Users\\Żaneta's & work\\Writing Lab") == "'C:\\Users\\Żaneta''s & work\\Writing Lab'"


@pytest.mark.skipif(os.name != 'nt',reason='Requires the real Windows shortcut COM implementation')
def test_windows_shortcut_roundtrip_with_unicode_and_spaces(tmp_path):
    root=tmp_path/"Żaneta's & writing lab";root.mkdir()
    desktop=tmp_path/'Isolated desktop';desktop.mkdir()
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    assert pythonw.is_file(),'The Python Windows distribution must include pythonw.exe'
    install.windows_shortcut(pythonw,root,destination=desktop)
    shortcut=desktop/'Writing Lab.lnk'
    assert shortcut.is_file()
    script="[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $shell=New-Object -ComObject WScript.Shell; $link=$shell.CreateShortcut("+install.ps_literal(shortcut)+"); @{target=$link.TargetPath;arguments=$link.Arguments;working=$link.WorkingDirectory}|ConvertTo-Json -Compress"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],check=True,capture_output=True,text=True,encoding='utf-8')
    saved=json.loads(result.stdout)
    assert Path(saved['target'])==pythonw
    assert Path(saved['working'])==root
    assert saved['arguments']==subprocess.list2cmdline(['-X','utf8',str(root/'desktop.py')])
