import os 
import collections

root = '/d/lean/doc_test/mathilb_docs/'
root = r"D:\lean\doc_test\mathlib_docs"

def is_displayable_html(name):
    fn, ext = os.path.splitext(name)
    return fn != 'index' and ext == '.html'

def write_html_indices(path):
    s = ''
    lst = os.listdir(os.path.join(root,path))
    files, dirs = [], {}
    for name in lst:
        f = os.path.join(path, name)
        if os.path.isdir(os.path.join(root,f)):
            dirs[name] = write_html_indices(f)
        else:
            files.append(name)
    for name in sorted(dirs.keys()):
        s += '<div class="nav_sect">{0}</div>\n<div class="nav_sect_inner" id="{1}">\n{2}\n</div>'.format(
            name,
            os.path.join(path, name),
            dirs[name]
        )
    for name in filter(is_displayable_html, sorted(files)):
        s += '<div class="nav_file" id="{0}">{1}</div>\n'.format(
            os.path.join(path, name),
            name
        )
    return s

print(write_html_indices(''))