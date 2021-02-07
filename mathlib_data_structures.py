from dataclasses import dataclass, field

@dataclass
class mathlibStructures:
  DECLARATIONS = 'decls'
  TACTICS = 'tactic_docs'
  MODULE_DESCRIPTIONS = 'mod_docs'
  NOTES = 'notes'
  INSTANCES = 'instances'

@dataclass
class declaration:
  NAME = 'name'
  IS_META = 'is_meta'
  ARGS = 'args'
  TYPE = 'type'
  DOC_STRING = 'doc_string'
  FILENAME = 'filename'
  LINE = 'line'
  ATTRIBUTES = 'attributes'
  EQUATIONS = 'equations'
  KIND = 'kind'
  STRUCTURE_FIELDS = 'structure_fields'
  CONSTRUCTORS = 'constructors'

@dataclass
class declarationKindsSource:
  THEOREM = 'thm'
  CONST = 'cnst'
  AXIOM = 'ax'

@dataclass
class declarationKindsDestination:
  STRUCTURE = 'structure'
  INDUCTIVE = 'inductive'
  THEOREM = 'theorem'
  CONST = 'const'
  AXIOM = 'axiom'

@dataclass
class tactic:
  NAME = 'name'
  CATEGORY = 'category'
  DECL_NAMES = 'decl_names'
  TAGS = 'tags'
  DESCRIPTION = 'description'
  IMPORT = 'import'

@dataclass
class tacticCategories:
  TACTIC = 'tactic'
  COMMAND = 'command'
  HOLE_COMMAND = 'hole_command'
  ATTRIBUTE = 'attribute'

@dataclass
class generalPages:
  INDEX = 'index'
  TACTICS = 'tactics'
  COMMANDS = 'commands'
  HOLE_COMMANDS = 'hole_commands'
  ATTRIBUTES = 'notes'


