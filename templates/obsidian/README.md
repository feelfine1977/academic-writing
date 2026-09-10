# Paper starter templates

These templates describe the paper format used by Writing Lab 0.16 and later.
Every paper has a root outline linking its sections, optional subsections and
arguments. Ordinary Markdown keeps the paper readable in Obsidian.

## Without code

In the app, choose **My papers → New paper** and enter a title. Add sections,
subsections and arguments as needed, or paste the example outline. The app assigns
identities and creates all the links. To open a generated folder already in your
vault, choose **Open Obsidian paper folder** and provide that folder's path.

The individual template files are field examples, not complete identified projects.
Use the app or generator to create valid metadata; copying a generated paper keeps
its identity and is a backup, not a different project.

Start from bullets, prose or a blank card. There is no requirement to complete the
whole template before writing. Source excerpts stay in Source mapping; notes and
questions stay in Notes; candidate paper text belongs in Manuscript prose.

## Generate a linked folder from an outline

The included `create_paper_workspace.py` needs only Python 3.10 or later, with no
third-party packages. It makes fresh identities and links and refuses to overwrite
an existing folder. The input convention is demonstrated in `Example outline.md`.
Use the generator or the unassigned template files for each new paper. Copying a
generated paper retains its identities and is a backup, not a newly identified project.

On Mac, from the folder containing the generator:

```sh
python3 create_paper_workspace.py --title "My next paper" --output "My next paper" --outline "Templates/Example outline.md"
```

On Windows:

```powershell
py create_paper_workspace.py --title "My next paper" --output "My next paper" --outline "Templates/Example outline.md"
```

Omit `--outline` to create one blank argument card. Move the resulting folder into
your vault. Open `Paper outline.md`. This utility creates notes; it does not set up the full
app, configure Sync, generate content, or provide automatic revision history.

## Template fields

The hierarchy is **Paper → Section → Subsection (optional) → Argument**. A section
may also contain arguments directly. Section and subsection cards hold purpose,
main message, scope and ordered child arguments. Argument cards hold actual prose.
Every level can begin empty or with bullets. Use the separate Section and Subsection
templates to plan the overall structure before filling in arguments.

In a generated outline, use `## Section: Introduction`,
`### Subsection: Motivation`, and `#### Argument: Why this matters`.
The example demonstrates these markers. Plain `## Argument title` remains valid
for a simple list of argument cards. Named fields still use headings such as
`### Purpose` or `### Manuscript prose`. Structural type labels are explicit so a
heading inside an ordinary note is not silently interpreted as a subsection.

- **Purpose:** what this argument should help the reader understand.
- **Notes and bullet points:** ideas, questions, planned support and alternatives.
- **Source mapping:** original passage location and why it fits; sources remain original material.
- **Manuscript prose:** only the candidate text for the paper; blank is valid.
- **Reasoning and decisions:** why wording or an argument changed; distinguish author decisions from advice.
- **Next step:** one action that makes restarting easier.

Supervisor agreement belongs to a specific source or draft version. Do not mark a
later rewrite as supervisor-agreed simply because it inherited an earlier card.
Keep a separate backup of your vault. Let Obsidian Sync finish before switching computers.
