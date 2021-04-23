from tsgen.types.base import Primitive, UnsupportedTypeError
from tsgen.types.datetime import DateTime
from tsgen.types.dict import Dict
from tsgen.types.list import List
from tsgen.types.object import Object
from tsgen.types.typetree import type_registry

type_registry.extend([Primitive, List, Object, DateTime, Dict])
