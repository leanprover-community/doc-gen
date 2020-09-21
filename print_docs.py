#!/usr/bin/env/python3

# Requires the `markdown2` and `toml` packages:
#   `pip install markdown2 toml`
#
# This script is not Windows friendly.
#

import json
import os
import os.path
import glob
import textwrap
import markdown2
import re
import subprocess
import toml
import shutil
import argparse
import html
import gzip
from urllib.parse import quote

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
# format: (filename_root, display_name, source, community_site_url)
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

# path to put generated html
html_root = os.path.join(root, cl_args.t if cl_args.t else 'html') + '/'

# TODO: make sure nothing is left in html_root

# root of the site, for display purposes.
# override this setting with the `-w` flag.
site_root = "/"

# root directory of mathlib.
local_lean_root = os.path.join(root, cl_args.r if cl_args.r else '_target/deps/mathlib') + '/'



mathlib_commit = 'lean-3.4.2' # default
mathlib_github_root = 'https://github.com/leanprover-community/mathlib' # default
with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
  f.close()
  ml_data = parsed_toml['dependencies']['mathlib']
  mathlib_commit = ml_data['rev'][:7]
  mathlib_github_root = ml_data['git'].strip('/')

if cl_args.w:
  site_root = cl_args.w

mathlib_github_src_root = "{0}/blob/{1}/src/".format(mathlib_github_root, mathlib_commit)

lean_commit = subprocess.check_output(['lean', '--run', 'src/lean_commit.lean']).decode()[:7]
lean_root = 'https://github.com/leanprover-community/lean/blob/{}/library/'.format(lean_commit)

env.globals['mathlib_github_root'] = mathlib_github_root
env.globals['mathlib_commit'] = mathlib_commit
env.globals['lean_commit'] = lean_commit
env.globals['site_root'] = site_root

note_regex = re.compile(r'Note \[(.*)\]', re.I)
target_url_regex = site_root + r'notes.html#\1'
link_patterns = [(note_regex, target_url_regex)]

def convert_markdown(ds, toc=False):
  extras = ['code-friendly', 'cuddled-lists', 'fenced-code-blocks', 'link-patterns']
  if toc:
    extras.append('toc')
  return markdown2.markdown(ds, extras=extras, link_patterns = link_patterns)

def filename_core(root, filename, ext):
  if 'lean/library' in filename:
    return root + 'core/' + filename.split('lean/library/', 1)[1][:-4] + ext
  elif 'mathlib/src' in filename:
    return root + filename.split('mathlib/src/', 1)[1][:-4] + ext
  else:
    return root + filename.split('mathlib/scripts/', 1)[1][:-4] + ext

def filename_import(filename):
  return filename_core('', filename, '')[:-1].replace('/', '.')
env.filters['filename_import'] = filename_import

def library_link(filename, line=None):
  root = lean_root + filename.split('lean/library/', 1)[1] \
           if 'lean/library' in filename \
           else mathlib_github_src_root + filename.split('mathlib/src/', 1)[1]
  return root + ('#L' + str(line) if line is not None else '')
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
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    return open(filename, mode, encoding='utf-8')

def separate_results(objs):
  file_map = {}
  loc_map = {}
  for obj in objs:
    if 'lean/library' not in obj['filename'] and 'mathlib/src' not in obj['filename']:
      continue
    if obj['filename'] not in file_map:
      file_map[obj['filename']] = [obj]
    else:
      file_map[obj['filename']].append(obj)
    loc_map[obj['name']] = obj['filename']
    for (cstr_name, tp) in obj['constructors']:
      loc_map[cstr_name] = obj['filename']
    for (sf_name, tp) in obj['structure_fields']:
      loc_map[sf_name] = obj['filename']
    if len(obj['structure_fields']) > 0:
      loc_map[obj['name'] + '.mk'] = obj['filename']
  return file_map, loc_map

def load_json():
  f = open('export.json', 'r', encoding='utf-8')
  decls = json.load(f, strict=False)
  f.close()
  file_map, loc_map = separate_results(decls['decls'])
  for entry in decls['tactic_docs']:
    if len(entry['tags']) == 0:
      entry['tags'] = ['untagged']
  return file_map, loc_map, decls['notes'], decls['mod_docs'], decls['instances'], decls['tactic_docs']

def linkify_core(decl_name, text, file_map):
  if decl_name in file_map:
    tooltip = ' title="{}"'.format(decl_name) if text != decl_name else ''
    return '<a href="{0}#{1}"{3}>{2}</a>'.format(
      filename_core(site_root, file_map[decl_name], 'html'), decl_name, text, tooltip)
  elif text != decl_name:
    return '<span title="{0}">{1}</span>'.format(decl_name, text)
  else:
    return text

def linkify(string, file_map):
  return linkify_core(string, string, file_map)

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

def linkify_markdown(string, loc_map):
  def linkify_type(string):
    splitstr = re.split(r'([\s\[\]\(\)\{\}])', string)
    tks = map(lambda s: linkify(s, loc_map), splitstr)
    return "".join(tks)

  string = re.sub(r'<code>([^<]+)</code>',
    lambda p: '<code>{}</code>'.format(linkify_type(p.group(1))), string)
  string = re.sub(r'<span class="n">([^<]+)</span>',
    lambda p: '<span class="n">{}</span>'.format(linkify_type(p.group(1))), string)
  return string

def link_to_decl(decl_name, loc_map):
  return filename_core(site_root, loc_map[decl_name], 'html') + '#' + decl_name

def kind_of_decl(decl):
  kind = 'structure' if len(decl['structure_fields']) > 0 else 'inductive' if len(decl['constructors']) > 0 else decl['kind']
  if kind == 'thm': kind = 'theorem'
  elif kind == 'cnst': kind = 'constant'
  elif kind == 'ax': kind = 'axiom'
  return kind
env.globals['kind_of_decl'] = kind_of_decl

# Inserts zero-width spaces after dots
def htmlify_name(n):
  # TODO: html escape
  return '.&#8203;'.join(n.split('.'))
env.filters['htmlify_name'] = htmlify_name

# returns (pagetitle, intro_block), [(tactic_name, tactic_block)]
def split_tactic_list(markdown):
  entries = re.findall(r'(?<=# )(.*)([\s\S]*?)(?=(##|\Z))', markdown)
  return entries[0], entries[1:]

def find_import_path(loc_map, decl_name):
  path = filename_import(loc_map[decl_name]) if decl_name in loc_map else ''
  if path.startswith('core.'):
    return path[5:]
  else:
    return path

def import_options(loc_map, decl_name, import_string):
  direct_import_path = find_import_path(loc_map, decl_name)
  direct_import_paths = []
  if direct_import_path != "":
    direct_import_paths.append(direct_import_path)
  if import_string != '' and import_string not in direct_import_paths:
    direct_import_paths.append(import_string)
  if any(i.startswith('init.') for i in direct_import_paths):
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul>'.format('<li>imported by default</li>')
  elif len(direct_import_paths) > 0:
    return '<details class="imports"><summary>Import using</summary><ul>{}</ul>'.format(
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

def write_pure_md_file(source, dest, name, loc_map):
  with open(source) as infile:
    body = convert_markdown(infile.read(), True)

  with open_outfile(dest) as out:
    out.write(env.get_template('pure_md.j2').render(
      active_path = '',
      name = name,
      body = body,
    ))

def mk_site_tree(partition):
  filenames = [ filename_core('', filename, 'html').split('/') for filename in partition ]
  return mk_site_tree_core(filenames)

def mk_site_tree_core(filenames, path=''):
  entries = []

  for dirname in sorted(set(dirname for dirname, *rest in filenames if rest != [])):
    new_path = dirname if path == '' else path+'/'+dirname
    entries.append({
      "kind": "dir",
      "name": dirname,
      "path": new_path,
      "children": mk_site_tree_core([rest for dn, *rest in filenames if rest != [] and dn == dirname], new_path)
    })

  for filename in sorted(filename for filename, *rest in filenames if rest == []):
    new_path = filename if path == '' else path+'/'+filename
    entries.append({
      "kind": "file",
      "name": filename[:-5],
      "path": new_path
    })

  return entries

def setup_jinja_globals(file_map, loc_map):
  env.globals['site_tree'] = mk_site_tree(file_map)
  env.globals['instances'] = instances
  env.globals['import_options'] = lambda d, i: import_options(loc_map, d, i)
  env.globals['find_import_path'] = lambda d: find_import_path(loc_map, d)
  env.filters['linkify'] = lambda x: linkify(x, loc_map)
  env.filters['linkify_efmt'] = lambda x: linkify_efmt(x, loc_map)
  env.filters['convert_markdown'] = lambda x: linkify_markdown(convert_markdown(x), loc_map) # TODO: this is probably very broken
  env.filters['link_to_decl'] = lambda x: link_to_decl(x, loc_map)

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
    md = mod_docs[filename] if filename in mod_docs else []
    with open_outfile(filename_core(html_root, filename, 'html')) as out:
      out.write(env.get_template('module.j2').render(
        active_path = filename_core('', filename, 'html'),
        filename = filename,
        items = sorted(md + decls, key = lambda d: d['line']),
        decl_names = sorted(d['name'] for d in decls),
      ))

  for (filename, displayname, source, _) in extra_doc_files:
    write_pure_md_file(local_lean_root + source, filename + '.html', displayname, loc_map)

def write_site_map(partition):
  with open_outfile('sitemap.txt') as out:
    for filename in partition:
      out.write(filename_core(site_root, filename, 'html') + '\n')
    for n in ['index', 'tactics', 'commands', 'hole_commands', 'notes']:
      out.write(site_root + n + '.html\n')
    for (filename, _, _, _) in extra_doc_files:
      out.write(site_root + filename + '.html\n')

def write_docs_redirect(decl_name, decl_loc):
  url = filename_core(site_root, decl_loc, 'html')
  with open_outfile('find/' + decl_name + '/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}#{quote(decl_name)}">')

def write_src_redirect(decl_name, decl_loc, file_map):
  url = library_link_from_decl_name(decl_name, decl_loc, file_map)
  with open_outfile('find/' + decl_name + '/src/index.html') as out:
    out.write(f'<meta http-equiv="refresh" content="0;url={url}">')

def write_redirects(loc_map, file_map):
  for decl_name in loc_map:
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

def copy_yaml_files(path):
  for fn in ['100.yaml', 'undergrad.yaml', 'overview.yaml']:
    shutil.copyfile(f'{local_lean_root}docs/{fn}', path+fn)

def write_decl_txt(loc_map):
  with open_outfile('decl.txt') as out:
    out.write('\n'.join(loc_map.keys()))

def mk_export_map_entry(decl_name, filename, kind, is_meta, line, args, tp):
  return {'filename': filename,
          'kind': kind,
          'is_meta': is_meta,
          'line': line,
          # 'args': args,
          # 'type': tp,
          'src_link': library_link(filename, line),
          'docs_link': filename_core(site_root, filename, 'html') + f'#{decl_name}'}

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

if __name__ == '__main__':
  file_map, loc_map, notes, mod_docs, instances, tactic_docs = load_json()
  setup_jinja_globals(file_map, loc_map)
  write_decl_txt(loc_map)
  write_html_files(file_map, loc_map, notes, mod_docs, instances, tactic_docs)
  write_redirects(loc_map, file_map)
  copy_css(html_root, use_symlinks=cl_args.l)
  copy_yaml_files(html_root)
  write_export_db(mk_export_db(loc_map, file_map))
  write_site_map(file_map)
