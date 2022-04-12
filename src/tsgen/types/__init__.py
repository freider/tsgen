from tsgen.types.base import AbstractNode, Primitive, UnsupportedTypeError
from tsgen.types.dates import DateTime, Date
from tsgen.types.dict import Dict
from tsgen.types.list import List
from tsgen.types.nullable import Nullable
from tsgen.types.object import Object
from tsgen.types.tuple import Tuple
from tsgen.types.typetree import type_registry, get_type_tree

type_registry.extend([Primitive, List, Object, DateTime, Date, Dict, Tuple, Nullable])
