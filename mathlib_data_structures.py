class mathlibStructures:
  DECLARATIONS = 'decls'
  TACTICS = 'tactic_docs'
  MODULE_DESCRIPTIONS = 'mod_docs'
  NOTES = 'notes'
  INSTANCES = 'instances'

declaration = dict(
  NAME = 'name',
  IS_META = 'is_meta',
  ARGS = 'args',
  TYPE = 'type',
  DOC_STRING = 'doc_string',
  FILENAME = 'filename',
  LINE = 'line',
  ATTRIBUTES = 'attributes',
  EQUATIONS = 'equations',
  KIND = 'kind',
  STRUCTURE_FIELDS = 'structure_fields',
  CONSTRUCTORS = 'constructors'
)

declarationKindsSource = dict(
  THEOREM = 'thm',
  CONST = 'cnst',
  AXIOM = 'ax'
)

declarationKindsDestination = dict(
  STRUCTURE = 'structure',
  INDUCTIVE = 'inductive',
  THEOREM = 'theorem',
  CONST = 'const',
  AXIOM = 'axiom'
)

tactic = dict(
  NAME = 'name',
  CATEGORY = 'category',
  DECL_NAMES = 'decl_names',
  TAGS = 'tags',
  DESCRIPTION = 'description',
  IMPORT = 'import'
)

tacticCategories = dict(
  TACTIC = 'tactic',
  COMMAND = 'command',
  HOLE_COMMAND = 'hole_command',
  ATTRIBUTE = 'attribute'
)

generalPages = dict(
  INDEX = 'index',
  TACTICS = 'tactics',
  COMMANDS = 'commands',
  HOLE_COMMANDS = 'hole_commands',
  ATTRIBUTES = 'notes',
)


