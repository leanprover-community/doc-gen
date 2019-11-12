#!/usr/bin/env/python3

# requires `pip install markdown2`

import json
import os
import textwrap
import markdown2
import re

# path to put generated html
html_root = "/home/rob/lean/mathlib/scripts/html_out/"

# root of the site, for display purposes. use `html_root` for local testing.
#site_root = "https://robertylewis.com/mathlib_docs/"
site_root = "/home/rob/lean/mathlib/scripts/html_out/"

# src directory of mathlib. used to scrape module docs.
lean_root = "/home/rob/lean/mathlib/src/"

def filename_core(root, filename, ext):
  if 'lean/library' in filename:
    return root + 'core/' + filename.split('lean/library/', 1)[1][:-4] + ext
  elif 'mathlib/src' in filename:
    return root + filename.split('mathlib/src/', 1)[1][:-4] + ext
  else:
    return root + filename.split('mathlib/scripts/', 1)[1][:-4] + ext

def open_outfile(filename, mode):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    return open(filename, mode, encoding='utf-8')

def separate_results(objs):
  file_map = {}
  loc_map = {}
  for obj in objs:
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
  doc_string = markdown2.markdown(obj['doc_string'])
  type = linkify_type(obj['type'], loc_map)
  attr_string = 'Attributes: ' + ', '.join(obj['attributes']) if len(obj['attributes']) > 0 else ''
  out.write(
    '<div class="{4}"><a id="{0}"></a>\
      <h4>{0}</h4><code>{1}</code>\n<div class="indent">{2} \
      {3}</div>\n</div>'.format(
      obj['name'], type, doc_string, attr_string, obj['kind'])
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
  out.write('<!DOCTYPE html><html lang="en"><head><title>{1}</title><meta charset="UTF-8"><link rel="stylesheet" href="{0}style.css"></head><body>'.format(site_root, path))
  ds = get_doc_string(filename_core(lean_root, filename, 'lean'))
  module_doc = linkify_markdown(markdown2.markdown(ds), loc_map)
  out.write('<div class="mod_doc">' + module_doc + '</div>')
  for o in sorted(objs, key = lambda d: d['line']):
    write_decl_html(o, loc_map, out)
  out.write('</body></html>')

def write_html_files(partition, loc_map):
  for filename in partition:
    f = open_outfile(filename_core(html_root, filename, 'html'), 'w')
    write_html_file(partition[filename], loc_map, filename, f)
    f.close()

def write_html_indices(path):
  out = open_outfile(path + "/index.html", 'w')
  out.write('<html><head><title>{1}</title><link rel="stylesheet" href="{0}style.css"></head><body><ul>'.format(site_root, path))
  lst = os.listdir(path)
  files, dirs = [], []
  for name in lst:
    f = os.path.join(path, name)
    if os.path.isdir(f):
      dirs.append(name)
      write_html_indices(f)
    else:
      files.append(name)
  for name in dirs:
    out.write('<li><a href="{0}/index.html" class="index">{0}</a></li>\n'.format(name))
  for name in files:
    out.write('<li><a href="{0}" class="file">{0}</a></li>\n'.format(name))
  out.write('</ul></body></html>')
  out.close()

file_map, loc_map, _ = load_json()
write_html_files(file_map, loc_map)
write_html_indices(html_root)