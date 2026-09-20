# Springer Nature export update

The only complete LaTeX export uses the user-supplied Springer Nature 3.1 (December 2024) source in `templates/latex/springer-nature-v3.1.tex`. The file is stored verbatim. The common renderer reuses its preamble and replaces tutorial content with approved manuscript text. No alternative document class, font or margin changes are introduced.

The preview API retains `tex` as the body fragment for existing clients. `document_tex` supplies the full document, `document_filename` is `main.tex`, and `bibliography_filename` is `sn-bibliography.bib`. Uncited exports omit the bibliography command; empty/unapproved selections do not produce an empty manuscript shell. Actual author metadata is left to the author.

The export dialog previews the full document by default, downloads it with matching bibliography naming, and retains a separate Copy section text action. Existing LaTeX list/formatting commands select LaTeX mode. Private notes and source quotations are not exported.

Validation: 30 Python export/bibliography tests; 14 browser-module tests; a temporary approved LaTeX paragraph exported and compiled with four resolved bibliography entries. The WISE outline compiled with 41 sources and two external PNGs. Template compilation used a clean directory containing only the supplied class/style to avoid unrelated auxiliary files in Downloads.

The 18 WISE draft updates were saved through the revision-aware API with source hashes and backups. Existing prose was retained exactly; other cards were unchanged. No live paragraph was approved as part of verification.

At the author’s subsequent request, those 18 outlines moved to a separate `Writing outline` field and an Outline support tab. The first paragraph’s newer wording and citations were preserved; only the known inserted scaffolds were removed from remaining prose. Side notes do not affect prose approval or LaTeX export.
