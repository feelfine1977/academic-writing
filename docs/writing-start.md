# Start writing from the outline

The outline describes what your section should accomplish. The writing brief turns the selected idea into a small task beside your own draft. It does not insert model prose or require a tutor review before you continue.

1. Choose an outline idea. Read **What the reader needs here** and the short writing actions.
2. Select **Write this idea**. Start with your own wording, or adapt an older passage that performs the same job. The draft remains your text; the guide stays separate.
3. Continue until the brief’s **Enough for now** point makes sense for your passage. This is a practical stopping cue, not a grade or word quota.
4. Read your passage with the previous sentences. Make one revision yourself if the connection is unclear, then continue to the next idea. Keep the current section rather than starting another version to escape an imperfect sentence.
5. If you are stuck, select the relevant passage and ask one question, such as “Does the reader know what this refers to?” or “Can you show a shorter version with the same claim?” A local model’s answer is advice to assess, not approval you must obtain.

Use **Rewrite for the reader** once there is prose to read together. Use **Polish the language** when the argument is understandable. You can move between stages whenever useful; they are not locked levels.

## Briefs in your Obsidian plan

In Obsidian, open your section card and find **Section writing plan**. Add an optional `writing_guide` inside each relevant step. Keep the JSON fence and the surrounding `steps` array; preserve existing step IDs so saved focus and links still work. For example, this complete small plan describes a fictional storage study:

```json
{
  "steps": [
    {
      "id": "context",
      "title": "Food preservation in context",
      "purpose": "Introduce the storage problem.",
      "writing_guide": {
        "goal": "Write the opening: what is stored and what can go wrong.",
        "write_now": [
          "Introduce the storage setting in your own words.",
          "Explain the limitation that motivates the comparison."
        ],
        "reader_needs": "The setting and the practical reason for this study.",
        "enough_for_now": "A connected start that introduces the storage problem.",
        "next": "Describe the materials that will be compared."
      }
    }
  ]
}
```

Keep paper-specific writing briefs and their provenance in the private vault. Generic app code only reads these fields. Existing plans without a brief still work: the app uses their purpose, points and neighbouring idea. Guide text is never automatically copied into manuscript prose. An idea can take several sentences or paragraphs; the number of outline boxes does not prescribe a paragraph count.

Use plain text for the guide fields and an array of strings for `write_now`. Prefer two or three concrete actions to a long checklist. State a useful stopping cue, such as “The reader can identify the comparison”, rather than demanding perfect wording or a tutor score. Keep source locators in the step's existing `provenance` field. Reopen the section in the app after Obsidian has saved and synced the change.

Choosing a new brief should not erase an existing draft, notes, or a saved writing intention. The interface can suggest a task; adopting it remains an explicit action.
