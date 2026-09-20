# Coaching from your own supervision notes

The section tutor can use a small, source-checked set of guidance kept in your paper's Obsidian folder. It reads the guidance relevant to your current writing stage and outline idea, then checks its proposed advice against the same saved passage. The aim is useful, consistent coaching that helps you continue writing. A matched source quotation or a second model check is not supervisor approval.

## Use it while writing

1. Open **Papers → your paper → Write whole section**. Choose the outline idea you are working on. Its neighbours give context; their content is not required in your current passage. If you are discussing the whole draft, leave the selection unset.
2. Write a few connected sentences and ask one concrete question. **Connect** focuses on missing relationships, **Rewrite** on the narrative, and **Polish** on wording and grammar. These are stages you choose, not tests you must pass.
3. While the review runs, keep writing. Ordinary feedback uses one local reading. You can enable **Compare the advice with another local reading**; proposed replacement wording always gets that extra comparison. When a comparison runs, the first interpretation is provisional while action items wait. Feedback refers to the saved snapshot, even if your editor has moved on.
4. Read the guidance sources and any notices. Keep passages that already do their job. “No required change” is a valid result; you do not need to keep asking until a model approves the whole section.
5. Use one justified revision, or continue with the next idea. A withheld suggestion means the app could not support that advice confidently; it does not mean your draft failed.

After drafting and revising yourself, you can select a short passage and request a **worked version** in Rewrite or Polish. The app recognises two intentional own-attempt checkpoints, or your explicit confirmation of work done outside the app. This is a learning-support choice, not a rule imposed by your supervisor. Compare the original and model wording before applying anything. The tutor must preserve claims, uncertainty, citations and open placeholders. Applying a suggestion is optional and can be undone.

## Where private guidance lives

A paper's folder contains the following files:

```text
06_Academic_Writing_Lab/Papers/<Paper title>/
  Cards/
  Section writing/
    Tutor knowledge.md
    Coaching preferences.md           # optional personal preferences
    Sources/
      Meeting notes.txt
    Reviews/
    Practice/
```

`Tutor knowledge.md` is a curated index, not the manuscript. It records a guidance point, where it applies, its current status, and a quotation supporting its interpretation. `Sources` holds the corresponding local Markdown or text files. Source paths in the index are relative to **Section writing**, such as `Sources/Meeting notes.txt`. PDF or Word files can remain alongside them, but retrieval uses their readable text extracts.

Copy `templates/section-writing/Tutor knowledge.md` into a paper's `Section writing` folder to start. Its empty index makes no claims about your supervisors. The tutor continues with the current card and general writing guidance when no valid records are available; a notice explains the limitation.

Private notes, source extracts and reviews belong in your synced vault. Keep them out of the public app repository. Sync Obsidian before switching computers. Updating the app through Git updates the general mechanism, not your private supervision records. Local Ollama settings and the chosen model must also be configured on each computer; saved reviews travel with the vault, but new model outputs can differ.

## Add a new meeting without losing earlier decisions

Uploading or copying a transcript does **not** automatically make every spoken sentence a tutor instruction. Discussions include tentative ideas, alternative routes, recognition errors and advice for earlier writing stages.

1. Preserve the original document. Add a readable `.txt` or `.md` extract under `Section writing/Sources`. Numbered paragraphs such as `P0001` make quotations easier to inspect.
2. Identify a small number of useful guidance points. For each, record an exact source quotation, its locator, and your interpretation. Separate the supervisor's words from your application of them.
3. Set the writing stages and, where appropriate, the section and outline-move IDs. Advice about a later problem statement should not become a requirement for the opening sentence.
4. Keep older records. Mark outdated advice `historical` or `superseded` and link the replacement through `supersedes`. A `qualified` record is also kept out of active retrieval until you resolve its qualifications and deliberately change its status to `active`. Do not resolve a real conflict simply by picking the newest or strictest sentence.
5. Include an example of when the guidance is **already satisfied**, plus when it should not apply. A useful tutor must recognise a completed connection as well as a missing one.
6. Recheck quotations and their surrounding context. If a recorded source hash changes, the affected guidance is excluded until rechecked. Editing guidance changes future review context; existing reviews retain their original saved context.

Keep this curation small and reviewable. A scientific claim discussed in a meeting still needs scholarly evidence. A meeting quotation proves that the words occur in the supplied record, not that the interpretation is correct or the claim is scientifically established.

## How the checks work

The retrieval layer reads the private index on demand. It checks local source paths, source changes, quotations and supplied paragraph locators. It considers stage and section/move scope, handles supersession and conflicts, and selects a bounded set of relevant excerpts. It does not send complete transcripts to the tutor by default. This is retrieval-augmented generation (RAG): the model receives selected evidence alongside the writing task.

A first local call describes what the submitted prose already covers, then proposes feedback. When requested, or when replacement wording is proposed, a second, narrower call checks proposed praise, criticisms, edits and the next action against the frozen text and guidance. It may retain or withhold items; it cannot introduce a new list of criticisms. The app also flags some wording changes involving citations, placeholders, negation and claim strength. Unsupported, uncertain or flagged edits are withheld. If a requested check cannot finish, unverified action items are withheld rather than presented as accepted recommendations. Ordinary one-reading feedback is explicitly labelled; it does not claim to have passed a second check. The optional comparison is off by default because local calibration did not justify its latency as a routine quality guarantee.

The second call uses the configured local model. It is not an independent human reviewer, and it can share the first call's mistakes. The provisional interpretation and praise can also be wrong. Word comparisons detect only some meaning changes. Your outline, source context and intended claim remain the basis for accepting advice. Reviews keep the original proposal and check record privately so a later disagreement can be examined.

For this workflow, a local file-based index is sufficient. No embedding download, vector database, external retrieval service or MCP server is required. MCP could expose the same retrieval functions to another client later; it would not itself improve the quality of judgement.

## Validation limits and a practical writing rhythm

This is experimental coaching. Local calibration found false criticism of adequate prose even when two readings agreed; a larger model also made that mistake. Source matching, response-schema validation and a completed advice comparison do not prove that a comment is academically correct. The comparison adds latency. Keep drafting while it runs, and use the recorded sources and your intended meaning to judge suggestions. Neither this review nor its agreement is required to continue or approve your own section.

Choose one connection to write for 10–25 minutes. Record your own attempt, reread what each sentence adds, and make one revision before requesting a model. Ask a specific question about that passage. Retain wording that works and leave a short next-action note before a break. These timings are adjustable work intervals, not measures of proficiency or attention.

The educational rationale is to inspect the argument actually written, as in [Harvard Writing Center's reverse-outlining guidance](https://writingcenter.fas.harvard.edu/blog/does-my-paper-flow-tips-creating-well-structured-essay). [Ollama's structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs) supports schema-constrained responses; our additional text and source checks address different concerns. [MCP's architecture](https://modelcontextprotocol.io/docs/learn/architecture) provides a way to connect tools and resources, but the choice to use direct local retrieval here is an application design decision, not an MCP quality guarantee.

## Index format: a small example

The first fenced `json` block in `Tutor knowledge.md` is the index. Use `schema_version: 1`, with `source_documents`, `requirements` and optionally `examples` arrays. Each source needs an ID and a relative text/Markdown path. Each requirement needs a unique ID, an instruction, applicable stages, scope and at least one exact supporting quotation. The loader currently bounds the index to 50 sources and 100 requirements.

The following is a **fictional format example**, not a real supervisor quotation. If trying it, create `Sources/Example coaching note.txt` containing exactly:

```text
P0001 Coach: Explain an unfamiliar label when the reader needs it to follow the argument.
```

Then use an index such as:

```json
{
  "schema_version": 1,
  "source_documents": [
    {
      "id": "example-note",
      "title": "Fictional coaching note for a format test",
      "path": "Sources/Example coaching note.txt"
    }
  ],
  "requirements": [
    {
      "id": "EXAMPLE-01",
      "title": "Explain a label when it matters",
      "instruction": "If an unfamiliar label prevents the reader from following the current passage, ask for a brief explanation. Keep an explanation that already works.",
      "stage": ["connect", "rewrite"],
      "scope": {"section_id": "any", "moves": []},
      "status": "active",
      "kind": "coaching",
      "strength": "explicit",
      "evidence": [
        {
          "source_id": "example-note",
          "paragraphs": ["P0001"],
          "quote": "Explain an unfamiliar label when the reader needs it to follow the argument.",
          "interpretation": "Explain only what the present reader needs, not every possible term."
        }
      ],
      "not_applicable_when": ["The intended reader already knows the term or the passage already explains it."],
      "positive_example": "A short explanation immediately after the new label can be sufficient.",
      "counterexample": "Require an unrelated textbook definition in every paragraph.",
      "supersedes": [],
      "conflicts_with": [],
      "tags": ["terminology", "definition", "reader"]
    }
  ],
  "examples": []
}
```

For real records, use meaningful dates and locators. A `sha256` on the source can pin the reviewed text; recheck the source and interpretation before updating that hash. To restrict guidance, replace `any` with the existing section card's stable ID and add move IDs from its section writing plan. Do not change existing card identities or invent a source quotation to satisfy the format.
