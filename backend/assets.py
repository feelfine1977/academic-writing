"""Optional private teaching/paper data kept in the user's vault, outside app releases."""
from pathlib import Path
import json

NAMES={'wise/writing_checks.json':'Paper writing checks.md','wise/blueprint.json':'Paper blueprint.md','wise/cards.json':'Research card catalogue.md','wise/vocabulary.json':'Paper vocabulary.md',
       'teaching_support.json':'Teaching examples.md','tutor_materials.json':'Tutor reference notes.md',
       'advanced/learning.json':'Advanced course catalogue.md','plain_examples.json':'Plain English examples.md'}


def load(root,name,default=None,vault=None):
    if vault and name in NAMES:
        path=Path(vault)/'06_Academic_Writing_Lab'/'Private library'/NAMES[name]
        if path.is_file():
            if path.stat().st_size>20_000_000:raise ValueError('Private library note is too large: '+path.name)
            raw=path.read_text(encoding='utf-8');marker='\n```json\n'
            if marker not in raw or not raw.endswith('\n```\n'):raise ValueError('Private library note is incomplete; let Obsidian Sync finish: '+path.name)
            return json.loads(raw.split(marker,1)[1][:-5])
    path=Path(root)/'content'/name
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else default


def backup_library(root,vault):
    from .workspace import atomic_write
    directory=Path(vault)/'06_Academic_Writing_Lab'/'Private library';directory.mkdir(parents=True,exist_ok=True)
    for name,title in NAMES.items():
        source=Path(root)/'content'/name
        if not source.is_file():continue
        path=directory/title
        if not path.exists():atomic_write(path,'# '+title[:-3]+'\n\nPrivate supporting material for your Writing Lab.\n\n```json\n'+source.read_text(encoding='utf-8').strip()+'\n```\n',exclusive=True)
