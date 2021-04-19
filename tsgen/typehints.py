import dataclasses
from typing import get_type_hints


def get_dataclass_type_hints(dc, localns=None):
    annotations = get_type_hints(dc, localns=localns)
    return {
        field.name: annotations[field.name]
        for field in dataclasses.fields(dc)
    }
