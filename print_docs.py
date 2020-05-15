#!/usr/bin/env/python3

# Requires the `markdown2` and `toml` packages:
#   `pip install markdown2 toml`
#
# This script is not Windows friendly.
#

import json
import os
import glob
import textwrap
import markdown2
import re
import subprocess
import toml
import shutil
import argparse
import html

root = os.getcwd()

parser = argparse.ArgumentParser('Options to print_docs.py')
parser.add_argument('-w', help = 'Generate docs for web. (Default local)', action = "store_true")
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
                   ('well_founded_recursion', 'well founded recursion', 'docs/extras/well_founded_recursion.md','extras/well_founded_recursion')]

# path to put generated html
html_root = root + '/' + (cl_args.t if cl_args.t else 'html/')

# TODO: make sure nothing is left in html_root

# root of the site, for display purposes.
# for local testing, use `html_root` or the address of a local server.
# override this setting with the `-w` flag.
site_root = "http://localhost:8000/"

# web root, used in place of `site_root` if the `-w` flag is used
web_root = "https://leanprover-community.github.io/mathlib_docs/"

# root directory of mathlib.
local_lean_root = root + '/' + (cl_args.r if cl_args.r else '_target/deps/mathlib/')



mathlib_commit = 'lean-3.4.2' # default
mathlib_github_root = 'https://github.com/leanprover-community/mathlib' # default
with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
  f.close()
  ml_data = parsed_toml['dependencies']['mathlib']
  mathlib_commit = ml_data['rev'][:7]
  mathlib_github_root = ml_data['git'].strip('/')
  if cl_args.w:
    site_root = web_root

mathlib_github_src_root = "{0}/blob/{1}/src/".format(mathlib_github_root, mathlib_commit)

lean_commit = subprocess.check_output(['lean', '--run', 'src/lean_commit.lean']).decode()[:7]
lean_root = 'https://github.com/leanprover-community/lean/blob/{}/library/'.format(lean_commit)

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

def library_link(filename, line=None):
  root = lean_root + filename.split('lean/library/', 1)[1] \
           if 'lean/library' in filename \
           else mathlib_github_src_root + filename.split('mathlib/src/', 1)[1]
  return root + ('#L' + str(line) if line is not None else '')

def nav_link(filename):
  tks = filename_core('', filename, '').split('/')
  links = ['<a href="{0}index.html">root</a>'.format(site_root)]
  for i in range(len(tks)-1):
    links.append('<a href="{2}{0}/index.html">{1}</a>'.format('/'.join(tks[:i+1]), tks[i], site_root))
  return '/<br>'.join(links) + '/<br><a href="{0}.html">{0}</a>'.format(tks[-1][:-1])

def index_nav_link(path):
  tks = path[len(html_root):].split('/')
  links = ['<a href="{0}/index.html">root</a>'.format(site_root)]
  for i in range(len(tks)):
    links.append('<a href="{2}{0}/index.html">{1}</a>'.format('/'.join(tks[:i+1]), tks[i], site_root))
  return '/<br>'.join(links)

def open_outfile(filename, mode):
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
    for (cstr_name, _) in obj['constructors']:
      loc_map[cstr_name] = obj['filename']
    for (sf_name, _) in obj['structure_fields']:
      loc_map[sf_name] = obj['filename']
    if len(obj['structure_fields']) > 0:
      loc_map[obj['name'] + '.mk'] = obj['filename']
  return (file_map, loc_map)

def load_json():
  f = open('json_export.txt', 'r', encoding='utf-8')
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

def linkify_type(string, loc_map):
  splitstr = re.split(r'([\s\[\]\(\)\{\}])', string)
  tks = map(lambda s: linkify(s, loc_map), splitstr)
  return "".join(tks)

def linkify_linked(string, loc_map):
  return ''.join(
    match[4] if match[0] == '' else
    match[1] + linkify_core(match[0], match[2], loc_map) + match[3]
    for match in re.findall(r'\ue000(.+?)\ue001(\s*)(.*?)(\s*)\ue002|([^\ue000]+)', string))

def linkify_markdown(string, loc_map):
  return re.sub(r'<code>([\s\S]*?)<\/code>', lambda p: linkify_type(p.group(), loc_map), string)

def write_decl_html(obj, loc_map, instances, out):
  doc_string = markdown2.markdown(obj['doc_string'], extras=["code-friendly", 'cuddled-lists', 'fenced-code-blocks', 'link-patterns'], link_patterns = link_patterns)

  kind = 'structure' if len(obj['structure_fields']) > 0 else 'inductive' if len(obj['constructors']) > 0 else obj['kind']
  if kind == 'thm': kind = 'theorem'
  elif kind == 'cnst': kind = 'constant'
  elif kind == 'ax': kind = 'axiom'

  is_meta = '<span class="decl_meta">meta</span>' if obj['is_meta'] else ''
  attr_string = '<div class="attributes">@[' + ', '.join(obj['attributes']) + ']</div>' if len(obj['attributes']) > 0 else ''
  name = '<a href="{0}#{1}">{2}</a>'.format(filename_core(site_root, obj['filename'], 'html'), obj['name'], obj['name'])
  args = []
  for s in obj['args']:
    arg = '<span class="decl_args">{}</span>'.format(linkify_linked(s['arg'], loc_map))
    if s['implicit']: arg = '<span class="impl_arg">{}</span>'.format(arg)
    args.append(arg)
  args = ' '.join(args)
  type = linkify_linked(obj['type'], loc_map)
  decl_code = '{attr_string} \
    <div class="decl_header impl_collapsed"> \
      {is_meta} <span class="decl_kind">{kind}</span> \
      <span class="decl_name">{name}</span> {args} <span class="decl_args">:</span> \
    <div class="decl_type">{type}</div></div>\n'.format(
      name = name,
      is_meta = is_meta,
      kind = kind,
      attr_string = attr_string,
      args = args,
      type = type,
    )

  eqns = ['<li class="equation">{}</li>'.format(linkify_linked(eqn, loc_map)) for eqn in obj['equations']]
  eqns = '<details><summary>Equations</summary><ul class="equations">{}</ul></details>'.format(''.join(eqns)) if len(eqns) > 0 else ''

  sf = ['<li class="structure_field" id="{2}.{0}">{0} : {1}</li>'.format(name.split('.')[-1], linkify_linked(tp, loc_map), obj['name']) for (name, tp) in obj['structure_fields']]
  sfs = '<ul class="structure_fields" id="{1}.mk">\n{0}\n</ul>'.format('\n'.join(sf), obj['name']) if len(sf) > 0 else ''

  cstr = ['<li class="constructor" id="{2}.{0}">{0} : {1}</li>'.format(name.split('.')[-1], linkify_linked(tp, loc_map), obj['name']) for (name, tp) in obj['constructors']]
  cstrs = '<ul class="constructors">\n{}\n</ul>'.format('\n'.join(cstr)) if len(cstr) > 0 else ''

  if obj['name'] in instances:
    insts = instances[obj['name']]
    insts = ['<li>{}</li>'.format(linkify_type(n, loc_map)) for n in insts]
    inst_string = '<details class="instances"><summary>Instances</summary><ul>{}</ul></details>'.format('\n'.join(insts))
  else:
    inst_string = ''

  gh_link = '<div class="gh_link"><a href="{0}">view source</a></div>'.format(library_link(obj['filename'], obj['line']))

  out.write('<div class="decl {kind}" id="{raw_name}">{gh_link} {decl_code} {sfs} {cstrs} {doc_string} {eqns} {inst_string}</ul></div>'.format(
      decl_code = decl_code,
      raw_name = obj['name'],
      doc_string = doc_string,
      kind = kind,
      eqns = eqns,
      sfs = sfs,
      cstrs = cstrs,
      inst_string = inst_string,
      gh_link = gh_link
  ))

search_snippet = """
<script async src="https://cse.google.com/cse.js?cx=013315010647789779870:7aikx0zd1z9"></script>
<div class="gcse-search"></div>
"""

def write_internal_nav(objs, filename, out):
  out.write('<h1>Lean <a href="https://leanprover-community.github.io">mathlib</a> docs</h1>')
  out.write('<h2><a href="#top">{0}</a></h2>'.format(filename_import(filename)))
  out.write('<div class="gh_nav_link"><a href="{}">View source</a></div>'.format(library_link(filename)))
  for o in sorted([o['name'] for o in objs]):
    out.write('<a href="#{0}">{0}</a><br>\n'.format(o))

def write_notes_nav(notes, out):
  out.write('<h1>Lean <a href="https://leanprover-community.github.io">mathlib</a> docs</h1>')
  out.write('<h2><a href="#top">Library notes</a></h2>')
  for o in sorted([o[0] for o in notes]):
    out.write('<a href="#{0}">{0}</a><br>\n'.format(o))

def write_mod_doc(obj, loc_map, out):
  doc = linkify_markdown(convert_markdown(obj['doc']), loc_map)
  out.write('<div class="mod_doc">\n' + doc + '</div>')


def write_body_content(objs, loc_map, filename, mod_docs, instances, body_out):
  body_out.write('<a id="top"></a>')
  for o in sorted(objs + mod_docs, key = lambda d: d['line']):
    if 'name' in o:
      write_decl_html(o, loc_map, instances, body_out)
    else:
      write_mod_doc(o, loc_map, body_out)

# MathJax configuration docs:
#   http://docs.mathjax.org/en/latest/options/document.html#the-configuration-block
# MathJax inlineMath/displayMath docs:
#   http://docs.mathjax.org/en/latest/options/input/tex.html#tex-extension-options
# StackOverflow link on why to avoid \(..\) and \[..\] when markdown is in the loop:
#   https://math.meta.stackexchange.com/a/18714
def html_head(title):
  return """<!DOCTYPE html>
<html lang="en">
    <head>
        <link rel="stylesheet" href="{0}style_js_frame.css">
        <link rel="shortcut icon" href="https://leanprover-community.github.io/assets/img/lean.ico">
        <title>mathlib docs: {1}</title>
        <meta charset="UTF-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script>
        MathJax = {{
          tex: {{
            inlineMath: [['$', '$']],
            displayMath: [['$$', '$$']]
          }},
          options: {{
              skipHtmlTags: [
                  'script', 'noscript', 'style', 'textarea', 'pre',
                  'code', 'annotation', 'annotation-xml',
                  'decl', 'decl_meta', 'attributes', 'decl_args', 'decl_header', 'decl_name',
                  'decl_type', 'equation', 'equations', 'structure_field', 'structure_fields',
                  'constructor', 'constructors', 'instances'
              ],
              ignoreHtmlClass: 'tex2jax_ignore',
              processHtmlClass: 'tex2jax_process',
          }},
        }};
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    </head>
    <body>
        <div class="row">""".format(site_root, title)

html_tail = """
        </div>
    </body>
    <script src="{0}nav.js"></script>
</html>
""".format(site_root)

def is_displayable_html(name):
    fn, ext = os.path.splitext(name)
    return fn != 'index' and ext in ['.html', '.lean']

def add_to_dir_tree(lst):
  dct, fil = {}, []
  for l in lst:
    if len(l) == 0:
      pass
    elif len(l) == 1:
      fil.append(l[0])
    elif l[0] in dct:
      dct[l[0]].append(l[1:])
    else:
      dct[l[0]] = [l[1:]]
  dct2 = {}
  for key in dct:
    dct2[key] = add_to_dir_tree(dct[key])
  return {'dirs':dct2, 'files':fil}

def print_dir_tree(path, active_path, tree):
  s = ''
  for name in sorted(tree['dirs'].keys()):
    new_path = os.path.join(path, name)
    s += '<div class="nav_sect">{0}</div>\n'.format(name)
    s += '<div class="nav_sect_inner{1}" id="{0}">\n'.format(new_path, '' if active_path.startswith(new_path + '/') else ' hidden')
    s += print_dir_tree(new_path, active_path, tree['dirs'][name])
    s += '\n</div>'
  for name in sorted(tree['files']):
    p = os.path.join(path, name)
    s += '<a class="nav_file{3}" id="{0}" href="{2}{0}">{1}</a><br>\n'.format(
          p,
          name[:-5],
          site_root,
          ' visible' if p == active_path else ''
      )
  s += '\n'
  return s

def content_nav(dir_list, active_path):
  s = '<div class="search">{}</div>\n'.format(search_snippet)
  s += '<h3>General documentation</h3>'
  s += '<a href="{0}">index</a><br>\n'.format(site_root)
  s += '<a href="{0}tactics.html">tactics</a><br>\n'.format(site_root)
  s += '<a href="{0}commands.html">commands</a><br>\n'.format(site_root)
  s += '<a href="{0}hole_commands.html">hole commands</a><br>\n'.format(site_root)
  s += '<a href="{0}attributes.html">attributes</a><br>\n'.format(site_root)
  s += '<a href="{0}notes.html">notes</a><br>\n'.format(site_root)
  s += '<h3>Tutorials</h3>'
  for (filename, displayname, _, community_site_url) in extra_doc_files:
    s += '<a href="https://leanprover-community.github.io/{0}.html">{1}</a><br>\n'.format(community_site_url, displayname)
  s += '<h3>Library</h3>'
  s += print_dir_tree('', active_path, dir_list)
  return s

def write_html_file(content_nav_str, objs, loc_map, filename, mod_docs, instances, out):
  out.write(html_head(filename_import(filename)))
  out.write('<div class="column left"><div class="internal_nav">\n' )
  write_internal_nav(objs, filename, out)
  out.write('</div></div>\n')
  out.write('<div class="column middle"><div class="content">\n')
  write_body_content(objs, loc_map, filename, mod_docs, instances, out)
  out.write('\n</div></div>\n')
  out.write('<div class="column right"><div class="nav">\n')
  out.write(content_nav_str)
  out.write('\n</div></div>\n')
  out.write(html_tail)

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

def escape_tag_name(tag):
  return tag.strip().replace(' ', '-')

# entries has the structure:
# [{name: "", category: "", decl_names: [], tags: [], description: "", import: ""}]
def write_tactic_doc_file(intro, entries, name, loc_map, dir_list):
  entries.sort(key = lambda p: (str.lower(p['name']), str.lower(p['category'])))
  out = open_outfile(html_root + name + '.html', 'w')
  out.write(html_head(name))
  out.write('<div class="column left"><div class="internal_nav">\n' )
  out.write('<h1>Lean <a href="https://leanprover-community.github.io">mathlib</a> docs</h1>')
  out.write('<h2><a href="#top">{0}</a></h2>'.format(name))
  tagset = set()
  for e in entries:
    tagset.update(e['tags'])
  out.write('\n<details class="tagfilter-div">\n<summary>Filter by tag</summary>\n')
  out.write('<label><input type="checkbox" id="tagfilter-selectall" name="tagfilter-selectall">Select/deselect all</label><br><hr>\n')
  for t in sorted(tagset):
    out.write('<label><input type="checkbox" class="tagfilter" name="{1}" value="{1}">{0}</label><br>\n'.format(t, escape_tag_name(t)))
  out.write('</details><br>\n')
  for e in entries:
    out.write('<div class="taclink {1}"><a href="#{0}">{0}</a></div>\n'.format(e['name'], ' '.join([escape_tag_name(t) for t in e['tags']])))
  out.write('</div></div>\n')
  out.write('<div class="column middle"><div class="content docfile">\n')
  out.write('<h1>{0}</h1>\n\n{1}'.format(intro['title'], convert_markdown(intro['body'])))
  for e in entries:
    out.write('<div class="tactic {}">\n'.format(' '.join([escape_tag_name(t) for t in e['tags']])))
    out.write('<h2 id="{0}"><a href="#{0}">{0}</a></h2>\n'.format(e['name']))
    out.write(convert_markdown(split_on_hr(e['description'])))
    if len(e['tags']) > 0:
      tags = ['<li>{}</li>'.format(t) for t in e['tags']]
      out.write('<div class="tags">Tags:<ul>{}</ul></div>'.format('\n'.join(tags)))
    if len(e['decl_names']) > 0:
      rel_decls = ['<li>{}</li>'.format(linkify_type(d, loc_map)) for d in e['decl_names']]
      decl_string = '<details class="rel_decls"><summary>Related declarations</summary><ul>{}</ul></details>'.format('\n'.join(rel_decls))
      out.write(decl_string)
      out.write(import_options(loc_map, e['decl_names'][0], e['import']))
    out.write('</div>\n')
  out.write('\n</div></div>\n')
  out.write('<div class="column right"><div class="nav">\n')
  out.write(content_nav(dir_list, 'index.html'))
  out.write('\n</div></div>\n')
  out.write(html_tail)
  out.close()

def write_pure_md_file(source, dest, name, loc_map, dir_list):
  with open(source, 'r') as infile:
    body = convert_markdown(infile.read(), True)
    infile.close()
  out = open_outfile(html_root + dest, 'w')
  out.write(html_head(name))
  out.write('<div class="column left"><div class="internal_nav">\n' )
  out.write('<h1>Lean <a href="https://leanprover-community.github.io">mathlib</a> docs</h1>')
  out.write('<h2><a href="#top">{0}</a></h2>'.format(name))
  out.write(body.toc_html)
  out.write('</div></div>\n')
  out.write('<div class="column middle"><div class="content">\n')
  out.write(body)
  out.write('\n</div></div>\n')
  out.write('<div class="column right"><div class="nav">\n')
  out.write(content_nav(dir_list, 'index.html'))
  out.write('\n</div></div>\n')
  out.write(html_tail)
  out.close()




index_body = """
<h1>Lean mathlib documentation</h1>

{4}

<p>Navigate through mathlib files using the menu on the right.</p>

<p>Declaration names link to their locations in the mathlib or core Lean source.
Names inside code snippets link to their locations in this documentation.</p>

<p>This documentation has been generated with mathlib commit
<a href="{1}/tree/{0}">{0}</a> and Lean commit <a href="{2}">{3}</a>.</p>

<p>Note: mathlib is still only partially documented, and this HTML display is still
under development. We welcome pull requests on <a href="{1}">GitHub</a> to update misleading or
badly formatted doc strings, or to add missing documentation.</p>
""".format(mathlib_commit, mathlib_github_root, lean_root, lean_commit, search_snippet)

notes_body = """
<a id="top"></a>
<h1>Lean mathlib notes</h1>

<p>Various implementation details are noted in the mathlib source, and referenced later on.
We collect these notes here.</p>
"""

def write_note(n, loc_map, out):
  note_id, note_body = n[0], linkify_markdown(convert_markdown(n[1]), loc_map)
  out.write('<div class="note" id="{}">'.format(note_id))
  out.write('<h2>{}</h2>'.format(note_id))
  out.write(note_body)
  out.write('</div>')

def write_note_file(notes, loc_map, dir_list):
  out = open_outfile(html_root + 'notes.html', 'w')
  out.write(html_head('notes'))
  out.write('<div class="column left"><div class="internal_nav">\n' )
  write_notes_nav(notes, out)
  out.write('</div></div>\n')
  out.write('<div class="column middle"><div class="content">\n')
  out.write(notes_body)
  for n in notes:
    write_note(n, loc_map, out)
  out.write('\n</div></div>\n')
  out.write('<div class="column right"><div class="nav">\n')
  out.write(content_nav(dir_list, 'index.html'))
  out.write('\n</div></div>\n')
  out.write(html_tail)
  out.close()

tactic_doc_intros = {
  'tactic': {'title': 'Mathlib tactics',
             'body':
             """In addition to the [tactics found in the core library](https://leanprover.github.io/reference/tactics.html),
mathlib provides a number of specific interactive tactics.
Here we document the mostly commonly used ones, as well as some underdocumented tactics from core."""},
  'command': {'title': 'Commands',
               'body':
               """Commands provide a way to interact with and modify a Lean environment outside of the context of a proof.
Familiar commands from core Lean include `#check`, `#eval`, and `run_cmd`.

Mathlib provides a number of commands that offer customized behavior. These commands fall into two
categories:

* *Transient* commands are used to query the environment for information, but do not modify it,
  and have no effect on the following proofs. These are useful as a user to get information from Lean.
  They should not appear in "finished" files.
  Transient commands typically begin with the symbol `#`.
  `#check` is a standard example of a transient command.

* *Permanent* commands modify the environment. Removing a permanent command from a file may affect
  the following proofs. `set_option class.instance_max_depth 500` is a standard example of a
  permanent command.

User-defined commands can have unintuitive interactions with the parser. For the most part, this is
not something to worry about. However, you may occasionally see strange error messages when using
mathlib commands: for instance, running these commands immediately after `import file.name` will
produce an error. An easy solution is to run a built-in no-op command in between, for example:

```
import data.nat.basic

run_cmd tactic.skip -- this serves as a "barrier" between `import` and `#find`

#find _ + _ = _ + _
```"""},
  'hole_command': {'title': 'Hole commands',
               'body':"""Both VS Code and emacs support integration for 'hole commands'.

In VS Code, if you enter `{! !}`, a small light bulb symbol will appear, and
clicking on it gives a drop down menu of available hole commands. Running one
of these will replace the `{! !}` with whatever text that hole command provides.

In emacs, you can do something similar with `C-c SPC`.

Many of these commands are available whenever `tactic.core` is imported.
Commands that require additional imports are noted below.
All should be available with `import tactic`."""},
  'attribute': {'title': 'Attributes',
               'body':"""
*Attributes* are a tool for associating information with declarations.

In the simplest case, an attribute is a tag that can be applied to a declaration.
`simp` is a common example of this. A lemma
```lean
@[simp] lemma foo : ...
```
has been tagged with the `simp` attribute.
When the simplifier runs, it will collect all lemmas that have been tagged with this attribute.

More complicated attributes take *parameters*. An example of this is the `nolint` attribute.
It takes a list of linter names when it is applied, and for each declaration tagged with `@[nolint linter_1 linter_2]`,
this list can be accessed by a metaprogram.

Attributes can also be applied to declarations with the syntax:
```lean
attribute [attr_name] decl_name_1 decl_name_2 decl_name 3
```

The core API for creating and using attributes can be found in
[core.init.meta.attribute](core/init/meta/attribute.html).
"""}
}

def write_tactic_doc_files(local_lean_root, entries, loc_map, dir_list):
  kinds = [('tactic', 'tactics'), ('command', 'commands'), ('hole_command', 'hole_commands'), ('attribute', 'attributes')]
  for (kind, filename) in kinds:
    restr_entries = [e for e in entries if e['category'] == kind]
    write_tactic_doc_file(tactic_doc_intros[kind], restr_entries, filename, loc_map, dir_list)

def write_html_files(partition, loc_map, notes, mod_docs, instances, entries):
  dir_list = add_to_dir_tree([filename_core('', filename, 'html').split('/') for filename in partition])
  for filename in partition:
    content_nav_str = content_nav(dir_list, filename_core('', filename, 'html'))
    body_out = open_outfile(filename_core(html_root, filename, 'html'), 'w')
    md = mod_docs[filename] if filename in mod_docs else []
    write_html_file(content_nav_str, partition[filename], loc_map, filename, md, instances, body_out)
    body_out.close()
  out = open_outfile(html_root + 'index.html', 'w')
  out.write(html_head('index'))
  out.write('<div class="column left"><div class="internal_nav">\n' )
  out.write('</div></div>\n')
  out.write('<div class="column middle"><div class="content">\n')
  out.write(index_body)
  out.write('\n</div></div>\n')
  out.write('<div class="column right"><div class="nav">\n')
  out.write(content_nav(dir_list, 'index.html'))
  out.write('\n</div></div>\n')
  out.write(html_tail)
  out.close()
  write_note_file(notes, loc_map, dir_list)
  #write_tactic_doc_file(local_lean_root + 'docs/tactics.md', 'tactics', loc_map, dir_list)
  #write_tactic_doc_file(local_lean_root + 'docs/commands.md', 'commands', loc_map, dir_list)
  #write_tactic_doc_file(local_lean_root + 'docs/holes.md', 'hole_commands', loc_map, dir_list)
  write_tactic_doc_files(local_lean_root, entries, loc_map, dir_list)
  for (filename, displayname, source, _) in extra_doc_files:
    write_pure_md_file(local_lean_root + source, filename + '.html', displayname, loc_map, dir_list)

def write_site_map(partition):
  out = open_outfile(html_root + 'sitemap.txt', 'w')
  for filename in partition:
    out.write(filename_core(site_root, filename, 'html') + '\n')
  for n in ['index', 'tactics', 'commands', 'hole_commands', 'notes']:
    out.write(site_root + n + '.html\n')
  for (filename, _, _, _) in extra_doc_files:
    out.write(site_root + filename + '.html\n')
  out.close()

def copy_css(path, use_symlinks):
  def cp(a, b):
    if use_symlinks:
      os.remove(b)
      os.symlink(os.path.relpath(a, os.path.dirname(b)), b)
    else:
      shutil.copyfile(a, b)

  cp('style_js_frame.css', path+'style_js_frame.css')
  cp('nav.js', path+'nav.js')

file_map, loc_map, notes, mod_docs, instances, tactic_docs = load_json()
write_html_files(file_map, loc_map, notes, mod_docs, instances, tactic_docs)
copy_css(html_root, use_symlinks=cl_args.l)
write_site_map(file_map)
