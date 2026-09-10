# Writing Lab on Mac and Windows

## Start the app

Download or clone the repository into a permanent folder. Install Python 3.12 or newer first. On Windows, enable the Python launcher when installing Python.

- **Windows:** double-click `Install on Windows.cmd` once. Then use the **Academic Writing Lab** shortcut on your Desktop, or `Start on Windows.cmd`.
- **Mac:** double-click `Install on Mac.command` once. Then open **Academic Writing Lab Portable.app** in your home Applications folder, or `Start on Mac.command`.

Setup installs the app's Python dependencies and creates a shortcut. It is a source installer, not a signed Windows MSI or a notarised, runtime-bundled Mac installer. No administrator account or Xcode is required. Keep the downloaded app folder in place because the shortcut points to it. A managed work laptop may require your IT team's normal software-installation process.

If launching a command file is unavailable, run these from the app folder:

```powershell
# Windows
py -3 install.py
.venv\Scripts\python.exe desktop.py
```

```sh
# Mac
python3 install.py
.venv/bin/python desktop.py
```

Writing works without a tutor. Start your existing **Ollama** application, open **Settings & backups**, refresh the models and select one already installed. LM Studio is an optional alternative, not a Windows requirement. Models and tutor settings are local to each computer.

## Connect your private writing

1. Let Obsidian Sync finish downloading your vault on this computer.
2. Open **My papers → Choose Obsidian vault**. Paste the local vault path. It is the folder containing `.obsidian`, not a paper subfolder. Your Windows and Mac paths can differ.
3. Existing managed paper folders appear automatically. For another paper folder in the vault, choose **Open Obsidian paper folder** and select its path. It needs one root card with the linked argument outline and the supplied metadata format.
4. Choose **Sync saved learning** to import saved attempts and completed feedback now. While the app is running it also checks every 15 seconds. The app does not start imported tutor jobs.

The SQLite database, Python environment and local model settings stay outside the synced vault. For the portable launcher, local data is under `%LOCALAPPDATA%/AcademicWritingLab/data` on Windows or `~/Library/Application Support/AcademicWritingLab/data` on Mac. Existing installations using `start.py` keep their own configured data directory.

## Paper folder and root outline

```text
06_Academic_Writing_Lab/
  Papers/
    My research paper/
      Paper outline.md
      Cards/
        Section - I · Introduction.md
        Subsection - Motivation.md
        Argument - I-01 · Business objective and limited capacity.md
      Sources/
      Revisions/
      Recovered files/
  Projects/                 # links to papers elsewhere in this vault
  Learning/                 # saved practice and portable exercise records
```

A paper has a readable folder name. Its **root card** links to every section, subsection and argument in order. Section and subsection cards also have a purpose and a main message. Subsections are optional. Stable IDs stay in the note properties, so two similarly titled cards remain distinct. Keep the metadata when editing a card in Obsidian.

In **New paper**, enter a title and optionally an outline:

```markdown
## Section: Introduction
### Purpose
Explain why the question matters.
### Subsection: Motivation
#### Argument: The unresolved question
- What is known
- What still needs explanation
### Manuscript prose
Your existing text, if you have any.
## Section: Discussion
```

An empty or bullet-only argument is valid. Use the supplied template generator if you prefer creating the folder before opening it in the app:

```sh
python scripts/create_paper_workspace.py --output "PATH/TO/VAULT/My paper" --title "My paper" --outline "outline.md"
```

Then open that folder through **My papers → Open Obsidian paper folder**. The root outline is required; the app does not infer a paper plan from arbitrary notes.

## Write one argument

1. Read its **Purpose**, its parent section and the before/after cards.
2. Plan in **Notes and bullet points**. Write the actual paper text in **Manuscript prose**.
3. Open **My reasoning and decisions** for explanations, supervisor directions and unresolved questions. Leave **Next step** as one small action for the next session.
4. Typing saves automatically after a short pause. Wait for **Saved to your Obsidian vault** before switching computers. **Save now** flushes it immediately. The exact filename and **Open in Obsidian** link are shown.
5. **Review or ask about my text** opens a saved copy in the existing tutor workflow. Submit it for feedback or ask your own wording question. After revising and saving an attempt, choose **Save revised answer to my argument**. The app checks that the argument has not changed since that review started.
6. Download the **working manuscript** from the outline. It includes argument prose in order, with section headings. It excludes planning notes, source quotations and teaching hints.

Use the red focus clock and minimise the main menu when you need more room. The argument outline can also be collapsed. **Resume writing** on My papers returns to the last opened card in this browser.

## Import a manuscript or discussion

Choose **Import source** in a paper. Supported formats are PDF, TeX, Word, Markdown and plain text, up to 16 MB. Select one or two columns for PDFs. Enable **black text means agreed wording** only when that is the convention in your document; colour alone does not establish supervisor approval.

Choose **Find source passages**. Search all text colours or filter by colour. Read the text before and after a result. Mark it **keep**, **adapt**, **combine** or **background**, and record why it belongs in this argument. Linking adds a source note; it does not insert or rewrite manuscript prose. Several passages can support one argument, and a source can be linked to several arguments.

TeX is preserved as text. Commands and `\input`/`\include` files are not executed or loaded. PDF extraction may need checking against the original, especially equations and multi-column layouts. Scanned PDFs need OCR before import. Source search is currently lexical; it does not imply that an LLM has assessed scientific relevance.

## Recovery and two-computer work

Notes and immutable revisions are saved together in the vault. An older editor cannot silently replace a newer note. If two computers edit the same card offline, both saved branches are retained. Use **Compare & recover** to read the alternatives and deliberately choose the current text or your displayed draft. History remains available after a merge.

The app also retains displaced files in **Recovered files**, including writes through an external editor's open file handle. A crash during publication can leave a temporarily missing current note; its displaced copy remains there. Missing files or parent revisions are treated as incomplete Sync, not deletion. Do not remove old metadata or recovery files while resolving a conflict.

A local vault save does not prove delivery to the other computer. Let Obsidian finish syncing before opening the same argument on another device. Original PDFs and other attachments need to be included in your Obsidian Sync settings. Browser-only drafts cannot transfer until a vault save or saved learning attempt succeeds. Keep a separate periodic backup of the vault; synced history is not protection against every kind of deletion or device failure.

