# Write a paper in Obsidian

This folder contains blank writing templates. No LLM or generated manuscript is involved.

1. Put the whole folder inside `06_Academic_Writing_Lab/Papers/` in your connected vault. Give the folder your paper's name.
2. Open `root.md`. Write the title, question and contribution in your own words.
3. Open the files linked under **Argument order**. Write planning notes under **Notes and bullet points**, quotations and page numbers under **Source mapping**, and your draft under **Manuscript prose**. Fields may remain empty.
4. Open **Papers** in Academic Writing Lab, or refresh that page. Your folder appears automatically when its root is valid. Open the paper and start writing. Approval is a separate action after you review the text.

## Keys — only needed when copying the raw template yourself

If you downloaded a personalised ZIP, the keys are already filled in.

If you copied the raw template files, replace every `<paper-key>` with one unique short key, such as `coastal-study`. Replace `<paper-title>` in `root.md` with your title. Angle-bracket placeholders are deliberately invalid until filled in. Use letters, numbers, hyphens or underscores for keys; no UUID is required.

The root's `awl_id` identifies the paper. Every card's `paper_id` must match it. Each card also has its own unique `awl_id`, such as `coastal-study-literature-argument`. Keep keys stable when renaming your files or titles. For another paper, start with fresh blank templates or download a ZIP with another key; do not copy a completed paper unchanged.

## Add your own argument

1. Copy an argument file within `Cards/`, give it a readable filename such as `05_Translation.md`, and change its `#` title.
2. Give the copy a new `awl_id`, such as `coastal-study-translation`. Keep its `paper_id` unchanged.
3. Add its link to **Argument order** in `root.md`, indented under its section:

```markdown
- [Introduction](Cards/01_Introduction.md)
    - [Introduction argument](Cards/02_Introduction_argument.md)
    - [Translation](Cards/05_Translation.md)
```

The root outline controls the order. A section has `card_type: section`; an argument has `card_type: argument`. For a subsection use `card_type: subsection`, indent it under a section, then indent its arguments one level further. Keep all linked card files directly in `Cards/`. If a filename contains spaces, use `%20` in its Markdown link; the supplied filenames avoid this.

## Formatting and sources

`##` starts a card field. Use `###` or smaller headings inside a field. You can use bold, lists, links and quotations there. Retain the field names so the Lab can locate your own manuscript text.

Literature PDFs and source files can be kept in this folder, but placing a PDF here does not automatically create a verified citation or quotation card. Use the Lab's source import and **References → Add BibTeX**, or write your evidence notes manually.

Obsidian files and app edits share the same manuscript; the template is not an automatic connection to Overleaf. Sync delivery depends on your configured vault service.

## Write across a whole section

In Papers, choose **Write whole section** beside a section. Keep the agreed outline in the support panel and draft connected prose in the large editor. Argument cards remain available. Whole-section exports require an explicit switch to section text and approval.
