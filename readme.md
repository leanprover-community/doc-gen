# Lean HTML documentation generator

A tool to generate documentation for [mathlib](https://github.com/leanprover-community/mathlib/).

## Requirements

This script is not Windows friendly.

It depends on features of Lean 3.5c added in
<https://github.com/leanprover-community/lean/pull/81>.

```
pip install -r requirements.txt
rm -rf _target
leanproject up
```

Make sure that [`.olean` files](https://github.com/leanprover/tutorial/blob/master/05_Interacting_with_Lean.org#projects)
are generated for mathlib in `_target`, otherwise this will be extremely slow.

## Usage

`./gen_docs` will create a directory `html` with the generated documentation.

If you don't have enough RAM to run `./gen_docs`, consider downloading the documentation
from [here](https://github.com/leanprover-community/mathlib_docs) and renaming `docs` to `html`.

The links will point to `/` as the root of the site.
I typically host a server from the `html` directory with `python3 -m http.server`.
If you intend to host the site somewhere else than the root,
call for example `./gen_docs -w 'https://lean.com/my-documentation/'`.

`gen_docs -l` will symlink the css file, so you can edit `style.css` in the root directory
without regenerating anything. This is useful for local development.
