# Reading notes and the Papyr planner

## Read and write in your own words

Open **Reading & notes → New reading document**. Choose a paper summary, book overview or other academic note. The starting templates use the Literature, Reading, Paper and Source cards in your selected Obsidian vault when available; built-in headings work in a new vault too.

You can also search **Start from an existing Obsidian literature card**. This creates a separate reading document. The original source card stays intact; its earlier notes appear as reference material, and your summary starts empty.

1. Set a reading objective under **Reading objective and working notes**.
2. Write **My summary · my own words**.
3. Use **Add quotation** for exact source wording, a page/location, context and your separate interpretation. Check wording against the source yourself.
4. Ask a specific question under **Tips on my summary**. The local tutor reads the saved summary and supplied quotation notebook. It does not open or verify the whole paper. Without excerpts, it can advise on writing but cannot verify fidelity to the source.
5. Keep writing while feedback runs. The review shows its saved text and tells you when your summary has changed. **Continue your work** returns you to the note.

For a book, create a **Book overview**, then **Add a chapter** for each chapter you want to work on. Each chapter has its own document, summary, quotation notebook and tutor feedback. The book overview links to them and is available for your whole-book synthesis.

Notes autosave after a short pause. **Save now** records them immediately. They live in:

```text
06_Academic_Writing_Lab/Reading/Readable title/
  Reading note.md        (a paper or other note)
  Book overview.md       (a book)
  Chapters/01 - Chapter title.md
  Revisions/
  Recovered files/
  Feedback/
```

The folder contains either a reading note or a book overview. Book chapters are separate Markdown files. Revisions and completed tutor feedback travel with the folder through Obsidian Sync. Wait for Sync to finish before switching computers. If two edits compete, the app retains both versions for comparison. A running review and an unsaved browser recovery draft stay on the originating computer.

Native iPad version 1.2.0 includes **Reading & notes** and **Planner**. Choose the root of the same Obsidian vault, then let Sync finish. The iPad creates and edits the same Markdown documents and revision histories. Use **Save & send tutor request**, open Obsidian to sync, and keep Writing Lab 0.19.1 or later running on the Mac. Feedback returns through the vault; use **Refresh feedback after Sync** on the iPad. Requests refer to the saved summary; if it changes before the Mac receives the request, send a new one. Local recovery drafts stay on the device until successfully saved to the vault. Existing-card import and conflict comparison remain Mac tools.

## Send a writing task to Papyr

Click **Send to planner** in Writing Lab's top bar, or beside a reading note. In focus mode, use **Timer options / Notes & finish → Send this task to planner**. Tutor feedback in Reading & notes also has **Plan this next step**.

1. Write one concrete action, such as “Check the evidence for my summary of chapter 3”.
2. Choose the date and, optionally, the number of Pomodoro sessions you expect to need.
3. Click **Add task to Obsidian**.

The task is added under **Tasks** in `Papyr/Planner/YYYY-MM-DD.md`, using your existing daily planning template when creating a new day. Other tasks, appointments and notes are retained. The task includes a Writing Lab return link and, where available, a link to the source note.

```markdown
- [ ] Check the evidence for chapter 3 [pomodoros:: 2] <!-- papyr-task:stable-uuid -->
```

The identifier above illustrates the format; the app supplies a valid UUID. Preserve it when moving the task to another planner date or period. Remove it if you copy the line to create a different task. The estimate is planned work, not a record of completed focus time.

Then use the existing Papyr integration in Obsidian on your Mac:

- **Papyr USB: Sync daily planner to Papyr (USB)**, or
- the existing **Wi-Fi sync** command.

Saving in Writing Lab does **not** perform device sync. When adding a task on Windows, let Obsidian Sync deliver the note to the Mac, then run Papyr sync there. Task completion and device focus records remain managed by the existing Papyr integration. The Writing Lab does not change its software or device settings.

For an existing daily note, the exact previous file is retained under `06_Academic_Writing_Lab/Planner backups/`. A demo day is rejected so real tasks do not become demo entries: choose another day or deliberately change `demo: true` to `demo: false` in Obsidian first.
