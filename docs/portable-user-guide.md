# Writing Lab on Mac and Windows

## Start the app

Clone the repository into a permanent folder for easy updates. Install Python 3.12 or newer first. On Windows, enable the Python launcher when installing Python. Follow the [Windows checklist](windows-setup.md) for the complete GitHub, Obsidian and Ollama setup.

- **Windows:** double-click `Install on Windows.cmd` once. Then use the **Writing Lab** shortcut on your Desktop, or `Start on Windows.cmd`.
- **Mac:** double-click `Install on Mac.command` once. Then open **Writing Lab Portable.app** in your home Applications folder, or `Start on Mac.command`.

Setup installs the app's Python dependencies and creates a shortcut. It is a source installer, not a signed Windows MSI or a notarised, runtime-bundled Mac installer. No administrator account or Xcode is required. Keep the downloaded app folder in place because the shortcut points to it. A managed work laptop may require your IT team's normal software-installation process.

If launching a command file is unavailable, run these from the app folder:

```powershell
# Windows
py -3 -X utf8 install.py
.venv\Scripts\python.exe -X utf8 desktop.py
```

```sh
# Mac
python3 install.py
.venv/bin/python desktop.py
```

Writing works without a tutor. Start your existing **Ollama** application, open **Settings → Tutor & backups**, refresh the models and select one already installed. LM Studio is an optional alternative, not a Windows requirement. Models and tutor settings are local to each computer.

For updates and switching computers, follow [One writing workspace on Mac and Windows](portable-sync.md). **Update on Windows.cmd** or **Update on Mac.command** pulls a clean Git clone and refreshes dependencies. Save and sync, restart the computer, then run Update before opening the app so the old background server cannot stay active.

## Find your work

The main menu has four work areas:

- **Learning:** use **Overview** to continue, **Courses** for a guided sequence, **Practice** for individual skills, **Saved answers** to revisit your attempts and feedback, **Progress** for history, and **Resources** for the phrasebook and research notes.
- **Papers:** find each paper represented in your Obsidian vault. Open its outline or choose **Resume writing** to return to an argument. Notes, reasoning, source mappings and manuscript prose belong to that paper.
- **Reading & notes:** write paper summaries, keep quotations and create separate chapter notes for books, with local tutor feedback on your own summaries.
- **Fiction workshop:** plan and develop creative writing separately from academic papers.

**Settings** contains the local tutor, backups and **Obsidian & devices**. **Help** contains the guide and your saved questions or comments. Minimise the main menu for more writing space. An idle focus timer appears inside a writing or exercise task; a running timer stays visible when you leave it.

Saved answers are practice records. Your paper text lives in **Papers**. A review opened from a paper uses a saved practice copy; return a revision with **Save revised answer to my argument**.

## Continue after a structural revision

A revised set of argument cards can become a new working outline inside the same paper. The paper keeps its identity and earlier writing. A revision labelled **proposal** does not record supervisor approval.

Open **Papers → your paper** to see the current outline. Open an argument and read its **Main message** and **Your next writing task**. Expand **Use earlier text** to inspect mapped previous arguments. Keep plans and questions in **Notes and bullet points**, and write your document in **Manuscript prose**. Existing source wording is never inserted automatically into an empty argument.

Use **Earlier outlines** to read the structure and text saved before an import. **Earlier / unplaced cards** also keeps previous card links usable. These app views are read only; the current manuscript export follows the active outline. **Revision guidance & sources** opens the imported vocabulary, coverage and mapping notes in Obsidian. Old exercise feedback stays attached to the old exercise; reviews opened from a new argument use its current purpose and scope.

For a prepared card ZIP, stop the app and preview the import from the repository folder:

```sh
python scripts/import_paper_revision.py --vault "PATH/TO/VAULT" --data-dir "PATH/TO/LOCAL/APP/DATA" --paper-id "EXISTING-PAPER-ID" --archive "revision-cards.zip" --label "September revision proposal"
```

Use the Python executable in your app's `.venv`. Add `--apply` to import after checking the preview, then restart the app. The ZIP needs one root `Paper_outline.md` or `Paper outline.md`, unique new card IDs, the existing paper ID and relative links to its cards and resources. An ordinary paper PDF belongs in **Import source** instead. Reimporting the identical completed package does not reset later writing.

The vault stores a linked snapshot in **Outline versions**, the original package and its guides in **Revision materials**, and the new working cards in **Cards**. Let Obsidian Sync finish before changing computers. A snapshot that has not finished syncing cannot be opened until all its files arrive.

## Connect your private writing

1. Let Obsidian Sync finish downloading your vault on this computer.
2. Open **Papers → Choose Obsidian vault**. Paste the local vault path. It is the folder containing `.obsidian`, not a paper subfolder. Your Windows and Mac paths can differ.
3. Existing managed paper folders appear automatically. For another paper folder in the vault, choose **Open Obsidian paper folder** and select its path. It needs one root card with the linked argument outline and the supplied metadata format.
4. Expand **Vault & sync settings** below the paper-list buttons, then choose **Sync saved learning** to import saved attempts and completed feedback now. While the app is running it also checks every 15 seconds. The app does not start imported tutor jobs.

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

Then open that folder through **Papers → Open Obsidian paper folder**. The root outline is required; the app does not infer a paper plan from arbitrary notes.

## Write one argument

1. Read its **Purpose**, its parent section and the before/after cards.
2. Plan in **Notes and bullet points**. Write the actual paper text in **Manuscript prose**.
3. Open **My reasoning and decisions** for explanations, supervisor directions and unresolved questions. Leave **Next step** as one small action for the next session.
4. Typing saves automatically after a short pause. Wait for **Saved to your Obsidian vault** before switching computers. **Save now** flushes it immediately. The exact filename and **Open in Obsidian** link are shown.
5. **Review or ask about my text** opens a saved copy in the existing tutor workflow. Submit it for feedback or ask your own wording question. After revising and saving an attempt, choose **Save revised answer to my argument**. The app checks that the argument has not changed since that review started.
6. Download the **working manuscript** from the outline. It includes argument prose in order, with section headings. It excludes planning notes, source quotations and teaching hints.

Use the red focus clock and minimise the main menu when you need more room. The argument outline can also be collapsed. **Resume writing** on Papers returns to the last opened card in this browser.

## Import a manuscript or discussion

Choose **Import source** in a paper. Supported formats are PDF, TeX, Word, Markdown and plain text, up to 16 MB. Select one or two columns for PDFs. Enable **black text means agreed wording** only when that is the convention in your document; colour alone does not establish supervisor approval.

Choose **Find source passages**. Search all text colours or filter by colour. Read the text before and after a result. Mark it **keep**, **adapt**, **combine** or **background**, and record why it belongs in this argument. Linking adds a source note; it does not insert or rewrite manuscript prose. Several passages can support one argument, and a source can be linked to several arguments.

TeX is preserved as text. Commands and `\input`/`\include` files are not executed or loaded. PDF extraction may need checking against the original, especially equations and multi-column layouts. Scanned PDFs need OCR before import. Source search is currently lexical; it does not imply that an LLM has assessed scientific relevance.

## Recovery and two-computer work

Notes and immutable revisions are saved together in the vault. An older editor cannot silently replace a newer note. If two computers edit the same card offline, both saved branches are retained. Use **Compare & recover** to read the alternatives and deliberately choose the current text or your displayed draft. History remains available after a merge.

The app also retains displaced files in **Recovered files**, including writes through an external editor's open file handle. A crash during publication can leave a temporarily missing current note; its displaced copy remains there. Missing files or parent revisions are treated as incomplete Sync, not deletion. Do not remove old metadata or recovery files while resolving a conflict.

A local vault save does not prove delivery to the other computer. Let Obsidian finish syncing before opening the same argument on another device. Original PDFs and other attachments need to be included in your Obsidian Sync settings. Browser-only drafts cannot transfer until a vault save or saved learning attempt succeeds. Keep a separate periodic backup of the vault; synced history is not protection against every kind of deletion or device failure.

