"""Portable desktop launcher. Uses a per-user database and an identified loopback service."""
from contextlib import contextmanager
from pathlib import Path
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

APP='Writing Lab'
ROOT=Path(__file__).resolve().parent


def user_directory():
    if os.name=='nt':return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'AcademicWritingLab'
    if sys.platform=='darwin':return Path.home()/'Library'/'Application Support'/'AcademicWritingLab'
    return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'academic-writing-lab'


def instance_id(data):return hashlib.sha256(str((Path(data)/'lab.sqlite3').resolve()).encode()).hexdigest()[:16]


def local_json(port,path):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(f'http://127.0.0.1:{port}{path}',timeout=1) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Local response too large.')
        return json.loads(raw)


def healthy(port,data):
    try:
        r=local_json(port,'/api/health')
        return r.get('application')=='academic-writing-lab' and r.get('instance_id')==instance_id(data) and r.get('status')=='ok'
    except (OSError,ValueError,AttributeError):return False


def occupied(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.2):return True
    except OSError:return False


@contextmanager
def launch_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        end=time.monotonic()+40
        while True:
            try:
                if os.name=='nt':
                    import msvcrt
                    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()>end:raise RuntimeError('Another launch is still starting. Try again shortly.')
                time.sleep(.15)
        try:yield
        finally:
            if os.name=='nt':
                import msvcrt
                f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_UN)


def launch(data=None,port=8765,open_browser=True):
    data=Path(data or os.environ.get('AWL_DATA_DIR') or user_directory()/'data').resolve();data.mkdir(parents=True,exist_ok=True)
    with launch_lock(data/'runtime'/'desktop.lock'):
        chosen=None
        for candidate in range(port,port+15):
            if healthy(candidate,data):chosen=candidate;break
        if chosen is None:
            chosen=next((p for p in range(port,port+15) if not occupied(p)),None)
            if chosen is None:raise RuntimeError('No free local port was found. Existing services were left running.')
            python=ROOT/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
            if not python.exists():raise RuntimeError('Run Install on Windows.cmd or Install on Mac.command first.')
            env=os.environ.copy();env.update(AWL_DATA_DIR=str(data),PYTHONUNBUFFERED='1',PYTHONUTF8='1')
            flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
            log=data/'runtime'/'server.log'
            with log.open('a',encoding='utf-8') as stream:
                child=subprocess.Popen([str(python),'-X','utf8',str(ROOT/'start.py'),'--port',str(chosen)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,**flags)
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if healthy(chosen,data):break
                if child.poll() is not None:raise RuntimeError('The local service could not start. See '+str(log))
                time.sleep(.3)
            else:raise RuntimeError('The service is still starting. Reopen the shortcut shortly; see '+str(log))
        url=f'http://127.0.0.1:{chosen}/#papers'
        if open_browser:webbrowser.open(url)
        return url


def show_error(message):
    if os.name=='nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,message,APP,0x10)
    elif sys.platform=='darwin':
        script='on run argv\n display dialog (item 1 of argv) with title "Writing Lab" buttons {"OK"} default button "OK"\nend run'
        subprocess.run(['/usr/bin/osascript','-e',script,message],check=False)
    else:print(message,file=sys.stderr)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data');parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-open',action='store_true');args=parser.parse_args()
    try:print(launch(args.data,args.port,not args.no_open))
    except Exception as error:show_error(str(error));sys.exit(1)
