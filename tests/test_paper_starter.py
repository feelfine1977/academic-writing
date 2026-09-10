from pathlib import Path
import importlib.util
import re
from urllib.parse import unquote, quote

import pytest

spec = importlib.util.spec_from_file_location("paper_starter", Path(__file__).parents[1] / "scripts/create_paper_workspace.py")
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


def test_mixed_outline_retains_notes_empty_prose_unknown_sections_and_code():
    cards = starter.read_outline("## First\n- A bullet\n### My unusual heading\nKeep this.\n### Manuscript prose\nActual prose.\n```md\n## Not a card\n```\n## Second\n- Plan only\n## Third\n")
    assert len(cards) == 3
    assert "### My unusual heading\nKeep this." in cards[0]["Notes and bullet points"]
    assert "## Not a card" in cards[0]["Manuscript prose"]
    assert cards[1]["Manuscript prose"] == ""
    assert cards[2]["Notes and bullet points"] == ""


def test_creates_linked_utf8_folder_and_refuses_existing_destination(tmp_path):
    destination = tmp_path / "Paper – Łódź"
    result = starter.create_paper(destination, "Museum [study]", starter.read_outline("## Claim\n- idée\n## Limit\n### Manuscript prose\nA narrow claim."))
    overview = (destination / "Paper outline.md").read_text(encoding="utf-8")
    targets = re.findall(r"\]\((Cards/[^)]+)\)", overview)
    assert len(targets) == 2
    assert all((destination / unquote(target)).is_file() for target in targets)
    assert "idée" in (destination / unquote(targets[0])).read_text(encoding="utf-8")
    assert "A narrow claim." in (destination / unquote(targets[1])).read_text(encoding="utf-8")
    assert len(set(result["card_ids"])) == 2
    with pytest.raises(FileExistsError):
        starter.create_paper(destination, "Other", starter.read_outline("replacement"))
    assert (destination / "Paper outline.md").read_text(encoding="utf-8") == overview


def test_invalid_card_does_not_create_folder_or_drop_data(tmp_path):
    destination = tmp_path / "bad"
    with pytest.raises(ValueError, match="Unknown card field"):
        starter.create_paper(destination, "Title", [{"title": "Card", "unexpected": "valuable notes"}])
    assert not destination.exists()
    assert starter.read_outline("- A bullet")[0]["Manuscript prose"] == ""


def test_a_fence_with_trailing_text_does_not_split_a_card():
    text = "## One\n### Manuscript prose\n```text\n```not-a-close\n## This is code\n```\n## Two\n"
    cards = starter.read_outline(text)
    assert len(cards) == 2
    assert "```not-a-close\n## This is code\n```" in cards[0]["Manuscript prose"]


def test_outline_failure_never_publishes_a_complete_paper(tmp_path, monkeypatch):
    original = Path.open
    def fail_outline(path, *args, **kwargs):
        if path.name == "Imported outline.md":
            raise OSError("Disk full")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_outline)
    destination = tmp_path / "partial"
    with pytest.raises(OSError, match="Disk full"):
        starter.create_paper(destination, "Title", starter.read_outline("- Notes"), "- Notes")
    assert not (destination / "Paper outline.md").exists()


def test_hierarchy_preserves_plan_cards_and_links_to_arguments(tmp_path):
    outline = """## Section: Introduction
### Purpose
Explain the problem.
### Subsection: Motivation
### Main message
There is a missing explanation.
#### Paragraph: Existing evidence
- Notes only
#### Paragraph: Open question
### Manuscript prose
Some evidence is still missing.
## Section: Discussion
"""
    cards = starter.read_outline(outline)
    assert [c["kind"] for c in cards] == ["section", "subsection", "argument", "argument", "section"]
    assert [c["parent_index"] for c in cards] == [None, 0, 1, 1, None]
    result = starter.create_paper(tmp_path / "paper", "Title", cards, outline)
    root = Path(result["path"])
    ids = result["card_ids"]
    names = result["filenames"]
    overview = (root / "Paper outline.md").read_text(encoding="utf-8")
    assert "    - [Subsection: Motivation]" in overview
    assert "        - [Argument: Existing evidence]" in overview
    section = (root / "Cards" / names[0]).read_text(encoding="utf-8")
    subsection = (root / "Cards" / names[1]).read_text(encoding="utf-8")
    paragraph = (root / "Cards" / names[2]).read_text(encoding="utf-8")
    assert "[Motivation](" + quote(names[1]) + ")" in section
    assert "[Parent: Introduction](" + quote(names[0]) + ")" in subsection
    assert "[Parent: Motivation](" + quote(names[1]) + ")" in paragraph
    assert "[After](" + quote(names[3]) + ")" in paragraph
    assert "## Manuscript prose" not in section
    assert (root / "Imported outline.md").read_text(encoding="utf-8") == outline


def test_subsection_without_parent_reports_problem_before_writing():
    with pytest.raises(ValueError, match="Subsection needs a Section"):
        starter.read_outline("### Subsection: Orphan\n- Keep this text")
