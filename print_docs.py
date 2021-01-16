#!/usr/bin/env/python3

# Requires the `markdown2` and `toml` packages:
#   `pip install markdown2 toml`
#

# interpreter and general external access
import sys
import os
import os.path
import argparse
import subprocess
from jinja2 import Environment, FileSystemLoader, select_autoescape

# directories manipulation
import shutil
import gzip

# data structures
from pathlib import Path
from typing import List
from collections import defaultdict
from import_name import ImportName

# data structures manipulation
import json
import toml
import glob
import re
import textwrap
import markdown2
import html
from urllib.parse import quote
from functools import reduce
import networkx as nx

# get arguments from script inititation
parser = argparse.ArgumentParser('Options to print_docs.py')
parser.add_argument('-w', help = 'Specify site root URL')
parser.add_argument('-l', help = 'Symlink CSS and JS instead of copying', action = "store_true")
parser.add_argument('-r', help = 'relative path to mathlib root directory')
parser.add_argument('-t', help = 'relative path to html output directory')
CLI_ARGS = parser.parse_args()

# setup templates environment
env = Environment(
  loader=FileSystemLoader('templates', 'utf-8'),
  autoescape=select_autoescape(['html', 'xml'])
)

# extra doc files to include in generation
# the content has moved to the community website,
# but we still build them to avoid broken links
# format: (filename_root, display_name, source, community_site_url)
# TODO: avoid broken links and remove unnecessary structures and action
EXTRA_DOC_FILES = [
  ('overview', 'mathlib overview', 'docs/mathlib-overview.md', 'mathlib-overview'),
  ('tactic_writing', 'tactic writing', 'docs/extras/tactic_writing.md', 'extras/tactic_writing'),
  ('calc', 'calc mode', 'docs/extras/calc.md', 'extras/calc'),
  ('conv', 'conv mode', 'docs/extras/conv.md', 'extras/conv'),
  ('simp', 'simplification', 'docs/extras/simp.md', 'extras/simp'),
  ('well_founded_recursion', 'well founded recursion', 'docs/extras/well_founded_recursion.md','extras/well_founded_recursion'),
  ('style', 'style guide', 'docs/contribute/style.md','contribute/style'),
  ('doc_style', 'documentation style guide', 'docs/contribute/doc.md','contribute/doc'),
  ('naming', 'naming conventions', 'docs/contribute/naming.md','contribute/naming')
]

# setup global variables
ROOT = os.getcwd()
SITE_ROOT = CLI_ARGS.w if CLI_ARGS.w else "/"
MATHLIB_SRC_ROOT = os.path.join(ROOT, CLI_ARGS.r if CLI_ARGS.r else '_target/deps/mathlib') + '/'
MATHLIB_DEST_ROOT = os.path.join(ROOT, CLI_ARGS.t if CLI_ARGS.t else 'html', '') # TODO: make sure nothing is left in docs_destination_root
LINK_PATTERNS = [(re.compile(r'Note \[(.*)\]', re.I), SITE_ROOT + r'notes.html#\1')]
LEAN_COMMIT = subprocess.check_output(['lean', '--run', 'src/lean_commit.lean']).decode()

with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
ml_data = parsed_toml['dependencies']['mathlib']
MATHLIB_COMMIT = ml_data['rev']
MATHLIB_GITHUB_ROOT = ml_data['git'].strip('/')

# ------------------------------------------------ START utils reading -------------------------------------------------

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
    for (cstr_name, _) in obj['constructors']:
      loc_map[cstr_name] = i_name
    for (sf_name, _) in obj['structure_fields']:
      loc_map[sf_name] = i_name
    if len(obj['structure_fields']) > 0:
      loc_map[obj['name'] + '.mk'] = i_name
  return file_map, loc_map

# ------------------------------------------------ END utils reading ---------------------------------------------------


# ------------------------------------------------ START read source files -------------------------------------------------

def read_src_data():
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

# ------------------------------------------------ END read source files -----------------------------------------------------

# ------------------------------------------------ START common utils --------------------------------------------------------

def convert_markdown(ds, toc=False):
  extras = ['code-friendly', 'cuddled-lists', 'fenced-code-blocks', 'link-patterns', 'tables']
  if toc:
    extras.append('toc')
  return markdown2.markdown(ds, extras=extras, link_patterns = LINK_PATTERNS)

# returns (pagetitle, intro_block), [(tactic_name, tactic_block)]
def split_tactic_list(markdown):
  entries = re.findall(r'(?<=# )(.*)([\s\S]*?)(?=(##|\Z))', markdown)
  return entries[0], entries[1:]

# ------------------------------------------------ END common utils ----------------------------------------------------------

# ------------------------------------------------ START templates setup ----------------------------------------------------
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

def import_options(loc_map, decl_name, import_string):
  direct_import_paths = []
  if decl_name in loc_map:
    direct_import_paths.append(loc_map[decl_name].name)
  if import_string != '' and import_string not in direct_import_paths:
    direct_import_paths.append(import_string)
  if any(i.startswith('init.') for i in direct_import_paths):
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul>'.format('<li>imported by default</li>')
  elif len(direct_import_paths) > 0:
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul>'.format(
      '\n'.join(['<li>import {}</li>'.format(d) for d in direct_import_paths]))
  else:
    return ''

def kind_of_decl(decl):
  kind = 'structure' if len(decl['structure_fields']) > 0 else 'inductive' if len(decl['constructors']) > 0 else decl['kind']
  if kind == 'thm': kind = 'theorem'
  elif kind == 'cnst': kind = 'constant'
  elif kind == 'ax': kind = 'axiom'
  return kind

def tag_id_of_name(tag):
  return tag.strip().replace(' ', '-')

def linkify_core(decl_name, text, loc_map):
  if decl_name in loc_map:
    tooltip = ' title="{}"'.format(decl_name) if text != decl_name else ''
    return '<a href="{0}#{1}"{3}>{2}</a>'.format(
      SITE_ROOT + loc_map[decl_name].url, decl_name, text, tooltip)
  elif text != decl_name:
    return '<span title="{0}">{1}</span>'.format(decl_name, text)
  else:
    return text

def linkify_efmt(f, loc_map):
  def linkify_linked(string, loc_map):
    return ''.join(
      match[4] if match[0] == '' else
      match[1] + linkify_core(match[0], match[2], loc_map) + match[3]
      for match in re.findall(r'\ue000(.+?)\ue001(\s*)(.*?)(\s*)\ue002|([^\ue000]+)', string))

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

def linkify_markdown(string, loc_map):
  def linkify_type(string):
    splitstr = re.split(r'([\s\[\]\(\)\{\}])', string)
    tks = map(lambda s: linkify_core(s, s, loc_map), splitstr)
    return "".join(tks)

  string = re.sub(r'<code>([^<]+)</code>',
    lambda p: '<code>{}</code>'.format(linkify_type(p.group(1))), string)
  string = re.sub(r'<span class="n">([^<]+)</span>',
    lambda p: '<span class="n">{}</span>'.format(linkify_type(p.group(1))), string)
  return string

def link_to_decl(decl_name, loc_map):
  return f'{SITE_ROOT}{loc_map[decl_name].url}#{decl_name}'

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
    r'^-{3,}\s*$', r'^\s*'
  ]

  text = reduce(lambda text, p: re.compile(p, re.MULTILINE).sub(r'\1', text), remove_keep_contents_patterns, text)
  text = reduce(lambda text, p: re.compile(p, re.MULTILINE).sub('', text), remove_patterns, text)

  # collapse lines again
  text = re.compile(r'\s*\.?\n').sub('. ', text)

  return textwrap.shorten(text, width = max_chars, placeholder="…")
  
def htmlify_name(n):
  return '.'.join([f'<span class="name">{ html.escape(part) }</span>' for part in n.split('.')])

def library_link(filename: ImportName, line=None):
  mathlib_github_src_root = "{0}/blob/{1}/src/".format(MATHLIB_GITHUB_ROOT, MATHLIB_COMMIT)
  lean_root = 'https://github.com/leanprover-community/lean/blob/{}/library/'.format(LEAN_COMMIT)

  # TODO: allow extending this for third-party projects
  library_link_roots = {
    'core': lean_root,
    'mathlib': mathlib_github_src_root,
  }

  try:
    root = library_link_roots[filename.project]
  except KeyError:
    return ""  # empty string is handled as a self-link

  root += '/'.join(filename.parts) + '.lean'
  if line is not None:
    root += f'#L{line}'
  return root

def setup_jinja_env(file_map, loc_map, instances):
  env.globals['import_graph'] = trace_deps(file_map)
  env.globals['site_tree'] = mk_site_tree(file_map)
  env.globals['instances'] = instances
  env.globals['import_options'] = lambda d, i: import_options(loc_map, d, i)
  env.globals['find_import_path'] = lambda d: find_import_path(loc_map, d)
  env.globals['sorted'] = sorted
  env.globals['extra_doc_files'] = EXTRA_DOC_FILES
  env.globals['mathlib_github_root'] = MATHLIB_GITHUB_ROOT
  env.globals['mathlib_commit'] = MATHLIB_COMMIT
  env.globals['lean_commit'] = LEAN_COMMIT
  env.globals['site_root'] = SITE_ROOT
  env.globals['kind_of_decl'] = kind_of_decl
  env.globals['tag_id_of_name'] = tag_id_of_name
  env.globals['tag_ids_of_names'] = lambda names: ' '.join(tag_id_of_name(n) for n in names)
  env.globals['library_link'] = library_link

  env.filters['linkify'] = lambda x: linkify_core(x, x, loc_map)
  env.filters['linkify_efmt'] = lambda x: linkify_efmt(x, loc_map)
  env.filters['convert_markdown'] = lambda x: linkify_markdown(convert_markdown(x), loc_map) # TODO: this is probably very broken
  env.filters['link_to_decl'] = lambda x: link_to_decl(x, loc_map)
  env.filters['plaintext_summary'] = plaintext_summary
  env.filters['split_on_hr'] = lambda x: x.split('\n---\n', 1)[-1]
  env.filters['htmlify_name'] = htmlify_name
  env.filters['library_link'] = library_link

# ------------------------------------------------ END templates setup ------------------------------------------------------


# ------------------------------------------------ START write destination files ----------------------------------------------

def open_outfile(filename, mode = 'w'):
  filename = os.path.join(MATHLIB_DEST_ROOT, filename)
  os.makedirs(os.path.dirname(filename), exist_ok=True)
  return open(filename, mode, encoding='utf-8')

def write_pure_md_file(source, dest, name):
  with open(source) as infile:
    body = convert_markdown(infile.read(), True)

  with open_outfile(dest) as out:
    out.write(env.get_template('pure_md.j2').render(
      active_path = '',
      name = name,
      body = body,
    ))

def write_html_files(partition, loc_map, notes, mod_docs, instances, tactic_docs):
  with open_outfile('index.html') as out:
    out.write(env.get_template('index.j2').render(
      active_path=''))

  with open_outfile('404.html') as out:
    out.write(env.get_template('404.j2').render(
      active_path=''))

  with open_outfile('notes.html') as out:
    out.write(env.get_template('notes.j2').render(
      active_path='',
      notes = sorted(notes, key = lambda n: n[0])))

  kinds = [('tactic', 'tactics'), ('command', 'commands'), ('hole_command', 'hole_commands'), ('attribute', 'attributes')]
  for (kind, filename) in kinds:
    entries = [e for e in tactic_docs if e['category'] == kind]
    with open_outfile(filename + '.html') as out:
      out.write(env.get_template(filename + '.j2').render(
        active_path='',
        entries = sorted(entries, key = lambda n: n['name']),
        tagset = sorted(set(t for e in entries for t in e['tags']))))

  for filename, decls in partition.items():
    md = mod_docs.get(filename, [])
    with open_outfile(MATHLIB_DEST_ROOT + filename.url) as out:
      out.write(env.get_template('module.j2').render(
        active_path = filename.url,
        filename = filename,
        items = sorted(md + decls, key = lambda d: d['line']),
        decl_names = sorted(d['name'] for d in decls),
      ))

  for (filename, displayname, source, _) in EXTRA_DOC_FILES:
    write_pure_md_file(MATHLIB_SRC_ROOT + source, filename + '.html', displayname)

def write_site_map(partition):
  with open_outfile('sitemap.txt') as out:
    for filename in partition:
      out.write(SITE_ROOT + filename.url + '\n')
    for n in ['index', 'tactics', 'commands', 'hole_commands', 'notes']:
      out.write(SITE_ROOT + n + '.html\n')
    for (filename, _, _, _) in EXTRA_DOC_FILES:
      out.write(SITE_ROOT + filename + '.html\n')

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

def write_docs_redirect(decl_name, decl_loc):
  url = SITE_ROOT + decl_loc.url
  with open_outfile('find/' + decl_name + '/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}#{quote(decl_name)}">')

def write_src_redirect(decl_name, decl_loc, file_map):
  url = library_link_from_decl_name(decl_name, decl_loc, file_map)
  with open_outfile('find/' + decl_name + '/src/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}">')

# TODO: see if we can do without the 'find' dir
def write_redirects(loc_map, file_map):
  for decl_name in loc_map:
    if decl_name.startswith('con.') and sys.platform == 'win32':
      continue  # can't write these files on windows
    write_docs_redirect(decl_name, loc_map[decl_name])
    write_src_redirect(decl_name, loc_map[decl_name], file_map)

def copy_web_files(path, use_symlinks):
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

def copy_yaml_files(path):
  for name in ['100.yaml', 'undergrad.yaml', 'overview.yaml']:
    shutil.copyfile(f'{MATHLIB_SRC_ROOT}docs/{name}', path+name)

def copy_static_files(path):
  for filename in glob.glob(os.path.join(ROOT, 'static', '*.*')):
    shutil.copy(filename, path)

def copy_files(path, use_symlinks): 
  copy_web_files(path, use_symlinks)
  copy_yaml_files(path)
  copy_static_files(path)
  
# write only declaration names in separate file
# TODO: delete when using data structure for searching
def write_decl_txt(loc_map):
  with open_outfile('decl.txt') as out:
    out.write('\n'.join(loc_map.keys()))

def mk_export_map_entry(decl_name, filename, kind, is_meta, line):
  return {
    'filename': str(filename.raw_path),
    'kind': kind,
    'is_meta': is_meta,
    'line': line,
    'src_link': library_link(filename, line),
    'docs_link': f'{SITE_ROOT}{filename.url}#{decl_name}'
  }

def mk_export_db(file_map):
  export_db = {}
  for _, decls in file_map.items():
    for obj in decls:
      export_db[obj['name']] = mk_export_map_entry(obj['name'], obj['filename'], obj['kind'], obj['is_meta'], obj['line'])
      export_db[obj['name']]['decl_header_html'] = env.get_template('decl_header.j2').render(decl=obj)
      for (cstr_name, _) in obj['constructors']:
        export_db[cstr_name] = mk_export_map_entry(cstr_name, obj['filename'], obj['kind'], obj['is_meta'], obj['line'])
      for (sf_name, _) in obj['structure_fields']:
        export_db[sf_name] = mk_export_map_entry(sf_name, obj['filename'],  obj['kind'], obj['is_meta'], obj['line'])
  return export_db

def write_export_db(export_db):
  json_str = json.dumps(export_db)
  with gzip.GzipFile(MATHLIB_DEST_ROOT + 'export_db.json.gz', 'w') as zout:
    zout.write(json_str.encode('utf-8'))

# ------------------------------------------------ END write destination files ----------------------------------------------

def main():
  file_map, loc_map, notes, mod_docs, instances, tactic_docs = read_src_data()

  setup_jinja_env(file_map, loc_map, instances)
  write_decl_txt(loc_map)
  write_html_files(file_map, loc_map, notes, mod_docs, instances, tactic_docs)

  write_redirects(loc_map, file_map)
  copy_files(MATHLIB_DEST_ROOT, use_symlinks=CLI_ARGS.l)
  write_export_db(mk_export_db(file_map))
  write_site_map(file_map)

if __name__ == '__main__':
  main()
