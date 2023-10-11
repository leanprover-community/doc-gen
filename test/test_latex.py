from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

import html
# can be removed if we make `print_docs` an installable module
sys.path.append(str(Path(__file__).parent.parent)) 

md = (
    MarkdownIt('commonmark' ,{'breaks':True,'html':True})
    .use(dollarmath_plugin)
    .enable('table')
)

env = Environment(
    loader=FileSystemLoader('templates', 'utf-8'),
    autoescape=select_autoescape(['html', 'xml'])
)

def write_pure_md_file(source, dest, name):
  with open(source) as infile:
    body = md.render(infile.read())

  with open(dest, 'w') as out:
    out.write(env.get_template('pure_md.j2').render(
      active_path = '',
      name = name,
      body = body,
    ))


write_pure_md_file('test/latex.md', 'latex.html', 'LaTeX test')