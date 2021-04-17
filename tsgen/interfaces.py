import dataclasses
from collections import defaultdict
from dataclasses import is_dataclass
from types import GenericAlias
from typing import Optional

import jinja2
from tsgen.formatting import to_pascal, to_camel

TS_INTERFACE_TEMPLATE = """
interface {{name}} {
{%- for field_name, type in fields %}
  {{field_name}}: {{type}};
{%- endfor %}
}
"""

def is_list_type(t: type):
    return isinstance(t, GenericAlias) and t.__origin__ == list


class CircularDependency(Exception):
    def __init__(self, name):
        self.name = name


PRIMITIVE_TYPES: dict[type, str] = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
}

class TSTypeContext:
    """
    Context object for building typescript interfaces from dataclasses

    Keeps track of inter-dependencies between those interfaces
    """
    def __init__(self):
        self.dataclass_types: dict[type, str] = {}
        self.interfaces: dict[str, str] = {}
        self.dependencies: dict[str, set[str]] = defaultdict(set)

    def top_level_interfaces(self) -> set[str]:
        """Get all types that no other types depend on"""
        without_dependents = set(self.interfaces.keys())
        for parent, deps in self.dependencies.items():
            if parent is not None:
                without_dependents -= set(deps)
        return without_dependents

    def natural_order(self) -> list[str]:
        """Get types in a natural order of definition

        Topologically sorted with leaves first and top level (root) interfaces last
        """
        ret = []
        for top in self.top_level_interfaces():
            deps = self.topological_dependencies(top)
            for d in deps:
                if d not in ret:
                    ret.append(d)
        return ret

    def topological_dependencies(self, ts_typename: str) -> list[str]:
        """
        Get all interface dependency types in topological order

        :param ts_typename: The name of the typescript type
        :return: List of typescript interfaces names, in leaf -> root order
        :raises: CircularDependency if a type direcltly or indirectly depends on itself (currently not supported)

        """
        used = set()
        result: list[str] = []

        def rec(t, ancestors):
            if t in ancestors:
                raise CircularDependency(t)
            if t in used:
                return
            unused = self.dependencies[t] - used
            if not unused:  # no unused dependency, this is a leaf!
                result.append(t)
                used.add(t)
                return

            for dep in unused:
                rec(dep, ancestors | {t})

        while True:
            rec(ts_typename, set())
            if result[-1] == ts_typename:  # toplevel dependency resolved
                break

        return result

    def py_to_ts_type(self, t: type, parent_ts_type: Optional[str] = None):
        if is_dataclass(t):
            if t not in self.dataclass_types:
                self._add_interface(t)
            ts_name = self.dataclass_types[t]
            self.dependencies[parent_ts_type].add(ts_name)
            return ts_name
        if is_list_type(t):
            #  e.g. list[int]
            return self._list_type(t, parent_ts_type)
        return PRIMITIVE_TYPES[t]

    def _list_type(self, t: GenericAlias, parent_ts_type: Optional[str] = None):
        assert len(t.__args__) == 1
        argtype = t.__args__[0]
        subtype = self.py_to_ts_type(argtype, parent_ts_type)
        return f"{subtype}[]"

    def _add_interface(self, dc):
        typename = to_pascal(dc.__name__)

        assert dc not in self.dataclass_types and typename not in self.dataclass_types.values()
        self.dataclass_types[dc] = typename
        dc_fields = dataclasses.fields(dc)
        fields = []

        for field in dc_fields:
            field_ts_type = self.py_to_ts_type(field.type, typename)
            field_ts_name = to_camel(field.name)
            fields.append((field_ts_name, field_ts_type))

        declaration_template = jinja2.Template(TS_INTERFACE_TEMPLATE)
        self.interfaces[typename] = declaration_template.render(
            name=typename,
            fields=fields
        )
