"""Resolve registered PDFs on this computer or inside the user's synced vault."""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re


ATTACHMENT_MAP = '06_Academic_Writing_Lab/Private library/Reading attachments.md'


class ReadingUnavailable(ValueError):
    """A reading is known, but its private attachment cannot be opened safely."""


def vault_attachment(vault, relative):
    """Portable separators are accepted; absolute paths and escaping links are not."""
    if not isinstance(relative, str) or not relative.strip() or '\x00' in relative:
        raise ReadingUnavailable('The reading attachment needs a path relative to your Obsidian vault.')
    windows = PureWindowsPath(relative)
    portable = PurePosixPath(relative.replace('\\', '/'))
    if windows.drive or windows.root or portable.is_absolute() or '..' in portable.parts or any(':' in part for part in portable.parts):
        raise ReadingUnavailable('Reading attachment paths must stay inside your selected Obsidian vault.')
    root = Path(vault).resolve()
    path = root.joinpath(*portable.parts)
    if not path.resolve().is_relative_to(root):
        raise ReadingUnavailable('Reading attachment paths must stay inside your selected Obsidian vault.')
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ReadingUnavailable('Reading attachments cannot use symbolic links. Put a copy inside your vault.')
    return path


def attachment_map(vault):
    path = vault_attachment(vault, ATTACHMENT_MAP)
    if not path.is_file():
        return {}
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError('Oversized reading attachment map')
        raw = path.read_text(encoding='utf-8')
        blocks = re.findall(r'^```json\s*\n(.*?)^```\s*$', raw, re.M | re.S)
        if len(blocks) != 1:
            raise ValueError('Expected one JSON block')
        value = json.loads(blocks[0])
        if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('readings'), dict):
            raise ValueError('Expected a version 1 reading map')
        return value['readings']
    except (OSError, UnicodeError, ValueError) as error:
        raise ReadingUnavailable('Reading attachments.md could not be read. Let Obsidian Sync finish, then check its version 1 JSON reading map.') from error


def resolve_reading(reading_id, registered, vault):
    """Only registered IDs can be served; the private map supplies portable paths."""
    if reading_id not in registered:
        raise ReadingUnavailable('This reading is not registered in your library. Open it from a lesson or your paper outline.')
    mappings = attachment_map(vault)
    if reading_id in mappings:
        path = vault_attachment(vault, mappings[reading_id])
    else:
        configured = registered[reading_id]
        if not isinstance(configured, str) or not configured.strip() or '\x00' in configured:
            configured = ''
        # A foreign drive or UNC path must never become a local relative filename.
        native = Path(configured)
        foreign = PureWindowsPath(configured)
        if configured and native.is_absolute():
            path = native  # Existing, explicitly registered local PDFs still work.
        elif configured and not (foreign.drive or foreign.root or PurePosixPath(configured).is_absolute()):
            path = vault_attachment(vault, configured)
        else:
            path = None
    try:
        if path and path.suffix.lower() == '.pdf' and path.is_file():
            return path
    except OSError:
        pass
    raise ReadingUnavailable('This PDF is not available on this computer. Let Obsidian Sync finish and select the same vault. If the PDF was stored only on another computer, copy it into your vault and add its reading ID to Private library/Reading attachments.md.')
