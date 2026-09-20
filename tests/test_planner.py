from datetime import date
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

from backend.planner import Planner, PlannerTask, insert_task
from backend.storage import Store
from backend.workspace import Workspace, Conflict


def planner(tmp_path):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    ws=Workspace(SimpleNamespace(store=Store(tmp_path/'data'),vault=vault));ws.configure(str(vault))
    return Planner(ws)


def task(**kw):
    return PlannerTask(request_id=uuid.uuid4(),title='Clarify my reading summary',day=date(2026,9,17),**kw)


def test_add_to_template_with_links_and_pomodoros(tmp_path):
    service=planner(tmp_path);vault=service.ws.lab.vault
    template=vault/'Papyr/Templates/Daily planning template.md';template.parent.mkdir(parents=True)
    template.write_text('---\ntype: papyr-daily\ndate: {{date}}\ndemo: false\n---\n\n# {{date}}\n\n## Tasks\n\n## My custom daily section\n\nKeep this.\n')
    source=vault/'Reading'/'A book.md';source.parent.mkdir();source.write_text('# Book\n')
    request=task(pomodoros=2,route='#reading/abc-123',source_path='Reading/A book.md')
    result=service.add(request,'http://127.0.0.1:8765/')
    raw=(vault/result['path']).read_text()
    assert '[pomodoros:: 2] <!-- papyr-task:'+str(request.request_id)+' -->' in raw
    assert '[Continue in Writing Lab](http://127.0.0.1:8765/#reading/abc-123)' in raw
    assert '../../Reading/A%20book.md' in raw
    assert 'date: 2026-09-17' in raw and 'Keep this.' in raw
    assert result['device_synced'] is False


def test_existing_note_bytes_and_completed_tasks_are_preserved(tmp_path):
    service=planner(tmp_path);path=service.ws.lab.vault/'Papyr/Planner/2026-09-17.md';path.parent.mkdir(parents=True)
    before=b'---\r\ndate: 2026-09-17\r\n---\r\n\r\n# Day\r\n## Tasks\r\n\r\n- [x] Done <!-- papyr-task:03a65e84-75a4-410e-b1e3-7f3634d84cf4 -->\r\n\r\n## Schedule\r\n| 14:00 | Meet supervisor |\r\n\r\n## Notes\r\nMy notes.\r\n'
    path.write_bytes(before)
    service.add(task(),'http://localhost:8765')
    raw=path.read_bytes()
    assert before.split(b'## Tasks\r\n')[1] in raw
    assert raw.count(b'\n')==raw.count(b'\r\n')
    backups=list((service.ws.lab.vault/'06_Academic_Writing_Lab/Planner backups').rglob('*.md'))
    assert len(backups)==1 and backups[0].read_bytes()==before


def test_retries_do_not_duplicate_even_after_task_moves_to_week(tmp_path):
    service=planner(tmp_path);request=task()
    result=service.add(request,'http://localhost:8765')
    daily=service.ws.lab.vault/result['path'];weekly=daily.parent/'Weekly/2026-W38.md';weekly.parent.mkdir();daily.rename(weekly)
    retry=service.add(request,'http://localhost:8765')
    assert retry['already_saved'] and retry['path'].endswith('Weekly/2026-W38.md')
    assert weekly.read_text().count('<!-- papyr-task:')==1 and not daily.exists()


def test_fenced_fake_tasks_heading_is_not_targeted():
    before='---\nexample: |\n  ## Tasks\n---\n\n```md\n## Tasks\n```\n\n## Tasks\n\n## Notes\nKeep'
    after=insert_task(before,'- [ ] My action')
    assert '```md\n## Tasks\n```' in after
    assert after.endswith('## Tasks\n\n- [ ] My action\n\n## Notes\nKeep')


def test_refuses_demo_symlink_and_injected_metadata(tmp_path):
    service=planner(tmp_path);path=service.ws.lab.vault/'Papyr/Planner/2026-09-17.md';path.parent.mkdir(parents=True)
    path.write_text('---\ndemo: true\n---\n## Tasks\n')
    with pytest.raises(ValueError,match='demo'):service.add(task(),'http://localhost:8765')
    path.unlink();outside=tmp_path/'outside.md';outside.write_text('private');path.symlink_to(outside)
    with pytest.raises(ValueError):service.add(task(),'http://localhost:8765')
    assert outside.read_text()=='private'
    for title in ('One\n- [ ] Two','Make a plan [pomodoros:: 2]','Wrong date 📅 2028-01-01'):
        with pytest.raises(ValueError):PlannerTask(request_id=uuid.uuid4(),title=title,day='2026-09-17')


def test_external_change_before_publish_is_kept(tmp_path,monkeypatch):
    service=planner(tmp_path);request=task();service.add(request,'http://localhost:8765')
    path=service.ws.lab.vault/'Papyr/Planner/2026-09-17.md'
    original=path.read_bytes();rename=__import__('os').rename
    def race(src,dst):
        Path(src).write_bytes(original+b'\nExternal new text.\n');rename(src,dst)
    monkeypatch.setattr('backend.planner.os.rename',race)
    with pytest.raises(Conflict):service.add(task(),'http://localhost:8765')
    assert path.read_bytes().endswith(b'External new text.\n')
    assert path.read_text().count('<!-- papyr-task:')==1
