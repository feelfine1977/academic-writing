# Write a section from an agreed outline

The simplest start is in **Papers → your paper → Edit paper outline**: add a section (or subsection), then choose **Write whole section**. The app creates a card with a unique identity. Put your agreed points in **Outline & notes**; you do not need JSON or a separate argument card for every sentence.

If talking helps you find the idea, choose **Speak my idea** beside Start writing. Record or import audio, check its local transcript and keep it as separate spoken notes. You can insert selected wording deliberately, merge clips or restore a recording from Trash. See [spoken ideas and local setup](voice-notes.md).

To create a card in Obsidian instead:

1. Copy `Section.md` into the existing paper's `Cards` folder and give the file a readable name, such as `Literature discussion.md`.
2. Replace `<unique-section-id>` with a new stable identifier, for example `my-study-literature`. Copy `<existing-paper-id>` from the paper's root card. Replace the title. For a subsection set `card_type: subsection`.
3. Add a Markdown link to the new card under `## Argument order` in the paper's root outline. Indent a subsection beneath its section. Do not change identities on existing cards.
4. Fill in purpose, agreed outline, scope, source references and unresolved questions. You may change the optional JSON steps to match your outline. A move is an idea in the argument, not a compulsory paragraph.
5. In the Lab, refresh Papers, open your paper and choose **Write whole section**.

Keep this template outside the `Papers` directory until its placeholders are filled. Do not copy a completed section with its old identity to make a new one.

## A writing session

Read one outline move, then write the connection in your own words. The scaffold is unfinished teaching material. Starting from it is optional and explicit; it never replaces existing prose. Earlier passages and quotations are references, not part of the manuscript until you deliberately reuse them.

Use **Connect** for missing reasons and undefined concepts; **Rewrite** for making the narrative coherent; **Polish** for sentence rhythm, wording and grammar. Stages are choices, not tests. Ask one concrete question of the local tutor. Read what works as well as the next priority. Keep writing while it reviews the saved snapshot.

## One manuscript source per section

The default is **argument cards**: existing card-based exports continue to work. The whole-section draft is saved separately on the section card. To use it in the paper export, explicitly select **whole section** and approve the exact draft. Its descendant argument cards remain available but are omitted from that section's export. Editing approved prose makes it a draft again.

Notes, scaffold and guidance remain outside manuscript exports. The section card and its saved versions are stored in Obsidian. Let vault sync finish before moving to another device; if changes conflict, keep both versions and compare them.

## Final polishing elsewhere

Use **ChatGPT polishing prompt** to copy the current manuscript, outline and boundaries into a prompt for a separate conversation. Inspect the prompt first. The Lab does not send it to ChatGPT. Use the response to choose your own edits; do not accept new claims, fabricated references or changes to your argument.

## Source-aware local coaching

The three tutor perspectives are narrative, argument and language. They are AI coaching perspectives, not messages from real supervisors. A section's current outline and dated meeting notes guide the response. Historical outlines and ambiguous transcript labels cannot establish new agreement. Feedback quotes the saved draft, identifies effective writing and gives at most two priorities plus one next action. Scientific support and exact quotations still require source checking.

The review runs on a saved snapshot. Continue editing while it runs; the result identifies its scope and earlier version. The tutor cannot approve a draft or silently replace text. For long sections, select a passage so the local model receives the complete passage with bounded context.

## Recover previous work

The manuscript autosaves to the section card. Browser recovery keeps unsent edits; a cross-device conflict must be compared rather than overwritten. The original argument cards remain in the paper outline. The section is also pinned in recent work so you can return after changing pages.

The private passage catalogue lives in `Section writing/Passage catalogue.json` inside its paper folder. Tag edits are kept separately from the original excerpts. Entries retain manuscript labels, locators, colour information where explicit, and evidence caveats. A quotation candidate from an earlier note is not automatically verified against its PDF. Paper data and private meeting notes are excluded from reusable app templates.

## Write, revise, then learn from a model

Use **One thing I will write now** to choose a small outcome, such as explaining one connection or developing one example. Choose 10, 25 or 45 minutes, or no timer, and click **Write this next**. This keeps the editor and your goal visible while the support panel is folded away. An existing timer is never silently replaced.

Keep developing the current draft. Autosaves preserve recovery versions; they are not new writing tasks. After making progress, open **Record progress & leave a next action**. Briefly say what changed or why a passage should stay. Choose whether it was your own attempt or contains wording applied from the tutor. Record a checkpoint and leave the next writing action. Both are stored in the paper folder for the next device. A shorter revision is still useful practice. No word quota, streak or score is awarded for accepting AI text.

Ask for feedback on a concrete question, then use **Work on one point myself** or **Keep this & continue writing**. A fresh model response can invent an optional problem; you do not need another approval to move on.

After drafting and revising, select one to three sentences, switch to **Rewrite** or **Polish**, and expand **After trying myself: show a worked version** in Tutor. The app recognises two distinct, deliberately recorded own attempts. If you already drafted and revised outside the app, confirm that explicitly instead. Request a demonstration and compare its sentence jobs and meaning with your version. Applying it is optional and reversible. Try writing the next related connection yourself. This is model guidance, not your supervisor's wording or approval.

Writing checkpoints are self-reported and are not proof of authorship or proficiency. Unchanged scaffolds and repeated autosaves do not count as attempts; model-assisted checkpoints retain their history separately. The local model can still offer poor or contradictory advice. Prioritise your current outline, the actual source evidence and your intended meaning.
