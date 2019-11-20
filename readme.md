# gen_docs

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

The links will point to `./html/` as the root of the site. If you intend to host the site elsewhere, edit `site_root` in `leanpkg.toml` and use `./gen_docs -w`.