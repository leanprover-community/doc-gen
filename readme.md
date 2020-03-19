# Lean HTML documentation generator

A tool to generate documentation for [mathlib](https://github.com/leanprover-community/mathlib/).

## Requirements

This script is not Windows friendly.

It depends on features of Lean 3.5c added in
<https://github.com/leanprover-community/lean/pull/81>.

```
pip install markdown2 toml
leanpkg configure
update-mathlib
```

Make sure that olean files are generated for mathlib in `_target`, otherwise this will be extremely slow.

## Usage

`./gen_docs` will create a directory `html` with the generated documentation.

The links will point to `http://localhost:8000` as the root of the site.
I typically host a server from the `html` directory with `python3 -m http.server`.
If you intend to host the site elsewhere, edit `web_root` in `print_docs.py` and use `./gen_docs -w`.

`gen_docs -l` will symlink the css file, so you can edit `style_js_frame.css` in the root directory
without regenerating anything. This is useful for local development.