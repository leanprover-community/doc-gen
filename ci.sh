DEPLOY_GITHUB_USER=leanprover-community-bot

set -e
set -x

lean_version="$(sed '/^lean_version/!d;s/.*"\(.*\)".*/\1/' mathlib/leanpkg.toml)"

cd mathlib
git_hash="$(git log -1 --pretty=format:%h)"

cd ..
# the commit hash in leanpkg.toml is used by doc_gen.
sed -i "s/rev = \"\S*\"/rev = \"$git_hash\"/" leanpkg.toml

echo -e "builtin_path\npath ./src\npath ../src" > leanpkg.path
git clone "https://$DEPLOY_GITHUB_USER:$DEPLOY_GITHUB_TOKEN@github.com/leanprover-community/mathlib_docs.git"

rm -rf mathlib_docs/docs/

# Force doc_gen project to match the Lean version used in CI.
# If they are incompatible, something in doc_gen will fail to compile,
# but this is better than trying to recompile all of mathlib.
elan override set "$lean_version"

./gen_docs -w -r "mathlib/" -t "mathlib_docs/docs/"

if [ "$github_repo" = "leanprover-community/doc-gen" -a "$github_ref" = "refs/heads/master" ]; then
  cd mathlib_docs/docs
  git config user.email "leanprover.community@gmail.com"
  git config user.name "leanprover-community-bot"
  git add -A .
  git checkout --orphan master2
  git commit -m "automatic update to $git_hash"
  git push -f origin HEAD:master
fi
