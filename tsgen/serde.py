import dataclasses
from dataclasses import is_dataclass

from tsgen.formatting import to_camel
from tsgen.interfaces import PRIMITIVE_TYPES, is_list_type


def parse_json(pytype: type, data):
    """Parse camel-case json as python types

    Mainly used for converting deserialized json data
    with came-cased object names into dataclasses that
    have snake_cased python names.
    """
    if pytype in PRIMITIVE_TYPES:
        return data  # passthrough of primitives
    elif is_dataclass(pytype):
        return pytype(**{
            field.name: parse_json(field.type, data[to_camel(field.name)])
            for field in dataclasses.fields(pytype)
        })
    elif is_list_type(pytype):
        list_arg = pytype.__args__[0]
        return [parse_json(list_arg, it) for it in data]
    else:
        raise RuntimeError(f"unsupported type {type!r}")


def prepare_json(obj):
    if type(obj) in PRIMITIVE_TYPES:
        return obj  # pass-through of primitives
    elif is_dataclass(obj):
        return {
            to_camel(field.name): prepare_json(getattr(obj, field.name))
            for field in dataclasses.fields(obj)
        }
    elif isinstance(obj, list):
        return [prepare_json(it) for it in obj]
    else:
        raise RuntimeError(f"unsupported type {type(obj)!r}")
