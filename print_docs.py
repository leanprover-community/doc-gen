#!/usr/bin/env/python3

# requires `pip install markdown2` and `pip install toml`
# this script is not Windows friendly.
#

import json
import os
import textwrap
import markdown2
import re
import subprocess
import toml
import shutil

# path to put generated html
html_root = "/home/rob/lean/doc_gen/html/"

# root of the site, for display purposes. use `html_root` for local testing.
#site_root = "https://robertylewis.com/mathlib_docs/"
site_root = "/home/rob/lean/doc_gen/html/"

# src directory of mathlib. used to scrape module docs.
# The files here should match the ones used to generate json_export.txt.
# All files should be committed in git, and HEAD should be a commit that exists
# on https://github.com/leanprover-community/mathlib .
local_lean_root = os.getcwd() + '/_target/deps/mathlib/src/' #"/home/rob/lean/mathlib/src/"

mathlib_commit = 'lean-3.4.2' # default
mathlib_github_root = "https://github.com/leanprover-community/mathlib" # default
with open('leanpkg.toml') as f:
  parsed_toml = toml.loads(f.read())
  ml_data = parsed_toml['dependencies']['mathlib']
  mathlib_commit = ml_data['rev']
  mathlib_github_root = ml_data['git'].strip('/')
  f.close()

mathlib_github_src_root = "{0}/blob/{1}/src/".format(mathlib_github_root, mathlib_commit)

lean_commit = subprocess.check_output(['lean', '--run', 'lean_commit.lean']).decode()
lean_root = "https://github.com/leanprover-community/lean/blob/{}/library/".format(lean_commit)

def convert_markdown(ds):
  return markdown2.markdown(ds, extras=['code-friendly', 'cuddled-lists'])

def filename_core(root, filename, ext):
  if 'lean/library' in filename:
    return root + 'core/' + filename.split('lean/library/', 1)[1][:-4] + ext
  elif 'mathlib/src' in filename:
    return root + filename.split('mathlib/src/', 1)[1][:-4] + ext
  else:
    return root + filename.split('mathlib/scripts/', 1)[1][:-4] + ext

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
  module_docs = []
  file_map, loc_map = separate_results(decls)
  return file_map, loc_map, module_docs

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

def write_decl_html(obj, loc_map, out):
  doc_string = markdown2.markdown(obj['doc_string'], extras=["code-friendly"])
  type = linkify_type(obj['type'], loc_map)
  args = [linkify_type(s, loc_map) for s in obj['args']]
  args = ['<span class="decl_args">{}</span>'.format(s) for s in args]
  args = ' '.join(args)
  sf = ['<div class="structure_field">{0} : {1}</div>'.format(name, linkify_type(tp, loc_map)) for (name, tp) in obj['structure_fields']]
  sfs = '<div class="structure_fields">\nFields:\n{}\n</div>'.format('\n'.join(sf)) if len(sf) > 0 else ''
  cstr = ['<div class="structure_field">{0} : {1}</div>'.format(name, linkify_type(tp, loc_map)) for (name, tp) in obj['constructors']]
  cstrs = '<div class="structure_fields">\nConstructors:\n{}\n</div>'.format('\n'.join(cstr)) if len(cstr) > 0 else ''
  kind = 'structure' if len(sf) > 0 else 'inductive' if len(cstrs) > 0 else obj['kind']
  name = '<a href="{0}">{1}</a>'.format(library_link(obj['filename'], obj['line']), obj['name'])
  attr_string = 'Attributes: ' + ', '.join(obj['attributes']) if len(obj['attributes']) > 0 else ''
  out.write(
    '<div class="{4}"><a id="{0}"></a>\
      <span class="decl_name">{6}</span> {5} <span class="decl_args">:</span> \
      <div class="decl_type">{1}</div>\n<div class="indent">{2} \
      {7}\n{8}\n{3}</div>\n</div>'.format(
      obj['name'], type, doc_string, attr_string, kind, args, name, sfs, cstrs)
  )

def get_doc_string(path):
  try:
    with open(path, 'r', encoding = 'utf-8') as inf:
      text = inf.read()
      inf.close()
      result = re.search(r'\/\-\!([\s\S]*?)\-\/', text)
      return result.group(1)
  except:
    return ''

def write_html_file(objs, loc_map, filename, out):
  path = filename_core('', filename, '')[:-1].replace('/', '.')
  file_source = library_link(filename)
  out.write('<!DOCTYPE html><html lang="en"><head><title>{1}</title><meta charset="UTF-8"><link rel="stylesheet" href="{0}style.css"></head><body>'.format(site_root, path))
  out.write('<div class="nav"><div class="title">mathlib API docs</div>{0}\
      <br><br><a href="{1}">View file source</a></div>'.format(nav_link(filename), file_source))
  ds = get_doc_string(filename_core(local_lean_root, filename, 'lean'))
  module_doc = linkify_markdown(convert_markdown(ds), loc_map)
  out.write('<div class="mod_doc">' + module_doc + '</div>')
  for o in sorted(objs, key = lambda d: d['line']):
    write_decl_html(o, loc_map, out)
  out.write('</body></html>')

def write_html_files(partition, loc_map):
  for filename in partition:
    f = open_outfile(filename_core(html_root, filename, 'html'), 'w')
    write_html_file(partition[filename], loc_map, filename, f)
    f.close()

def is_displayable_html(name):
  fn, ext = os.path.splitext(name)
  return fn != 'index' and ext == '.html'

def write_html_indices(path):
  out = open_outfile(path + "/index.html", 'w')
  out.write('<html><head><title>{1}</title><link rel="stylesheet" href="{0}style.css"></head><body>\
    <div class="nav"><div class="title">mathlib API docs</div>{2}</div><div class="index_body"><ul>'.format(site_root, path, index_nav_link(path)))
  lst = os.listdir(path)
  files, dirs = [], []
  for name in lst:
    f = os.path.join(path, name)
    if os.path.isdir(f):
      dirs.append(name)
      write_html_indices(f)
    else:
      files.append(name)
  for name in sorted(dirs):
    out.write('<li><a href="{0}/index.html" class="index">{0}</a></li>\n'.format(name))
  for name in filter(is_displayable_html, sorted(files)):
    out.write('<li><a href="{0}" class="file">{0}</a></li>\n'.format(name))
  out.write('</ul></div></body></html>')
  out.close()

def copy_css(path):
  shutil.copyfile('style.css', path+'style.css')

file_map, loc_map, _ = load_json()
write_html_files(file_map, loc_map)
write_html_indices(html_root)
copy_css(html_root)
