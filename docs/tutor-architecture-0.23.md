# Tutor architecture: smaller, explicit jobs

20 September 2026. This design was reviewed from independent AI perspectives on local-model orchestration, academic argument, and writing practice. No human supervisor or external expert was contacted. The design is a candidate to evaluate, not a claim of reliable academic judgement.

## Start writing without waiting for a model

The section outline and its writing guide supply the current argument's purpose, what to draft now, a reasonable stopping point, and the next idea. The author works in one continuing draft. Asking an AI to approve the current paragraph is optional. Writing guides and private decisions live with the paper in Obsidian; generic application code stays in the public package.

The tutor request has an explicit intent:

- **Discuss my question:** answer the question about the submitted text.
- **Check this connection:** examine that connection; do not turn the whole outline into a paragraph checklist.
- **Help me continue:** propose one next writing action. The response schema and server reject diagnostic priorities in this mode.
- **Requested selected edit:** use a separate editing operation described below.

Selecting an outline idea or seeing the next idea does not require including every associated point in the current passage. App-side writing guides are excluded from the model's selected-idea packet. Retrieval queries use the author's question and actual writing; they no longer append all of the selected move's future points.

## Separate editing from criticism

Previously, a request to shorten a sentence could ask one small model for coverage analysis, strengths, criticism, a next task and an edited sentence in the same response. This creates opportunities to manufacture a problem in order to fill the response.

The selected-edit route now receives only the exact selection, nearby prose, the author's question, writing intention and meaning boundaries. It returns one of three results:

1. **Edit:** one replacement of the selected passage, with a brief explanation of the editing operation.
2. **Keep:** the unchanged selection, because a change is not needed for the request.
3. **Clarify:** one unresolved meaning question, with no proposed replacement.

It cannot return diagnostic priorities, praise, an expanded outline or a new writing assignment. It may shorten syntax or split a sentence, but it may not invent a fact, strengthen a claim or replace a technical distinction with a more fluent alternative. A model passage remains short and optional; the existing deliberate-practice requirement for worked demonstrations remains.

An additional local reading compares requested edits using the same compact context. This is a fallible comparison, not a semantic certificate. Mechanical checks independently withhold edits with identifiable changes to citations, placeholders, numbers, uppercase abbreviations, negation and some modality or epistemic distinctions. These checks also catch removal of a weak modal such as “can” and the difference between “alone” and “single”. Passing them does not establish that every meaning is preserved.

After the first candidate's fresh evaluation still found meaning-changing edits, a separately versioned development candidate adds **one bounded repair**. Mechanical text checks run before the additional model comparison. When they identify a concrete contract violation, the editor receives the rejected wording, the observed flags and exact original spans to preserve, and starts again from the original passage. The repair is checked once; a persistent violation is withheld without a comparison call or another repair. A semantic disagreement from the model checker never triggers this loop, nor does ordinary critique. The first response, rejected proposal, flags, repair input/output and provenance remain in the private review trace. This extension was developed after known failures and must not be described as passing an untouched evaluation set. It may add one local call and still fail to provide a useful alternative.

## Evidence for a criticism

An ordinary review may contain at most one priority. Before giving it, the model must quote the strongest existing wording that could already answer the question and explain the specific remaining reading difficulty. This counterevidence is checked against the actual submitted passage. A missing or fabricated counterquotation causes the proposed action to be withheld. Coverage must also say that the point needs work now; deferred outline content cannot support a current deficiency.

This structure makes a criticism inspectable. It does **not** make the model's explanation true. The model may misread a perfectly adequate connection, misapply a real source quotation, or invent a plausible reason. Sources and a second reading do not eliminate these failure modes. The author can keep the passage and continue.

## Why this design rather than a larger voting panel

Recent primary work supports testing narrow tasks and careful orchestration, but it does not demonstrate supervisor-equivalent writing feedback:

- [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153), revised September 2025, argues for specialised small-model calls and heterogeneous systems where broader ability is needed. It is a position paper, not a benchmark showing that a local model can judge this author's introduction.
- [Can Small Agents Collaborate to Beat a Single Large Language Model?](https://arxiv.org/abs/2601.11327), revised April 2026, evaluates restricted agent collaboration on tool-intensive tasks. Orchestrator reasoning mattered more than enabling reasoning everywhere. This motivates bounded orchestration; it does not justify adding multiple academic personas to the same weak model and counting their agreement.
- [On the self-verification limitations of large language models on reasoning and planning tasks](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f3c5e56274140e0420baa3916c529210-Abstract-Conference.html), ICLR 2025, finds substantial weaknesses in self-critique on formal tasks and benefits from sound external verification. Here, exact text and structural checks provide limited external checks; academic interpretation has no equivalent complete verifier.
- [Correlated Errors in Large Language Models](https://proceedings.mlr.press/v267/kim25e.html), ICML 2025, finds correlated errors across models. Therefore, even cross-model agreement is not independent evidence of correctness.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), September 2025, recommends concise, relevant context and clear tool contracts. The local edit route applies that engineering principle rather than inserting the full paper plan into every wording request.
- [Agentic Context Engineering](https://arxiv.org/abs/2510.04618), ICLR 2026, studies structured context curation rather than repeatedly replacing a growing playbook with compressed summaries. The app keeps source records and their provenance separate from bounded retrieval. It does not automatically rewrite supervision guidance from model-generated feedback.

These are design influences and limited-domain findings. Their transfer to writing coaching is an engineering hypothesis that needs direct tests. No additional MCP server or vector database is introduced: the current local file retrieval already provides the required source access, and a protocol would not itself repair judgement errors.

## Evaluate the actual workflow

Maintain a frozen set of clear and flawed passages, narrow questions, requested edits and conflicting instructions. Record original inputs, selected sources, actual compact packets, raw outputs, withheld proposals, final displayed advice, model identity and latency. Separate a successful edit from a failed edit that was safely withheld. A valid JSON response is not a successful writing judgement.

The independent retest compares the previous release with this candidate on fresh cases. Freeze the candidate before inspecting its outputs. Do not repeatedly tune the same few sentences until they receive favourable reviews. Test false criticism of adequate prose as carefully as missed errors in weak prose. This follows the distinction between a trial's transcript and its actual outcome discussed in [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), January 2026.

Software tests cover persistence, provider contracts, exact quotations, intent routing, editing bounds, guards and cache separation. They cannot establish agreement with a supervisor. Private drafts, meeting records, tutor knowledge and evaluation traces remain in private storage and Obsidian; general schemas, synthetic tests and this document can be public.

## Observed release limits

The local development evaluation used 16 requests across the previous release and two candidates on the installed 8B model. Its records remain private with the paper. Narrower editing reduced latency in the two initial edit comparisons, but both first-candidate edits were withheld rather than successfully delivered. The repair follow-up produced two substantially useful edits and two mixed outcomes; one restored an altered epistemic limitation, while another lost an explicit pilot-study qualification despite model-checker approval. These few qualitative trials do not establish an accuracy rate or supervisor-equivalent judgement.

The interface therefore leaves drafting independent of approval, treats the rewrite as optional, preserves the original text, and records rejected proposals. Exact text guards catch particular changes; they cannot establish full semantic equivalence. Expanding the same model into more named reviewers would not address the observed shared errors.
