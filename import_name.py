import subprocess
from typing import NamedTuple, List
from pathlib import Path
import json
import toml

class ImportName(NamedTuple):
  project: str
  parts: List[str]
  raw_path: Path

  @classmethod
  def of(cls, fname: str):
    fname = Path(fname)
    path_info = [(p.resolve(), get_name_from_leanpkg_path(p)) for p in lean_paths]
    path_details = "".join(f" - {p}\n" for p, _ in path_info)

    for p, name in path_info:
      try:
        rel_path = fname.relative_to(p)
      except ValueError:
        pass
      else:
        return cls(name, rel_path.with_suffix('').parts, fname)
        
    raise RuntimeError(
      f"Cannot determine import name for {fname}; it is not within any of the directories returned by `lean --path`:\n"
      f"{path_details}"
      f"Did you generate `export.json` using a different Lean installation to the one this script is running with?")

  @property
  def name(self):
    return '.'.join(self.parts)

  @property
  def url(self):
    return '/'.join(self.parts) + '.html'

def get_name_from_leanpkg_path(p: Path) -> str:
  """ get the package name corresponding to a source path """
  if p.parts[-5:] == Path('bin/../lib/lean/library').parts or p.parts[-3:] == Path('bin/../library').parts:
    return "core"

  # try the toml
  p_leanpkg = p / '..' / 'leanpkg.toml'
  try:
    f = p_leanpkg.open()
  except FileNotFoundError:
    pass
  else:
    with f:
      parsed_toml = toml.loads(f.read())
    return parsed_toml['package']['name']

  return '<unknown>'

lean_paths = [
  Path(p)
  for p in json.loads(subprocess.check_output(['lean', '--path']).decode())['path']
]
