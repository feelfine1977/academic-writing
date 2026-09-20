# Windows setup: from GitHub to your writing

Use this checklist after the current application has been pushed to GitHub. You will install the app once, connect the Obsidian vault already on your Windows computer, and use its saved paper work.

```text
Application:  public GitHub repository → local app folder on Windows
Your work:    Mac Obsidian vault ↔ Obsidian Sync ↔ Windows Obsidian vault
Local tutor:  Ollama and its models installed on each computer
```

Your vault and app folder have different jobs. Keep the app outside Obsidian and outside a second synchronisation service such as OneDrive. Keep using Obsidian Sync for the vault.

## 1. Confirm the published app

- [ ] Open the repository on GitHub. Its README should link to this Windows guide, and the file list should include `Install on Windows.cmd`, `Update on Windows.cmd` and `Set up voice on Windows.cmd`.
- [ ] Open the repository's **Actions** tab and the latest **Portable application checks** run. Both the Windows and macOS jobs should pass before you use that revision. A pending or red run is not a successful Windows check. [How to inspect a run](https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history).

## 2. Prepare the Windows computer

- [ ] Install **GitHub Desktop** from [desktop.github.com](https://desktop.github.com/) and sign in.
- [ ] Install a **64-bit Python 3.12 or newer** from [python.org](https://www.python.org/downloads/windows/). Include the Python launcher. The dependency set is checked with Python 3.12 on Windows x64. Open a new Terminal and run `py -3 --version`; it should report 3.12 or higher. [Python's Windows instructions](https://docs.python.org/3.12/using/windows.html).
- [ ] Open Obsidian and allow your existing vault to finish syncing. Do not create an empty replacement for a vault you already use.
- [ ] Open the Ollama application already installed on this computer. Writing works without it; tutor feedback needs a locally available model.

The installer is per-user. A managed work laptop can still restrict Python, scripts or local models; use your organisation's normal installation process if a tool is blocked.

## 3. Clone and install

1. In GitHub Desktop, use **File → Clone repository → URL**, and paste the address of your app repository.
2. Choose a short, permanent folder outside the vault, for example `C:\Users\YourName\Apps\academic-writing`. Confirm the clone. A Git clone supports updates; a downloaded ZIP does not. [GitHub's cloning instructions](https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop).
3. Open this folder in File Explorer. Double-click **Install on Windows.cmd**.
4. Leave the setup window open until it reports **Installed**. The first run downloads Python dependencies. A red error or “Setup could not finish” means installation has not completed.
5. Double-click the new **Writing Lab** Desktop shortcut. Alternatively, run **Start on Windows.cmd** in the app folder.

**Checkpoint:** a local browser page opens with Learning, Papers, Reading & notes and Fiction workshop. The usual address starts with `http://127.0.0.1:8765`; another nearby port can be selected if necessary. You do not need a public website, Docker, Xcode or LM Studio.

If the shortcut does not open, start from Terminal in the app folder to see the error:

```powershell
.\.venv\Scripts\python.exe -X utf8 desktop.py
```

## 4. Connect the existing Obsidian vault

1. In Obsidian, confirm that the paper's **Paper outline** and latest section draft are present.
2. In Writing Lab, open **Papers → Choose Obsidian vault**.
3. Enter this computer's local vault path. For a new vault location, prefer a short path such as `C:\Vault\PhD`: deeply nested cards can otherwise exceed Windows path limits. Select the folder containing `.obsidian`, not `Papers` or a single paper folder. The Mac path is not valid on Windows.
4. Your managed papers should appear. Open the existing paper; do not create a second paper just because the list is still waiting for sync.
5. Expand **Vault & sync settings** and choose **Sync saved learning**. Saved attempts, completion records and completed feedback are imported into this computer's local database. The app also checks periodically while running.

In **Obsidian Settings → Sync**, enable the attachment types used by your work, including images, PDFs and audio, plus **Sync all other types** for JSON, TeX, bibliography and other supporting files. Check excluded folders on both computers. The app's accepted upload size can exceed your Obsidian plan's per-file limit; an oversized attachment saved locally may not reach the other computer. [Selective sync settings](https://obsidian.md/help/sync/settings), [file-size limits](https://obsidian.md/help/sync/plans).

**Checkpoint:** the same paper outline, section prose, notes and earlier versions open. No database file needs to be copied into the vault. If an attachment is missing, check Obsidian's sync log before changing or deleting anything.

A link to another computer's Downloads or Zotero folder does not transfer that PDF. Imported passage text may be available even when the original file is absent. Keep PDFs you need on both computers inside the vault. For registered lesson readings, the app supports vault-relative catalogue paths or a private **Reading attachments.md** map; see [portable reading links](portable-sync.md#portable-reading-links). Do not rewrite immutable source imports or revision files merely to change a path.

## 5. Select Ollama on Windows

1. Open Writing Lab **Settings** and select **Ollama** as the tutor provider.
2. Refresh the model list and choose a model already installed on this Windows computer.
3. Save the setting and try a short tutor question on a saved passage.

If the list is empty, run `ollama list` in Terminal. If it shows no models, install the model you want through Ollama. Model files and settings do not travel through Obsidian. Ollama's Windows app exposes its local API on port 11434. [Official Windows guide](https://docs.ollama.com/windows).

## 6. Optional: spoken ideas

Run **Set up voice on Windows.cmd** once after installing the main app. It installs or locates FFmpeg, whisper.cpp and the separate speech model locally. Then open a paper's Section writing screen, choose **Speak my idea**, and check **Local transcription setup**.

**Checkpoint:** transcription reports ready. Record a short test only when you choose to grant the browser microphone access. Audio and corrected notes are saved in the selected paper's vault folder; they are separate from your manuscript. See the [voice guide](voice-notes.md) for imports, merging, Trash and supported platforms. The automated voice package is for Windows x64; other architectures need compatible local speech executables.

## 7. Verify the handover once

- [ ] On the Mac, save a harmless next-action note in your existing paper and wait for the app's saved indicator.
- [ ] Let Obsidian finish syncing on the Mac, then on Windows.
- [ ] Open that same paper/card on Windows and check the note and the latest prose.
- [ ] Make one small note change on Windows, save it, let both vaults sync and verify it on the Mac.
- [ ] Open one saved exercise and one audio/source attachment you expect to use.

This checks your actual vault connection and remote sync. Automated app tests cannot confirm that your Obsidian account has delivered every file.

## 8. Everyday use and updates

Before switching computers: save your writing and spoken notes, save any exercise attempt, leave a next action, and let Obsidian Sync finish. Then let the second computer sync before opening that work. Work on the same section on one computer at a time where possible; if two edits conflict, compare both saved versions.

For an app update, save and sync first. Closing the browser does not stop the background server. The simplest way to stop it is to restart Windows, then update **before** opening Writing Lab.

- **GitHub Desktop route:** select the app repository, fetch and pull the published update, then run **Install on Windows.cmd** again to refresh dependencies. Reopen the shortcut after setup succeeds.
- **Command-file route:** run **Update on Windows.cmd**. It locates Git on your PATH, in GitHub Desktop or in standard Git for Windows locations, refuses a dirty checkout or a running app, pulls without rewriting history, then installs dependencies. If Git is unavailable, use the Desktop route or install [Git for Windows](https://gitforwindows.org/).

Updating the application does not upload your writing. Use the same application revision on both computers. If your Mac already runs a development installation, keep that installation and its current launcher; do not install a second portable app over it just to obtain Windows support.

## When something is missing

| What you see | Next action |
|---|---|
| Python launcher unavailable | Repair the Python installation to include its launcher, or run `python -X utf8 install.py` from Terminal after verifying that Python is 3.12+. |
| No paper or an incomplete outline | Let Obsidian finish; check the selected local vault and folder exclusions; choose Refresh papers. |
| Long-path or invalid-name error | Keep app/vault paths short. Your IT administrator may need to enable Windows long-path support. Do not rename linked cards blindly. |
| No tutor models | Start Ollama, run `ollama list`, then refresh the app's model list. |
| Audio unavailable on the other computer | Check audio/other-file sync settings and file-size limits; model files themselves remain local. |
| Update says there are local changes | Review those source edits in GitHub Desktop. Do not discard them merely to update. |
| Update says the app is running | Restart, then update before launching the app. |
| Saved text differs between computers | Wait for both syncs, then compare revisions in the paper rather than overwriting one version. |

Portable local data lives at `%LOCALAPPDATA%\AcademicWritingLab\data`; the server log is in its `runtime\server.log`. Paper writing belongs to your vault. Neither location should be committed to GitHub.

## What has been verified

The public source is tested with isolated vaults and local databases, including changes between two copies, saved learning, conflict handling and voice-note metadata. Windows x64 dependency wheels for Python 3.12 resolve from PyPI. GitHub Actions is configured to run the suite on actual Windows and macOS runners after publication. A physical Windows desktop, microphone, your Ollama hardware and your Obsidian account still need the checkpoints above.
