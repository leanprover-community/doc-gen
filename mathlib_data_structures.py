class mathlibStructures:
  DECLARATIONS = 'decls'
  TACTICS = 'tactic_docs'
  MODULE_DESCRIPTIONS = 'mod_docs'
  NOTES = 'notes'
  INSTANCES = 'instances'

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

class declarationKindsSource:
  THEOREM = 'thm'
  CONST = 'cnst'
  AXIOM = 'ax'

class declarationKindsDestination:
  STRUCTURE = 'structure'
  INDUCTIVE = 'inductive'
  THEOREM = 'theorem'
  CONST = 'const'
  AXIOM = 'axiom'

class tactic:
  NAME = 'name'
  CATEGORY = 'category'
  DECL_NAMES = 'decl_names'
  TAGS = 'tags'
  DESCRIPTION = 'description'
  IMPORT = 'import'

class tacticCategories:
  TACTIC = 'tactic'
  COMMAND = 'command'
  HOLE_COMMAND = 'hole_command'
  ATTRIBUTE = 'attribute'

class generalPages:
  INDEX = 'index'
  TACTICS = 'tactics'
  COMMANDS = 'commands'
  HOLE_COMMANDS = 'hole_commands'
  ATTRIBUTES = 'notes'