"""One manuscript template: the user's Springer Nature 3.1 (December 2024).

Keep the supplied template intact. Reuse its preamble, replacing its tutorial
body with the selected author content. No alternate class or preview fallback.
"""
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates/latex/springer-nature-v3.1.tex'
TEMPLATE_ID = 'springer-nature-v3.1-december-2024'
BIBLIOGRAPHY_FILENAME = 'sn-bibliography.bib'


def springer_preamble(additional_preamble=''):
    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    preamble, marker, _ = source.partition(r'\begin{document}')
    if not marker:
        raise ValueError('The Springer Nature template is incomplete.')
    return preamble + (additional_preamble.rstrip() + '\n\n' if additional_preamble else '')


def springer_document(body_tex, title_tex, *, bibliography=True, additional_preamble=''):
    """Title is already escaped; body is an approved LaTeX fragment."""
    if not body_tex.strip():
        return ''
    frontmatter = '\n'.join([
        r'\begin{document}', '',
        r'\title{' + title_tex + '}', '',
        '% Add the actual authors and affiliations using the template commands:',
        r'% \author*{\fnm{Given name} \sur{Family name}}\email{address}',
        r'% \affil{\orgdiv{Department}, \orgname{Organisation}, \orgaddress{\country{Country}}}',
        '% Add your approved abstract and keywords when ready:',
        r'% \abstract{...}', r'% \keywords{...}', '',
        r'\maketitle', '',
    ])
    ending = '\n\n' + r'\backmatter' + '\n'
    if bibliography:
        ending += '\n' + r'\bibliography{sn-bibliography}' + '% cited entries supplied separately\n'
    ending += '\n' + r'\end{document}' + '\n'
    return springer_preamble(additional_preamble) + frontmatter + body_tex.rstrip() + ending
