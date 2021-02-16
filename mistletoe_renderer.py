"""
This module contains a class CustomHTMLRenderer, which uses
mistletoe to generate HTML from markdown.

Extra features include:
- Library note links
- Managing LaTeX so that MathJax will be able to process it in the browser
- Syntax highlighting with Pygments
"""
import re

from mistletoe import Document, HTMLRenderer, span_token, latex_token
from pygments import highlight
from pygments.lexers import get_lexer_by_name as get_lexer
from pygments.formatters.html import HtmlFormatter

class NoteLink(span_token.SpanToken):
    """
    Detect library note links
    """
    parse_inner = False
    pattern = re.compile(r'Note \[(.*)\]', re.I)

    def __init__(self, match):
        self.body = match.group(0)
        self.note = match.group(1)


class CustomHTMLRenderer(HTMLRenderer):
    """
    Call the constructor with `site_root`.

    The main rendering function is `render_md`.
    """

    def __init__(self, site_root):
        self.site_root = site_root
        super().__init__(NoteLink, latex_token.Math)

    def render_md(self, ds):
        """
        A wrapper for this class's .render() function.

        Input is a string containing markdown with LaTeX,
        Output is a string containing HTML.

        Uses `mathjax_editing` to strip out sections of the text
        which potentially contain LaTeX and then splice them back in.
        """
        return self.render(Document(ds))

    def render_heading(self, token) -> str:
        """
        Override the default heading to provide links like in GitHub.

        TODO: populate a list of table of contents in the `.toc_html` field of the body
        """
        template = '<h{level} id="{anchor}" class="markdown-heading">{inner} <a class="hover-link" href="#{anchor}">#</a></h{level}>'
        inner: str = self.render_inner(token)
        # generate anchor following what github does
        # See info and links at https://gist.github.com/asabaylus/3071099
        anchor = inner.strip().lower()
        anchor = re.sub(r'[^\w\- ]+', '', anchor).replace(' ', '-')
        return template.format(level=token.level, inner=inner, anchor=anchor)

    # Use pygments highlighting.
    # https://github.com/miyuchina/mistletoe/blob/8f2f0161b2af92f8dd25a0a55cb7d437a67938bc/contrib/pygments_renderer.py
    # HTMLCodeFormatter class copied from markdown2:
    # https://github.com/trentm/python-markdown2/blob/2c58d70da0279fe19d04b3269b04d360a56c01ce/lib/markdown2.py#L1826
    class HtmlCodeFormatter(HtmlFormatter):
        def _wrap_code(self, inner):
            """A function for use in a Pygments Formatter which
            wraps in <code> tags.
            """
            yield 0, "<code>"
            for tup in inner:
                yield tup
            yield 0, "</code>"

        def wrap(self, source, outfile):
            """Return the source with a code, pre, and div."""
            return self._wrap_div(self._wrap_pre(self._wrap_code(source)))

    # `cssclass` here should agree with what we have in pygments.css
    formatter = HtmlCodeFormatter(cssclass='codehilite')

    def render_block_code(self, token):
        # replace math before highlighting
        code = token.children[0].content
        try:
            # default to 'lean' if no language is specified
            lexer = get_lexer(
                token.language) if token.language else get_lexer('lean')
        except Exception:
            lexer = get_lexer('text')
        return highlight(code, lexer, self.formatter)

    def render_note_link(self, token):
        """
        Render library note links
        """
        return f'<a href="{self.site_root}notes.html#{token.note}">{token.body}</a>'

    @staticmethod
    def render_math(token):
        return token.content
