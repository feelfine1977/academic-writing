# Academic Writing Lab

A local writing and English-practice workspace for Mac and Windows, with readable paper cards in Obsidian and an optional Ollama tutor.

## Install

Install Python 3.12 or newer. Download this repository into a permanent folder and run **Install on Windows.cmd** or **Install on Mac.command**. Setup installs dependencies and creates a shortcut. It is a source installer; signed binary installers are not included. Open the shortcut, choose your Obsidian vault in **My papers**, and let Sync finish before changing computers.

Windows can use an existing Ollama installation. Select an installed model in **Settings & backups**. Writing and saved practice work without a model.

[Full installation and writing guide](docs/portable-user-guide.md)

[How to push this app to GitHub](docs/publishing.md)

## Paper workflow

Create or open a folder named after your paper. A root outline links to section, subsection and argument cards. Plan with bullets, keep reasoning separately, and write prose in the argument editor. Import PDF or TeX as original sources, search their passages and map them to the plan. A saved card can be reviewed with the local tutor.

The app writes notes and immutable revisions to your selected vault. Saved attempts and completed feedback are exchanged as Markdown records; a live SQLite database is never synced. Conflicting argument edits remain available for comparison. The application cannot verify remote Obsidian Sync delivery.

## Included and private data

This source distribution includes the reusable application, templates and 120 general English exercises. Private manuscripts, WISE research cards, supervisor discussions, local preferences, backups and prior Git history are excluded. Your existing private paper folders and saved learning travel through your vault.

## Development

Run tests with `python -m pytest` from the installed environment. The portable launcher is `desktop.py`; `start.py --port 8765` runs a local server directly. The server binds to loopback only. Python environments are created separately on each computer.
