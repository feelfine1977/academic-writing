# One writing workspace on Mac and Windows

GitHub delivers the application. Obsidian Sync delivers your writing. Keep the two folders separate: never clone the app into your vault and never publish your private development repository.

Use the [guided Windows setup](windows-setup.md) for installation checkpoints, Ollama, attachments and your first handover test. Use the [publishing guide](publishing.md) to upload a prepared public update yourself.

## First setup on the other computer

1. Install Obsidian and let the complete vault finish syncing, including PDF, JSON, SVG, Canvas and other attachments used by your papers. Do not exclude `06_Academic_Writing_Lab`.
2. Clone the public app repository into a permanent folder with GitHub Desktop or `git clone YOUR-REPOSITORY-URL`. A clone supports later updates; a downloaded ZIP does not contain Git history.
3. Install Python 3.12 or newer, then run **Install on Windows.cmd** or **Install on Mac.command**. Open the Windows **Writing Lab** shortcut or Mac **Writing Lab Portable.app**.
4. In **Papers**, select this computer's vault folder. The path may differ between Mac and Windows. Paper identities and links use metadata and relative vault paths.
5. Expand **Vault & sync settings** and choose **Sync saved learning**. The app also checks every 15 seconds. This imports saved attempts, completions, exercise context and writer questions; it does not start another device's unfinished model jobs.
6. Start Ollama on this computer. In Settings choose **Ollama**, refresh models and select a model installed here. The app does not require LM Studio. Model files, runtime settings and permissions are local to each device.

## What travels where

| Material | Location | How it travels |
|---|---|---|
| App, general coaching rules, exercises and blank templates | Public app repository | Git pull |
| Outline, section/argument drafts, notes, reasoning, revisions and approval state | Paper folder in the vault | Obsidian Sync |
| Section plans, dated supervisor guidance, outline images and source catalogue | Section cards and `Section writing` in the paper folder | Obsidian Sync |
| Writing intentions, restart notes and intentional checkpoints | Section cards and `Section writing/Practice` | Obsidian Sync |
| Section tutor requests and completed feedback | `Section writing/Reviews` in the paper folder | Obsidian Sync |
| Spoken notes, original audio and transcription history | `Section writing/Voice notes` in the paper folder | Obsidian Sync, with audio and JSON attachments enabled |
| Earlier private lesson catalogues and paper-specific checks | `06_Academic_Writing_Lab/Private library` | Obsidian Sync |
| Saved exercise attempts, completion reviews, feedback and writer questions | `06_Academic_Writing_Lab/Learning` | Obsidian Sync; the app restores a local index |
| Reading summaries, chapter notes and their feedback | Reading folders in the vault | Obsidian Sync |
| Database, Python environment, vault path and Ollama settings | Each computer's local app data | Rebuilt/configured locally; never sync the live database |
| Unsaved browser recovery, currently open view and a running timer | That browser | Local only |

Paper-specific guidance belongs in the section's **Supervisor comments and editing consequences**, **Academic reviewer guidance**, **Outline provenance** and outline fields. General prompt code interprets those fields; a named supervisor or private research claim need not be hardcoded in the app. A proposal is not supervisor approval.

## Portable reading links

Saved summaries and extracted passages can travel even when an original PDF remains outside the vault. A link into another computer's Downloads or Zotero directory does not make that file available on Windows.

Put a private copy of a required reading inside the vault, for example `06_Academic_Writing_Lab/Readings/Academic Phrasebank.pdf`. For registered lesson/outline readings, use vault-relative paths in the private catalogue, or add **`06_Academic_Writing_Lab/Private library/Reading attachments.md`** with one JSON block:

````markdown
# Reading attachments

```json
{
  "version": 1,
  "readings": {
    "PHRASEBANK": "06_Academic_Writing_Lab/Readings/Academic Phrasebank.pdf"
  }
}
```
````

Use the reading ID already registered in your private library. This map changes where the app opens that reading without altering original source metadata. It takes precedence over older absolute paths. If its file has not synced, the app reports it as unavailable instead of silently opening an older local copy. Both slash styles are accepted, and paths must stay inside the vault. Normal links in editable Obsidian notes should likewise point to vault attachments; the reading map does not rewrite arbitrary historical links.

## Change computers without losing your place

Save the section or argument and wait for **Saved to your Obsidian vault**. Leave one short next action in your notes. Save exercise answers as attempts; text that exists only in browser recovery does not travel. Give the app's learning archive a sync cycle or click **Sync saved learning**. Let Obsidian finish syncing before closing the first device.

On the second computer, let Obsidian finish first, then open the same paper and section. The manuscript, outline, attached guidance and completed reviews should match. **Previous writing question** and the saved-question list recover coaching for the same exercise or argument, even in a new browser. Two devices can produce different new model feedback: the same model name does not guarantee identical runtime, model weights or stochastic output.

If the same note was edited on both computers, use the comparison view. Both revisions are retained. Wait if files are still arriving; an incomplete sync is not a request to delete a note. A local save confirms a file on this device, not remote delivery. Keep periodic independent vault backups.

## Update the app

Save and sync your writing. The app runs a background server even after its browser window is closed. For the simplest safe update, restart the computer, then run **Update on Windows.cmd** or **Update on Mac.command before opening Writing Lab**. The updater checks for a clean Git clone, refuses to overwrite local changes, performs `git pull --ff-only`, and refreshes dependencies. It never pushes or changes your vault.

If the updater reports a running server, no application files were changed. Restart and retry before opening the shortcut. A dependency installation failure leaves the source update in place; rerun the installer before starting. Use the same app revision on both computers. Do not copy a `.venv` between operating systems.

The prepared public release is a new source folder with no private Git history. Publishing it is a separate author action described in [the publishing guide](publishing.md).

## Validation boundary

Cross-device transfer is tested with two isolated databases and vault copies, including saved questions, terminal feedback and conflict handling. The source updater is tested against local Git repositories. The public repository includes a Windows/macOS workflow that also tests a fresh server, Unicode paths, copied-vault reopening and a Windows shortcut. Check its results after publishing: configuring a workflow does not mean it has passed. Your Windows laptop, Ollama performance and actual Obsidian delivery still need the handover checklist. The application cannot check whether Obsidian's remote service has delivered every attachment.
