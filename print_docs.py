#!/usr/bin/env/python3
"""
Run using ./gen_docs unless debugging

Example standalone usage for local testing (requires export.json):
$ python3 print_docs.py -r "_target/deps/mathlib" -w "/" -l

"""
import json
import os
import os.path
import glob
import textwrap
import re
import subprocess
import toml
import shutil
import argparse
import html
import gzip
from urllib.parse import quote
from functools import reduce
import textwrap
from collections import Counter, defaultdict, namedtuple
from pathlib import Path
from typing import NamedTuple, List, Optional
import sys

from mistletoe_renderer import CustomHTMLRenderer
import pybtex.database
from pybtex.style.labels.alpha import LabelStyle
from pylatexenc.latex2text import LatexNodes2Text
import networkx as nx

root = os.getcwd()

from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader('templates', 'utf-8'),
    autoescape=select_autoescape(['html', 'xml'])
)
env.globals['sorted'] = sorted

parser = argparse.ArgumentParser('Options to print_docs.py')
parser.add_argument('-w', help = 'Specify site root URL')
parser.add_argument('-l', help = 'Symlink CSS and JS instead of copying', action = "store_true")
parser.add_argument('-r', help = 'relative path to mathlib root directory')
parser.add_argument('-t', help = 'relative path to html output directory')
cl_args = parser.parse_args()

# extra doc files to include in generation
# the content has moved to the community website,
# but we still build them to avoid broken links
# format: (filename_root, display_name, source relative to local_lean_root, community_site_url)
extra_doc_files = [('overview', 'mathlib overview', 'docs/mathlib-overview.md', 'mathlib-overview'),
                   ('tactic_writing', 'tactic writing', 'docs/extras/tactic_writing.md', 'extras/tactic_writing'),
                   ('calc', 'calc mode', 'docs/extras/calc.md', 'extras/calc'),
                   ('conv', 'conv mode', 'docs/extras/conv.md', 'extras/conv'),
                   ('simp', 'simplification', 'docs/extras/simp.md', 'extras/simp'),
                   ('well_founded_recursion', 'well founded recursion', 'docs/extras/well_founded_recursion.md','extras/well_founded_recursion'),
                   ('style', 'style guide', 'docs/contribute/style.md','contribute/style'),
                   ('doc_style', 'documentation style guide', 'docs/contribute/doc.md','contribute/doc'),
                   ('naming', 'naming conventions', 'docs/contribute/naming.md','contribute/naming')]
env.globals['extra_doc_files'] = extra_doc_files

# test doc files to include in generation
# will not be linked to from the doc pages
# format: (filename_root, display_name, source relative to cwd)
test_doc_files = [('latex', 'latex tests', 'test/latex.md')]
env.globals['test_doc_files'] = test_doc_files

# path to put generated html
html_root = os.path.join(root, cl_args.t if cl_args.t else 'html') + '/'

# TODO: make sure nothing is left in html_root

# root of the site, for display purposes.
# override this setting with the `-w` flag.
site_root = "/"

# root directory of mathlib.
local_lean_root = os.path.join(root, cl_args.r if cl_args.r else '_target/deps/mathlib') + '/'

latexnodes2text = LatexNodes2Text()
def clean_tex(src: str) -> str:
  return latexnodes2text.latex_to_text(src)

def parse_bib_file(fname):
  bib = pybtex.database.parse_file(fname)

  label_style = LabelStyle()
  # cf. LabelStyle.format_labels in pybtex.style.labels.alpha:
  # label_style.format_label generates a label from author(s) + year
  # counted tracks the total number of times a label appears
  counted = Counter()

  for key, data in bib.entries.items():
    for author in data.persons['author']:
      # turn LaTeX special characters to Unicode,
      # since format_label does not correctly abbreviate names containing LaTeX
      author.last_names = list(map(clean_tex, author.last_names))
    label = label_style.format_label(data)
    counted.update([label])
    data.alpha_label = label
  # count tracks the number of times a duplicate label has been finalized
  count = Counter()

  for key, data in bib.entries.items():
    label = data.alpha_label
    # Finalize duplicate labels by appending 'a', 'b', 'c', etc.
    # Currently the ordering is determined by `docs/references.bib`
    if counted[label] > 1:
      data.alpha_label += chr(ord('a') + count[label])
      count.update([label])

    url = None
    if 'link' in data.fields:
      url = data.fields['link'][5:-1]
    elif 'url' in data.fields:
      url = data.fields['url']
    elif 'eprint' in data.fields:
      eprint = data.fields['eprint']
      if eprint.startswith('arXiv:'):
        url = 'https://arxiv.org/abs/'+eprint[6:]
      elif (('archivePrefix' in data.fields and data.fields['archivePrefix'] == 'arXiv') or
        ('eprinttype' in data.fields and data.fields['eprinttype'] == 'arXiv')):
        url = 'https://arxiv.org/abs/'+eprint
      else:
        url = eprint
    elif 'doi' in data.fields:
      url = 'https://doi.org/'+data.fields['doi']
    # else:
      # raise ValueError(f"Couldn't find a url for bib item {key}")
    if url:
      if url.startswith(r'\url'):
        url = url[4:].strip('{}')
      url = url.replace(r'\_', '_')

    if 'journal' in data.fields and data.fields['journal'] != 'CoRR':
      journal = data.fields['journal']
    elif 'booktitle' in data.fields:
      journal = data.fields['booktitle']
    else:
      journal = None
    data.fields['url'] = url
    data.fields['journal'] = journal
    data.backrefs = []

  return bib

with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
ml_data = parsed_toml['dependencies']['mathlib']
mathlib_commit = ml_data['rev']
mathlib_github_root = ml_data['git'].strip('/')

if cl_args.w:
  site_root = cl_args.w

mathlib_github_src_root = "{0}/blob/{1}/src/".format(mathlib_github_root, mathlib_commit)

lean_commit = subprocess.check_output(['lean', '--run', 'src/lean_commit.lean']).decode()
lean_root = 'https://github.com/leanprover-community/lean/blob/{}/library/'.format(lean_commit)

def get_name_from_leanpkg_path(p: Path) -> str:
  """ get the package name corresponding to a source path """
  # lean core?
  if p.parts[-5:] == Path('bin/../lib/lean/library').parts:
    return "core"
  if p.parts[-3:] == Path('bin/../library').parts:
    return "core"

  # try the toml
  p_leanpkg = p / '..' / 'leanpkg.toml'
  try:
    f = p_leanpkg.open()
  except FileNotFoundError:
    pass
  else:
    with f:
      parsed_toml = toml.loads(f.read())
    return parsed_toml['package']['name']

  return '<unknown>'

lean_paths = [
  Path(p)
  for p in json.loads(subprocess.check_output(['lean', '--path']).decode())['path']
]
path_info = [(p.resolve(), get_name_from_leanpkg_path(p)) for p in lean_paths]

class ImportName(NamedTuple):
  project: str
  parts: List[str]
  raw_path: Path

  @classmethod
  def of(cls, fname: str):
    fname = Path(fname)
    for p, name in path_info:
      try:
        rel_path = fname.relative_to(p)
      except ValueError:
        pass
      else:
        return cls(name, rel_path.with_suffix('').parts, fname)
    path_details = "".join(f" - {p}\n" for p, _ in path_info)
    raise RuntimeError(
      f"Cannot determine import name for {fname}; it is not within any of the directories returned by `lean --path`:\n"
      f"{path_details}"
      f"Did you generate `export.json` using a different Lean installation to the one this script is running with?")

  @property
  def name(self):
    return '.'.join(self.parts)

  @property
  def url(self):
    return '/'.join(self.parts) + '.html'

env.globals['mathlib_github_root'] = mathlib_github_root
env.globals['mathlib_commit'] = mathlib_commit
env.globals['lean_commit'] = lean_commit
env.globals['site_root'] = site_root

markdown_renderer = CustomHTMLRenderer()

def convert_markdown(ds):
  return markdown_renderer.render_md(ds)

# TODO: allow extending this for third-party projects
library_link_roots = {
  'core': lean_root,
  'mathlib': mathlib_github_src_root,
}

def library_link(filename: ImportName, line=None):
  try:
    root = library_link_roots[filename.project]
  except KeyError:
    return ""  # empty string is handled as a self-link

  root += '/'.join(filename.parts) + '.lean'
  if line is not None:
    root += f'#L{line}'
  return root

env.globals['library_link'] = library_link
env.filters['library_link'] = library_link

def name_in_decl(decl_name, dmap):
  if dmap['name'] == decl_name:
    return True
  if decl_name in [sf[0] for sf in dmap['structure_fields']]:
    return True
  if decl_name in [sf[0] for sf in dmap['constructors']]:
    return True
  return False

def library_link_from_decl_name(decl_name, decl_loc, file_map):
  try:
    e = next(d for d in file_map[decl_loc] if name_in_decl(decl_name, d))
  except StopIteration as e:
    if decl_name[-3:] == '.mk':
      return library_link_from_decl_name(decl_name[:-3], decl_loc, file_map)
    print(f'{decl_name} appears in {decl_loc}, but we do not have data for that declaration. file_map:')
    print(file_map[decl_loc])
    raise e
  return library_link(decl_loc, e['line'])

def open_outfile(filename, mode = 'w'):
    filename = os.path.join(html_root, filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    return open(filename, mode, encoding='utf-8')

def separate_results(objs):
  file_map = defaultdict(list)
  loc_map = {}
  for obj in objs:
    # replace the filenames in-place with parsed filename objects
    i_name = obj['filename'] = ImportName.of(obj['filename'])
    if i_name.project == '.':
      continue  # this is doc-gen itself
    file_map[i_name].append(obj)
    loc_map[obj['name']] = i_name
    for (cstr_name, tp) in obj['constructors']:
      loc_map[cstr_name] = i_name
    for (sf_name, tp) in obj['structure_fields']:
      loc_map[sf_name] = i_name
    if len(obj['structure_fields']) > 0:
      loc_map[obj['name'] + '.mk'] = i_name
  return file_map, loc_map

def trace_deps(file_map):
  graph = nx.DiGraph()
  import_name_by_path = {k.raw_path: k for k in file_map}
  n = 0
  n_ok = 0
  for k in file_map:
    deps = subprocess.check_output(['lean', '--deps', str(k.raw_path)]).decode()
    graph.add_node(k)
    for p in deps.split():
      n += 1
      try:
        p = import_name_by_path[Path(p).with_suffix('.lean')]
      except KeyError:
        print(f"trace_deps: Path not recognized: {p}")
        continue
      graph.add_edge(k, p)
      n_ok += 1
  print(f"trace_deps: Processed {n_ok} / {n} dependency links")
  return graph

def load_json():
  with open('export.json', 'r', encoding='utf-8') as f:
    decls = json.load(f, strict=False)
  file_map, loc_map = separate_results(decls['decls'])
  for entry in decls['tactic_docs']:
    if len(entry['tags']) == 0:
      entry['tags'] = ['untagged']

  mod_docs = {ImportName.of(f): docs for f, docs in decls['mod_docs'].items()}
  # ensure the key is present for `default.lean` modules with no declarations
  for i_name in mod_docs:
    if i_name.project == '.':
      continue  # this is doc-gen itself
    file_map[i_name]

  return file_map, loc_map, decls['notes'], mod_docs, decls['instances'], decls['tactic_docs']

def linkify_core(decl_name, text, loc_map):
  if decl_name in loc_map:
    tooltip = ' title="{}"'.format(decl_name) if text != decl_name else ''
    return '<a href="{0}#{1}"{3}>{2}</a>'.format(
      site_root + loc_map[decl_name].url, decl_name, text, tooltip)
  elif text != decl_name:
    return '<span title="{0}">{1}</span>'.format(decl_name, text)
  else:
    return text

def linkify(string, loc_map):
  return linkify_core(string, string, loc_map)

def linkify_linked(string, loc_map):
  return ''.join(
    match[4] if match[0] == '' else
    match[1] + linkify_core(match[0], match[2], loc_map) + match[3]
    for match in re.findall(r'\ue000(.+?)\ue001(\s*)(.*?)(\s*)\ue002|([^\ue000]+)', string))

def linkify_efmt(f, loc_map):
  def go(f):
    if isinstance(f, str):
      f = f.replace('\n', ' ')
      # f = f.replace(' ', '&nbsp;')
      return linkify_linked(f, loc_map)
    elif f[0] == 'n':
      return f'<span class="fn">{go(f[1])}</span>'
    elif f[0] == 'c':
      return go(f[1]) + go(f[2])
    else:
      raise Exception('unknown efmt object')

  return go(['n', f])

# store number of backref anchors and notes in each file
num_backrefs = defaultdict(int)
num_notes = defaultdict(int)

def linkify_markdown(string: str, loc_map, bib) -> str:
  def linkify_type(string: str):
    splitstr = re.split(r'([\s\[\]\(\)\{\}])', string)
    tks = map(lambda s: linkify(s, loc_map), splitstr)
    return "".join(tks)

  def backref_title(filename: str):
    parts = filename.split('/')
    # drop .html
    parts[-1] = parts[-1].split('.')[0]
    return f'{current_project}: {".".join(parts)}'

  def note_backref(key: str) -> str:
    num_notes[current_filename] += 1
    backref_id = f'noteref{num_notes[current_filename]}'
    if current_project and current_project != 'test':
      global_notes[key].backrefs.append(
        (current_filename, backref_id, backref_title(current_filename))
      )
    return backref_id
  def bib_backref(key: str) -> str:
    num_backrefs[current_filename] += 1
    backref_id = f'backref{num_backrefs[current_filename]}'
    if current_project and current_project != 'test':
      bib.entries[key].backrefs.append(
        (current_filename, backref_id, backref_title(current_filename))
      )
    return backref_id

  def linkify_note(body: str, note: str) -> str:
    if note in global_notes:
      return f'<a id="{note_backref(note)}" href="{site_root}notes.html#{note}">{body}</a>'
    return body
  def linkify_named_ref(body: str, name: str, key: str) -> str:
    if key in bib.entries:
      alpha_label = bib.entries[key].alpha_label
      return f'<a id="{bib_backref(key)}" href="{site_root}references.html#{alpha_label}">{name}</a>'
    return body
  def linkify_standalone_ref(body: str, key: str) -> str:
    if key in bib.entries:
      alpha_label = bib.entries[key].alpha_label
      return f'<a id="{bib_backref(key)}" href="{site_root}references.html#{alpha_label}">[{alpha_label}]</a>'
    return body

  # notes
  string = re.compile(r'Note \[(.*)\]', re.I).sub(
    lambda p: linkify_note(p.group(0), p.group(1)), string)
  # inline declaration names
  string = re.sub(r'<code>([^<]+)</code>',
    lambda p: f'<code>{linkify_type(p.group(1))}</code>', string)
  # declaration names in highlighted Lean code snippets
  string = re.sub(r'<span class="n">([^<]+)</span>',
    lambda p: f'<span class="n">{linkify_type(p.group(1))}</span>', string)
  # references (don't match if there are illegal characters for a BibTeX key,
  # cf. https://tex.stackexchange.com/a/408548)
  string = re.sub(r'\[([^\]]+)\]\s*\[([^{ },~#%\\]+)\]',
    lambda p: linkify_named_ref(p.group(0), p.group(1), p.group(2)), string)
  string = re.sub(r'\[([^{ },~#%\\]+)\]',
    lambda p: linkify_standalone_ref(p.group(0), p.group(1)), string)
  return string

def plaintext_summary(markdown, max_chars = 200):
  # collapse lines
  text = re.compile(r'([a-zA-Z`(),;\$\-]) *\n *([a-zA-Z`()\$])').sub(r'\1 \2', markdown)

  # adapted from https://github.com/writeas/go-strip-markdown/blob/master/strip.go
  remove_keep_contents_patterns = [
    r'(?m)^([\s\t]*)([\*\-\+]|\d\.)\s+',
    r'\*\*([^*]+)\*\*',
    r'\*([^*]+)\*',
    r'(?m)^\#{1,6}\s*([^#]+)\s*(\#{1,6})?$',
    r'__([^_]+)__',
    r'_([^_]+)_',
    r'\!\[(.*?)\]\s?[\[\(].*?[\]\)]',
    r'\[(.*?)\][\[\(].*?[\]\)]'
  ]
  remove_patterns = [
    r'^\s{0,3}>\s?', r'^={2,}', r'`{3}.*$', r'~~', r'^[=\-]{2,}\s*$',
    r'^-{3,}\s*$', r'^\s*']

  text = reduce(lambda text, p: re.compile(p, re.MULTILINE).sub(r'\1', text), remove_keep_contents_patterns, text)
  text = reduce(lambda text, p: re.compile(p, re.MULTILINE).sub('', text), remove_patterns, text)

  # collapse lines again
  text = re.compile(r'\s*\.?\n').sub('. ', text)

  return textwrap.shorten(text, width = max_chars, placeholder="…")

def link_to_decl(decl_name, loc_map):
  return f'{site_root}{loc_map[decl_name].url}#{decl_name}'

def kind_of_decl(decl):
  kind = 'structure' if len(decl['structure_fields']) > 0 else 'inductive' if len(decl['constructors']) > 0 else decl['kind']
  if kind == 'thm': kind = 'theorem'
  elif kind == 'cnst': kind = 'constant'
  elif kind == 'ax': kind = 'axiom'
  return kind
env.globals['kind_of_decl'] = kind_of_decl

def htmlify_name(n):
  return '.'.join([f'<span class="name">{ html.escape(part) }</span>' for part in n.split('.')])
env.filters['htmlify_name'] = htmlify_name

# returns (pagetitle, intro_block), [(tactic_name, tactic_block)]
def split_tactic_list(markdown):
  entries = re.findall(r'(?<=# )(.*)([\s\S]*?)(?=(##|\Z))', markdown)
  return entries[0], entries[1:]

def import_options(loc_map, decl_name, import_string):
  direct_import_paths = []
  if decl_name in loc_map:
    direct_import_paths.append(loc_map[decl_name].name)
  if import_string != '' and import_string not in direct_import_paths:
    direct_import_paths.append(import_string)
  if any(i.startswith('init.') for i in direct_import_paths):
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul></details>'.format('<li>imported by default</li>')
  elif len(direct_import_paths) > 0:
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul></details>'.format(
      '\n'.join(['<li>import {}</li>'.format(d) for d in direct_import_paths]))
  else:
    return ''

def split_on_hr(description):
  return description.split('\n---\n', 1)[-1]
env.filters['split_on_hr'] = split_on_hr

def tag_id_of_name(tag):
  return tag.strip().replace(' ', '-')
env.globals['tag_id_of_name'] = tag_id_of_name
env.globals['tag_ids_of_names'] = lambda ns: ' '.join(tag_id_of_name(n) for n in ns)

def write_pure_md_file(source, dest, name):
  with open(source) as infile:
    body = convert_markdown(infile.read())

  with open_outfile(dest) as out:
    out.write(env.get_template('pure_md.j2').render(
      active_path = '',
      name = name,
      body = body,
    ))

def mk_site_tree(partition: List[ImportName]):
  filenames = [ [filename.project] + list(filename.parts) for filename in partition ]
  return mk_site_tree_core(filenames)

def mk_site_tree_core(filenames, path=[]):
  entries = []

  for dirname in sorted(set(dirname for dirname, *rest in filenames if rest != [])):
    new_path = path + [dirname]
    entries.append({
      "kind": "project" if not path else "dir",
      "name": dirname,
      "path": '/'.join(new_path[1:]),
      "children": mk_site_tree_core([rest for dn, *rest in filenames if rest != [] and dn == dirname], new_path)
    })

  for filename in sorted(filename for filename, *rest in filenames if rest == []):
    new_path = path + [filename]
    entries.append({
      "kind": "file",
      "name": filename,
      "path": '/'.join(new_path[1:]) + '.html',
    })

  return entries

def setup_jinja_globals(file_map, loc_map, instances, bib):
  env.globals['import_graph'] = trace_deps(file_map)
  env.globals['site_tree'] = mk_site_tree(file_map)
  env.globals['instances'] = instances
  env.globals['import_options'] = lambda d, i: import_options(loc_map, d, i)
  env.filters['linkify'] = lambda x: linkify(x, loc_map)
  env.filters['linkify_efmt'] = lambda x: linkify_efmt(x, loc_map)
  env.filters['convert_markdown'] = lambda x: linkify_markdown(convert_markdown(x), loc_map, bib) # TODO: this is probably very broken
  env.filters['link_to_decl'] = lambda x: link_to_decl(x, loc_map)
  env.filters['plaintext_summary'] = lambda x: plaintext_summary(x)
  env.filters['tex'] = lambda x: clean_tex(x)

# stores the full filename of the markdown being rendered
current_filename: Optional[str] = None
# stores the project of the file, e.g. "mathlib", "core", etc.
current_project: Optional[str] = None
global_notes = {}
GlobalNote = namedtuple('GlobalNote', ['md', 'backrefs'])
def write_html_files(partition, loc_map, notes, mod_docs, instances, tactic_docs, bib):
  global current_filename, current_project
  for note_name, note_markdown in notes:
    global_notes[note_name] = GlobalNote(note_markdown, [])

  with open_outfile('index.html') as out:
    current_filename = 'index.html'
    current_project = None
    out.write(env.get_template('index.j2').render(
      active_path=''))

  with open_outfile('404.html') as out:
    current_filename = '404.html'
    current_project = None
    out.write(env.get_template('404.j2').render(
      active_path=''))

  kinds = [('tactic', 'tactics'), ('command', 'commands'), ('hole_command', 'hole_commands'), ('attribute', 'attributes')]
  current_project = 'docs'
  for (kind, filename) in kinds:
    entries = [e for e in tactic_docs if e['category'] == kind]
    with open_outfile(filename + '.html') as out:
      current_filename = filename + '.html'
      out.write(env.get_template(filename + '.j2').render(
        active_path='',
        entries = sorted(entries, key = lambda n: n['name']),
        tagset = sorted(set(t for e in entries for t in e['tags']))))

  for filename, decls in partition.items():
    md = mod_docs.get(filename, [])
    with open_outfile(html_root + filename.url) as out:
      current_project = filename.project
      current_filename = filename.url
      out.write(env.get_template('module.j2').render(
        active_path = filename.url,
        filename = filename,
        items = sorted(md + decls, key = lambda d: d['line']),
        decl_names = sorted(d['name'] for d in decls),
      ))

  current_project = 'extra'
  for (filename, displayname, source, _) in extra_doc_files:
    current_filename = filename + '.html'
    write_pure_md_file(local_lean_root + source, filename + '.html', displayname)

  current_project = 'test'
  for (filename, displayname, source) in test_doc_files:
    current_filename = filename + '.html'
    write_pure_md_file(source, filename + '.html', displayname)

  # generate notes.html and references.html last
  # so that we can add backrefs
  with open_outfile('notes.html') as out:
    current_project = 'docs'
    current_filename = 'notes.html'
    out.write(env.get_template('notes.j2').render(
      active_path='',
      notes = sorted(global_notes.items(), key = lambda n: n[0])))

  with open_outfile('references.html') as out:
    current_project = 'docs'
    current_filename = 'references.html'
    out.write(env.get_template('references.j2').render(
      active_path='',
      entries = sorted(bib.entries.items(), key = lambda e: e[1].alpha_label)))

  current_project = None
  current_filename = None

def write_site_map(partition):
  with open_outfile('sitemap.txt') as out:
    for filename in partition:
      out.write(site_root + filename.url + '\n')
    for n in ['index', 'tactics', 'commands', 'hole_commands', 'notes', 'references']:
      out.write(site_root + n + '.html\n')
    for (filename, _, _, _) in extra_doc_files:
      out.write(site_root + filename + '.html\n')

def write_docs_redirect(decl_name, decl_loc):
  url = site_root + decl_loc.url
  with open_outfile('find/' + decl_name + '/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}#{quote(decl_name)}">')

def write_src_redirect(decl_name, decl_loc, file_map):
  url = library_link_from_decl_name(decl_name, decl_loc, file_map)
  with open_outfile('find/' + decl_name + '/src/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}">')

def write_redirects(loc_map, file_map):
  for decl_name in loc_map:
    if (decl_name == 'con' or decl_name.startswith('con.')) and sys.platform == 'win32':
      continue  # can't write these files on windows
    write_docs_redirect(decl_name, loc_map[decl_name])
    write_src_redirect(decl_name, loc_map[decl_name], file_map)

def copy_css(path, use_symlinks):
  def cp(a, b):
    if use_symlinks:
      try:
        os.remove(b)
      except FileNotFoundError:
        pass
      os.symlink(os.path.relpath(a, os.path.dirname(b)), b)
    else:
      shutil.copyfile(a, b)

  cp('style.css', path+'style.css')
  cp('pygments.css', path+'pygments.css')
  cp('nav.js', path+'nav.js')
  cp('searchWorker.js', path+'searchWorker.js')

def copy_yaml_bib_files(path):
  for fn in ['100.yaml', 'undergrad.yaml', 'overview.yaml', 'references.bib']:
    shutil.copyfile(f'{local_lean_root}docs/{fn}', path+fn)

def copy_static_files(path):
  for filename in glob.glob(os.path.join(root, 'static', '*.*')):
    shutil.copy(filename, path)

def write_decl_txt(loc_map):
  with open_outfile('decl.txt') as out:
    out.write('\n'.join(loc_map.keys()))

def mk_export_map_entry(decl_name, filename, kind, is_meta, line, args, tp):
  return {'filename': str(filename.raw_path),
          'kind': kind,
          'is_meta': is_meta,
          'line': line,
          # 'args': args,
          # 'type': tp,
          'src_link': library_link(filename, line),
          'docs_link': f'{site_root}{filename.url}#{decl_name}'}

def mk_export_db(loc_map, file_map):
  export_db = {}
  for fn, decls in file_map.items():
    for obj in decls:
      export_db[obj['name']] = mk_export_map_entry(obj['name'], obj['filename'], obj['kind'], obj['is_meta'], obj['line'], obj['args'], obj['type'])
      export_db[obj['name']]['decl_header_html'] = env.get_template('decl_header.j2').render(decl=obj)
      for (cstr_name, tp) in obj['constructors']:
        export_db[cstr_name] = mk_export_map_entry(cstr_name, obj['filename'], obj['kind'], obj['is_meta'], obj['line'], [], tp)
      for (sf_name, tp) in obj['structure_fields']:
        export_db[sf_name] = mk_export_map_entry(sf_name, obj['filename'],  obj['kind'], obj['is_meta'], obj['line'], [], tp)
  return export_db

def write_export_db(export_db):
  json_str = json.dumps(export_db)
  with gzip.GzipFile(html_root + 'export_db.json.gz', 'w') as zout:
    zout.write(json_str.encode('utf-8'))

def main():
  bib = parse_bib_file(f'{local_lean_root}docs/references.bib')
  file_map, loc_map, notes, mod_docs, instances, tactic_docs = load_json()
  setup_jinja_globals(file_map, loc_map, instances, bib)
  write_decl_txt(loc_map)
  write_html_files(file_map, loc_map, notes, mod_docs, instances, tactic_docs, bib)
  write_redirects(loc_map, file_map)
  copy_css(html_root, use_symlinks=cl_args.l)
  copy_yaml_bib_files(html_root)
  copy_static_files(html_root)
  write_export_db(mk_export_db(loc_map, file_map))
  write_site_map(file_map)

if __name__ == '__main__':
  main()
