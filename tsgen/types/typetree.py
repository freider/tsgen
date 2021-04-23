from __future__ import annotations

from tsgen.types.base import UnsupportedTypeError


type_registry = []


def get_type_tree(pytype: type, localns=None):
    for node_class in type_registry:
        if node := node_class.match(pytype, localns):
            return node
    raise UnsupportedTypeError(pytype)

