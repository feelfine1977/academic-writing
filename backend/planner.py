"""Write tasks to the existing Papyr Obsidian planner, without operating the device."""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
import os
import re
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .workspace import Conflict, atomic_write

FOLDER = Path('Papyr/Planner')
TEMPLATE = Path('Papyr/Templates/Daily planning template.md')
PERIOD_FOLDERS = ('', 'Weekly', 'Monthly', 'Yearly')
SYNC_HELP = 'In Obsidian on your Mac, run “Papyr USB: Sync daily planner to Papyr (USB)” or the Wi-Fi sync command. Saving here does not transfer to the reader.'


class PlannerTask(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    day: date
    pomodoros: int = Field(default=0, ge=0, le=99, strict=True)
    route: str = Field(default='', max_length=1000)
    source_path: str = Field(default='', max_length=1500)

    @field_validator('title')
    @classmethod
    def one_line(cls, value):
        if not value.strip() or any(ord(c)<32 for c in value) or re.search(r'<!--|\[pomodoros::|\[due::|📅', value, re.I):
            raise ValueError('Use a single-line action. Choose the date and Pomodoro estimate in their own fields.')
        return value.strip()

    @field_validator('route')
    @classmethod
    def local_route(cls, value):
        if value and not re.fullmatch(r'#(?:reading|papers|paper|practice|fiction|revision|section-writing)/[A-Za-z0-9%_:@.?=&-]+',value):
            raise ValueError('Use a Writing Lab task link.')
        return value


def insert_task(text, block):
    """Skip fenced examples and YAML; retain every existing byte of note text."""
    eol = '\r\n' if '\r\n' in text else '\n'
    fence = None
    metadata = text.startswith(('---\n','---\r\n'))
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if metadata:
            if i and stripped in ('---','...'): metadata=False
            continue
        match=re.match(r'^\s*(`{3,}|~{3,})',line)
        if match:
            mark=match[1]
            if fence is None: fence=mark
            elif mark[0]==fence[0] and len(mark)>=len(fence): fence=None
            continue
        if not fence and re.fullmatch(r'##\s+Tasks\s*',stripped,re.I):
            if not line.endswith(('\n','\r')): lines[i]+=eol
            lines.insert(i+1,eol+block.replace('\n',eol)+eol)
            return ''.join(lines)
    if fence or metadata: raise ValueError('Close the unfinished Markdown fence or properties block in the planner note before adding a task.')
    return text+('' if text.endswith(eol) else eol)+eol+'## Tasks'+eol+eol+block.replace('\n',eol)+eol


class Planner:
    def __init__(self, workspace): self.ws=workspace

    def status(self):
        status=self.ws.status()
        return {'enabled':status['enabled'] and status['available'], 'folder':FOLDER.as_posix(),
                'today':date.today().isoformat(), 'sync_help':SYNC_HELP}

    def existing(self, marker):
        for folder in PERIOD_FOLDERS:
            directory=self.ws.safe(self.ws.lab.vault/FOLDER/folder)
            for path in directory.glob('*.md'):
                path=self.ws.safe(path)
                if path.stat().st_size>2_000_000: raise ValueError('A planner note is too large to check safely: '+path.name)
                if marker in path.read_text(encoding='utf-8'): return path
        return None

    def add(self, task, origin):
        self.ws.require_enabled()
        parsed=urlsplit(origin)
        if parsed.scheme not in ('http','https') or parsed.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('The return link must point to this local Writing Lab.')
        with self.ws.lock:
            marker='<!-- papyr-task:'+str(task.request_id)+' -->'
            existing=self.existing(marker)
            if existing: return self.receipt(existing,task,True)
            vault=self.ws.lab.vault
            path=self.ws.safe(vault/FOLDER/(task.day.isoformat()+'.md'))
            before=path.read_bytes() if path.exists() else None
            if before is not None:
                text=before.decode('utf-8')
                if re.search(r'^demo:\s*true\s*$',text,re.M):
                    raise ValueError('This date has a demo planner note. Choose another date or turn off its demo flag in Obsidian before adding real work.')
            else:
                template=self.ws.safe(vault/TEMPLATE)
                if template.is_file():
                    if template.stat().st_size>200_000: raise ValueError('The daily planning template is too large.')
                    text=template.read_text(encoding='utf-8').replace('{{date}}',task.day.isoformat())
                    if re.search(r'^demo:\s*true\s*$',text,re.M): raise ValueError('Use a non-demo daily planning template.')
                else:
                    day=task.day.isoformat()
                    text=f'---\ntype: papyr-daily\ndate: {day}\ndemo: false\n---\n\n# {day} - Daily plan\n\n## Focus\n\n## Tasks\n\n## Schedule\n\n| Time | Appointment |\n| --- | --- |\n\n## Notes\n\n'
            block='- [ ] '+task.title+(f' [pomodoros:: {task.pomodoros}]' if task.pomodoros else '')+' '+marker
            if task.source_path:
                source=self.ws.safe(vault/task.source_path)
                if source.suffix.lower()!='.md' or not source.is_file(): raise ValueError('The source note is not available in this vault. Wait for Obsidian Sync or omit the source link.')
                relative=os.path.relpath(source,path.parent).replace(os.sep,'/')
                block+='\n  - [Open source note in Obsidian]('+quote(relative,safe='/')+')'
            if task.route: block+='\n  - [Continue in Writing Lab]('+origin.rstrip('/')+'/'+task.route+')'
            after=insert_task(text,block)
            if before is None:
                try: atomic_write(path,after,exclusive=True)
                except FileExistsError: raise Conflict('This planner date was just created elsewhere. Retry; existing tasks will be kept.')
            else: self.replace(path,before,after)
            return self.receipt(path,task,False)

    def replace(self,path,before,after):
        # Keep the displaced inode (including late writes by an editor), and
        # refuse to publish over an external edit or a newly recreated path.
        if self.ws.safe(path).read_bytes()!=before: raise Conflict('The planner changed during saving. Retry after Obsidian Sync finishes.')
        directory=self.ws.safe(self.ws.lab.vault/'06_Academic_Writing_Lab'/'Planner backups'/path.stem)
        directory.mkdir(parents=True,exist_ok=True)
        kept=directory/(datetime.now(timezone.utc).strftime('%Y-%m-%d %H%M%S.%f')+' - '+str(uuid.uuid4())[:8]+'.md')
        os.rename(path,kept)
        try:
            if kept.read_bytes()!=before: raise Conflict('The planner changed during saving. Its text is kept in Planner backups; retry after sync.')
            atomic_write(path,after,exclusive=True)
        except Exception:
            if not path.exists():
                try: os.link(kept,path)
                except OSError: pass
            raise Conflict('The planner could not be updated safely. The previous text is in Planner backups. Check the date note, then retry.')

    def receipt(self,path,task,already):
        return {'saved':True,'already_saved':already,'task_id':str(task.request_id),
                'path':path.relative_to(self.ws.lab.vault).as_posix(),'uri':self.ws.uri(path),
                'sync_help':SYNC_HELP,'device_synced':False}


def router(planner):
    r=APIRouter(prefix='/api/planner')
    @r.get('')
    def status(): return planner.status()
    @r.post('/tasks')
    def add(body:PlannerTask,request:Request): return planner.add(body,str(request.base_url))
    return r
