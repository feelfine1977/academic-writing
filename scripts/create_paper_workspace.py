"""Create readable Obsidian paper cards. No app database or existing note is edited.

Standard library only; runs on Windows and macOS with Python 3.10+.
This is a template generator, not the live application's import/sync engine.
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
import unicodedata
from pathlib import Path
from urllib.parse import quote


CARD_FIELDS = ("Purpose", "Notes and bullet points", "Source mapping",
               "Manuscript prose", "Reasoning and decisions", "Next step")
STRUCTURE_FIELDS = ("Purpose", "Main message", "Scope and boundaries", "Notes and bullet points",
                    "Connection to the surrounding argument", "Reasoning and decisions", "Next step")
ALL_FIELDS = tuple(dict.fromkeys(CARD_FIELDS + STRUCTURE_FIELDS))


def portable_name(title: str) -> str:
    """Readable names that also work on Windows; IDs remain inside metadata."""
    title = unicodedata.normalize("NFC", title)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f#%\[\]]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip(' .')[:90].rstrip(' .') or "Untitled"
    if title.split('.')[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM"+str(n) for n in range(1,10)), *("LPT"+str(n) for n in range(1,10))}:
        title = "Paper - " + title
    return title


def unique_name(title: str, used: set[str]) -> str:
    stem = portable_name(title); candidate = stem; number = 2
    while candidate.casefold() in used:
        candidate = f"{stem} ({number})"; number += 1
    used.add(candidate.casefold())
    return candidate


def read_outline(text: str) -> list[dict]:
    """Explicit Section/Subsection/Argument labels build a hierarchy.

    An untyped level-2 heading starts a argument card; named level-3 headings
    separate fields, regardless of the card type.

    Everything below a card heading defaults to notes. Unknown level-3 headings
    are retained in their current field. A code fence protects heading-like text.
    We never guess that notes are manuscript prose.
    """
    cards: list[dict] = []
    current = None
    section = subsection = None
    field = "Notes and bullet points"
    fence = None
    preamble = []
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
        typed = re.fullmatch(r"#{2,4} (Section|Subsection|Argument|Paragraph): (.+)", line, re.I) if not fence and not marker else None
        heading = re.fullmatch(r"## ([^\r\n]+)", line) if not fence and not marker else None
        if typed or heading:
            kind = typed.group(1).lower() if typed else "argument"
            if kind == "paragraph": kind = "argument"
            card_title = typed.group(2).strip() if typed else heading.group(1).strip()
            if kind == "section":
                parent = None
                section, subsection = len(cards), None
            elif kind == "subsection":
                if section is None:
                    raise ValueError("A Subsection needs a Section before it in the outline.")
                parent = section
                subsection = len(cards)
            else:
                parent = subsection if subsection is not None else section
            current = {"title": card_title, "kind": kind, "parent_index": parent,
                       **{key: "" for key in ALL_FIELDS}}
            cards.append(current)
            field = "Notes and bullet points"
        elif current is None:
            preamble.append(line)
        elif not fence and line.startswith("### ") and line[4:].strip() in ALL_FIELDS:
            field = line[4:].strip()
        else:
            current[field] += line + "\n"
    if not cards:
        cards = [{"title": "First argument", **{key: "" for key in CARD_FIELDS},
                  "Notes and bullet points": text.strip()}]
    elif any(line.strip() and not line.startswith("# ") for line in preamble):
        # Preserve input that precedes the first card; keep it out of prose.
        cards[0]["Notes and bullet points"] = "\n".join(preamble).strip() + "\n\n" + cards[0]["Notes and bullet points"]
    return [{key: value.strip() if isinstance(value, str) else value for key, value in card.items()} for card in cards]


def frontmatter(values: dict) -> str:
    return "---\n" + "\n".join(key + ": " + json.dumps(value, ensure_ascii=False)
                                for key, value in values.items()) + "\n---\n\n"


def link_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def create_paper(destination: Path, title: str, cards: list[dict], original_outline: str | None = None) -> dict:
    destination = Path(destination)
    if not title.strip() or "\n" in title or "\r" in title:
        raise ValueError("Use a non-empty, single-line paper title.")
    if not cards:
        raise ValueError("Supply at least one card. Empty prose is allowed.")
    for index, card in enumerate(cards):
        if not isinstance(card.get("title"), str) or not card["title"].strip() or any(c in card["title"] for c in "\r\n"):
            raise ValueError("Every card needs a single-line title.")
        if set(card) - {"title", "kind", "parent_index", *ALL_FIELDS}:
            raise ValueError("Unknown card field; refusing to discard input.")
        if not all(isinstance(value, str) for key, value in card.items() if key != "parent_index"):
            raise ValueError("Card fields must be text.")
        kind, parent = card.get("kind", "argument"), card.get("parent_index")
        if kind not in {"section", "subsection", "argument"}:
            raise ValueError("Unknown card type.")
        if parent is not None and (type(parent) is not int or not 0 <= parent < index):
            raise ValueError("A parent must refer to an earlier structure card.")
        parent_kind = cards[parent].get("kind", "argument") if parent is not None else None
        if ((kind == "section" and parent is not None)
                or (kind == "subsection" and parent_kind != "section")
                or (kind == "argument" and parent_kind not in {None, "section", "subsection"})):
            raise ValueError("Use paper → section → optional subsection → argument order.")
    # Exclusive folder creation refuses to overwrite an existing paper, even empty.
    # Paper outline.md is written last; its absence identifies an interrupted generation.
    destination.mkdir(parents=True, exist_ok=False)
    if original_outline is not None:
        with (destination / "Imported outline.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(original_outline)
    (destination / "Cards").mkdir()
    paper_id = str(uuid.uuid4())
    card_ids = [str(uuid.uuid4()) for _ in cards]
    used_names = set()
    filenames = [unique_name(card.get("kind", "argument").capitalize() + " - " + card["title"], used_names) + ".md" for card in cards]
    for index, (card_id, card) in enumerate(zip(card_ids, cards)):
        title_card = card["title"].strip()
        kind, parent = card.get("kind", "argument"), card.get("parent_index")
        body = frontmatter({"awl_schema": 1, "awl_kind": "card", "awl_id": card_id,
                            "card_type": kind, "paper_id": paper_id, "status": "planned", "aliases": [title_card]})
        body += "# " + kind.capitalize() + " · " + title_card + "\n\n[Back to paper](../Paper%20outline.md)"
        if parent is not None:
            body += " · [Parent: " + link_label(cards[parent]["title"]) + "](" + quote(filenames[parent]) + ")"
        siblings = [i for i, candidate in enumerate(cards) if candidate.get("parent_index") == parent]
        position = siblings.index(index)
        if position:
            body += " · [Before](" + quote(filenames[siblings[position - 1]]) + ")"
        if position + 1 < len(siblings):
            body += " · [After](" + quote(filenames[siblings[position + 1]]) + ")"
        body += "\n\n"
        for field in (CARD_FIELDS if kind == "argument" else STRUCTURE_FIELDS):
            body += "## " + field + "\n\n" + card.get(field, "").strip() + "\n\n"
        # Retain non-empty optional fields even when not part of this type's template.
        for field in ALL_FIELDS:
            if field not in (CARD_FIELDS if kind == "argument" else STRUCTURE_FIELDS) and card.get(field):
                body += "## " + field + "\n\n" + card[field].strip() + "\n\n"
        children = [i for i, candidate in enumerate(cards) if candidate.get("parent_index") == index]
        if kind != "argument":
            body += "## Argument inside this " + kind + "\n\n"
            body += "\n".join("- [" + link_label(cards[i]["title"]) + "](" + quote(filenames[i]) + ")" for i in children)
            body += "\n\n"
        with (destination / "Cards" / filenames[index]).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
    def ordered_tree(parent=None, depth=0):
        lines = []
        for index, card in enumerate(cards):
            if card.get("parent_index") != parent:
                continue
            label = card.get("kind", "argument").capitalize() + ": " + card["title"].strip()
            lines.append("    " * depth + "- [" + link_label(label) + "](Cards/" + quote(filenames[index]) + ")")
            lines.extend(ordered_tree(index, depth + 1))
        return lines
    order = ordered_tree()
    guide = """# Start here

Open Paper outline.md in Obsidian, then open a card from the argument order.

1. Read Purpose. Add a short intention if helpful; blanks are allowed.
2. Keep bullets in Notes and bullet points. Put only candidate paper text in Manuscript prose.
3. Link exact original passages under Source mapping; an empty mapping is valid.
4. Record why you keep, change, combine or replace wording under Reasoning and decisions.
5. Leave one small Next step before stopping.

These are ordinary Markdown notes. In Writing Lab 0.16 or later, choose My papers,
connect your Obsidian vault, then choose Open Obsidian paper folder. Select this
folder to edit it in the app with automatic saving and revision history.
The standalone generator only creates the initial notes. Keep a separate backup.

The hierarchy and order in Paper outline.md are the planned authority. Parent, child and
Before/After links in these starter cards are initial navigation aids: if you move
cards manually, update those links or return through Paper outline.md. Card identities stay
stable when titles change. Sections and subsections guide their child arguments;
candidate manuscript prose normally belongs in argument cards.

The outline you supplied is retained in Imported outline.md when supplied through
the command line. No notes are automatically treated as manuscript prose.
"""
    with (destination / "Start here.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(guide)
    paper = frontmatter({"awl_schema": 1, "awl_kind": "paper", "awl_id": paper_id,
                         "status": "planning", "aliases": [title.strip()]})
    paper += "# " + title.strip() + "\n\n[How to use this folder](Start%20here.md)\n\n"
    paper += "## Research question\n\n\n## Intended contribution\n\n\n## Argument order\n\n" + "\n".join(order)
    paper += "\n\n## Agreed plan and open questions\n\n\n## Next writing session\n\n"
    with (destination / "Paper outline.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(paper)
    return {"paper_id": paper_id, "card_ids": card_ids, "filenames": filenames, "path": str(destination.resolve())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="A NEW paper folder; existing folders are never replaced.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--outline", type=Path, help="UTF-8 Markdown: ## Section:, ### Subsection:, #### Argument:; plain ## headings also make arguments.")
    args = parser.parse_args()
    try:
        text = args.outline.read_text(encoding="utf-8-sig") if args.outline else ""
        result = create_paper(args.output, args.title, read_outline(text), text if args.outline else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, "Could not create the paper: " + str(error) + "\n")


if __name__ == "__main__":
    main()
