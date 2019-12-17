#!/usr/bin/env/python3

# Requires the `markdown2` and `toml` packages:
#   `pip install markdown2 toml`
#
# This script is not Windows friendly.
#

import json
import os
import textwrap
import markdown2
import re
import subprocess
import toml
import shutil
import argparse

root = os.getcwd()

# path to put generated html
html_root = root + '/html/'

# root of the site, for display purposes.
# for local testing, use `html_root` or the address of a local server.
# override this setting with the `-w` flag.
site_root = "http://localhost:8000/"

# web root, used in place of `site_root` if the `-w` flag is used
web_root = "https://leanprover-community.github.io/mathlib_docs/"

# src directory of mathlib. used to scrape module docs.
# The files here should match the ones used to generate json_export.txt.
local_lean_root = root + '/_target/deps/mathlib/src/'

parser = argparse.ArgumentParser('Options to print_docs.py')
parser.add_argument('-w', help = 'Generate docs for web. (Default local)', action = "store_true")
parser.add_argument('-l', help = 'Symlink CSS and JS instead of copying', action = "store_true")
cl_args = parser.parse_args()

mathlib_commit = 'lean-3.4.2' # default
mathlib_github_root = 'https://github.com/leanprover-community/mathlib' # default
with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
  f.close()
  ml_data = parsed_toml['dependencies']['mathlib']
  mathlib_commit = ml_data['rev']
  mathlib_github_root = ml_data['git'].strip('/')
  if cl_args.w:
    site_root = web_root

mathlib_github_src_root = "{0}/blob/{1}/src/".format(mathlib_github_root, mathlib_commit)

lean_commit = subprocess.check_output(['lean', '--run', 'src/lean_commit.lean']).decode()
lean_root = 'https://github.com/leanprover-community/lean/blob/{}/library/'.format(lean_commit)

def convert_markdown(ds):
  return markdown2.markdown(ds, extras=['code-friendly', 'cuddled-lists', 'fenced-code-blocks'])

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
  return (file_map, loc_map)

def load_json():
  f = open('json_export.txt', 'r', encoding='utf-8')
  decls = json.load(f, strict=False)
  f.close()
  file_map, loc_map = separate_results(decls['decls'])
  return file_map, loc_map, decls['mod_docs'], decls['instances']

def linkify(string, file_map):
  if string in file_map:
    return '<a href="{0}#{1}">{1}</a>'.format(filename_core(site_root, file_map[string], 'html'), string)
  else:
    return string

def linkify_type(string, loc_map):
  splitstr = re.split(r'([\s\[\]\(\)\{\}])', string)
  tks = map(lambda s: linkify(s, loc_map), splitstr)
  return "".join(tks)

def linkify_markdown(string, loc_map):
  return re.sub(r'<code>([\s\S]*?)<\/code>', lambda p: linkify_type(p.group(), loc_map), string)

def write_decl_html(obj, loc_map, instances, out):
  doc_string = markdown2.markdown(obj['doc_string'], extras=["code-friendly", 'cuddled-lists', 'fenced-code-blocks'])

  kind = 'structure' if len(obj['structure_fields']) > 0 else 'inductive' if len(obj['constructors']) > 0 else obj['kind']
  if kind == 'thm': kind = 'theorem'
  elif kind == 'cnst': kind = 'constant'
  elif kind == 'ax': kind = 'axiom'

  is_meta = '<span class="decl_meta">meta</span>' if obj['is_meta'] else ''
  attr_string = '<div class="attributes">@[' + ', '.join(obj['attributes']) + ']</div>' if len(obj['attributes']) > 0 else ''
  name = '<a href="{0}">{1}</a>'.format(library_link(obj['filename'], obj['line']), obj['name'])
  args = []
  for s in obj['args']:
    arg = '<span class="decl_args">{}</span>'.format(linkify_type(s['arg'], loc_map))
    if s['implicit']: arg = '<span class="impl_arg">{}</span>'.format(arg)
    args.append(arg)
  args = ' '.join(args)
  type = linkify_type(obj['type'], loc_map)
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

  sf = ['<li class="structure_field">{0} : {1}</li>'.format(name.split('.')[-1], linkify_type(tp, loc_map)) for (name, tp) in obj['structure_fields']]
  sfs = '<ul class="structure_fields">\n{}\n</ul>'.format('\n'.join(sf)) if len(sf) > 0 else ''

  cstr = ['<li class="constructor">{0} : {1}</li>'.format(name.split('.')[-1], linkify_type(tp, loc_map)) for (name, tp) in obj['constructors']]
  cstrs = '<ul class="constructors">\n{}\n</ul>'.format('\n'.join(cstr)) if len(cstr) > 0 else ''

  if obj['name'] in instances:
    insts = instances[obj['name']]
    insts = ['<li>{}</li>'.format(linkify_type(n, loc_map)) for n in insts]
    inst_string = '<details class="instances"><summary>Instances</summary><ul>{}</ul></details>'.format('\n'.join(insts))
  else:
    inst_string = ''

  out.write('<div class="decl {kind}" id="{raw_name}">{decl_code} {sfs} {cstrs} {doc_string} {inst_string}</ul></div>'.format(
      decl_code = decl_code,
      raw_name = obj['name'],
      doc_string = doc_string,
      kind = kind,
      sfs = sfs,
      cstrs = cstrs,
      inst_string = inst_string,
  ))

search_snippet = """
<script async src="https://cse.google.com/cse.js?cx=013315010647789779870:7aikx0zd1z9"></script>
<div class="gcse-search"></div>
"""

def write_internal_nav(objs, filename, out):
  out.write('<h1>Lean <a href="https://leanprover-community.github.io">mathlib</a> docs</h1>')
  out.write('<h2><a href="#top">{0}</a></h2>'.format(filename_import(filename)))
  out.write('<div class="gh_link"><a href="{}">(view source on GitHub)</a></div>'.format(library_link(filename)))
  for o in sorted([o['name'] for o in objs]):
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

def html_head(title):
  return """<!DOCTYPE html>
<html lang="en">
    <head>
        <link rel="stylesheet" href="{0}style_js_frame.css">
        <link rel="shortcut icon" href="https://leanprover-community.github.io/assets/img/lean.ico">
        <title>mathlib docs: {1}</title>
        <meta charset="UTF-8">
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
  s += '<a href="{0}">index</a><br><br>\n'.format(site_root)
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

index_body = """
<h1>Lean mathlib documentation</h1>

{4}

<p>Navigate through mathlib files using the menu on the right.</p>

<p>Declaration names link to their locations in the mathlib or core Lean source.
Names inside code snippets link to their locations in this documentation.</p>

<p>This documentation has been generated with mathlib commit
<a href="{1}/tree/{0}">{0}</a> and Lean 3.5c commit <a href="{2}">{3}</a>.</p>

<p>Note: mathlib is still only partially documented, and this HTML display is still
under development. We welcome pull requests on <a href="{1}">GitHub</a> to update misleading or
badly formatted doc strings, or to add missing documentation.</p>
""".format(mathlib_commit, mathlib_github_root, lean_root, lean_commit, search_snippet)

def write_html_files(partition, loc_map, mod_docs, instances):
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

def write_site_map(partition):
  out = open_outfile(html_root + 'sitemap.txt', 'w')
  for filename in partition:
    out.write(filename_core(site_root, filename, 'html') + '\n')
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

file_map, loc_map, mod_docs, instances = load_json()
write_html_files(file_map, loc_map, mod_docs, instances)
copy_css(html_root, use_symlinks=cl_args.l)
write_site_map(file_map)