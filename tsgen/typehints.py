import dataclasses
from types import GenericAlias
from typing import get_type_hints


def get_dataclass_type_hints(dc, localns=None):
    annotations = get_type_hints(dc, localns=localns)
    return {
        field.name: annotations[field.name]
        for field in dataclasses.fields(dc)
    }


def is_list_type(t: type):
    return isinstance(t, GenericAlias) and t.__origin__ == list