"""Blank, human-editable paper folders; no LLM, import inference or vault writes."""
from pathlib import Path
import io
import re
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.create_paper_workspace import portable_name


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]/'templates'/'manual-paper'
TEMPLATE_FILES = ('root.md', 'START_HERE.md', 'Cards/01_Introduction.md',
                  'Cards/02_Introduction_argument.md', 'Cards/03_Literature.md',
                  'Cards/04_Literature_argument.md')


def paper_template(title, key, existing_keys=()):
    if not isinstance(title, str) or not title.strip() or len(title) > 150 or any(c in title for c in '\r\n\x00'):
        raise ValueError('Use a non-empty paper title of up to 150 characters on one line.')
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,60}', key):
        raise ValueError('Choose a short paper key, such as coastal-study: up to 61 letters, numbers, hyphens or underscores.')
    if key in existing_keys:
        raise ValueError('That paper key is already in your workspace. Choose a new key for the new paper.')
    folder = portable_name(title)
    output = io.BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name in TEMPLATE_FILES:
            raw = (TEMPLATE_ROOT/name).read_text(encoding='utf-8')
            # The guide explains the literal placeholders; keep its examples.
            if name != 'START_HERE.md':
                raw = raw.replace('<paper-key>', key).replace('<paper-title>', title.strip())
            archive.writestr(folder+'/'+name, raw)
    return output.getvalue(), folder+'.zip'
