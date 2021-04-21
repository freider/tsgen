from __future__ import annotations

import datetime
from dataclasses import dataclass, is_dataclass
from typing import Optional

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_camel, to_pascal
from tsgen.typehints import is_list_type, get_dataclass_type_hints


PRIMITIVE_TYPES: dict[type, str] = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
}


class UnsupportedTypeError(Exception):
    def __init__(self, pytype):
        super(UnsupportedTypeError, self).__init__(f"Unsupported python type {pytype}")


def get_type_tree(pytype: type, localns=None):
    for node_class in type_registry:
        if node := node_class.match(pytype, localns):
            return node
    raise UnsupportedTypeError(pytype)


class AbstractNode:
    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        raise NotImplementedError(repr(cls))

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        raise NotImplementedError(repr(self))

    def parse_json(self, struct):
        raise NotImplementedError(repr(self))

    def prepare_json(self, pystruct):
        raise NotImplementedError(repr(self))

    def ts_prep_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return ts_expression

    def ts_parse_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return ts_expression


@dataclass()
class List(AbstractNode):
    element_node: AbstractNode

    @classmethod
    def match(cls, pytype: type, localns=None):
        if is_list_type(pytype):
            subtype = pytype.__args__[0]
            return List(element_node=get_type_tree(subtype, localns=localns))

    def ts_repr(self, ctx):
        return f"{self.element_node.ts_repr(ctx)}[]"

    def parse_json(self, struct):
        assert isinstance(struct, list)
        return [self.element_node.parse_json(it) for it in struct]

    def prepare_json(self, pystruct):
        return [self.element_node.prepare_json(it) for it in pystruct]

    def ts_prep_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"{ts_expression}.map(item => {self.element_node.ts_prep_json(ctx, 'item')})"

    def ts_parse_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"{ts_expression}.map(item => {self.element_node.ts_parse_json(ctx, 'item')})"


TS_INTERFACE_TEMPLATE = """
interface {{name}} {
{%- for field_name, type in fields %}
  {{field_name}}: {{type}};
{%- endfor %}
}
"""


@dataclass()
class Object(AbstractNode):
    dataclass: type
    fields: dict[str, AbstractNode]

    @classmethod
    def match(cls, pytype: type, localns=None):
        if is_dataclass(pytype):
            field_hints = get_dataclass_type_hints(pytype, localns=localns)
            fields = {
                field_name: get_type_tree(subtype, localns)
                for field_name, subtype in field_hints.items()
            }
            return Object(dataclass=pytype, fields=fields)

    def ts_repr(self, ctx: CodeSnippetContext):
        interface_name = to_pascal(self.dataclass.__name__)
        if interface_name not in ctx:
            code = self._render_ts_interface(interface_name, ctx)
            ctx.add(interface_name, code)

        return interface_name

    def _render_ts_interface(self, interface_name: str, ctx: CodeSnippetContext):
        ts_fields = []
        subctx = ctx.subcontext(interface_name)
        for field_name, sub_node in self.fields.items():
            field_ts_type = sub_node.ts_repr(subctx)
            field_ts_name = to_camel(field_name)
            ts_fields.append((field_ts_name, field_ts_type))

        declaration_template = jinja2.Template(TS_INTERFACE_TEMPLATE)
        return declaration_template.render(
            name=interface_name,
            fields=ts_fields
        )

    def parse_json(self, struct):
        return self.dataclass(**{
            name: subtype.parse_json(struct[to_camel(name)])
            for name, subtype in self.fields.items()
        })

    def prepare_json(self, pystruct):
        return {
            to_camel(name): subtype.prepare_json(getattr(pystruct, name))
            for name, subtype in self.fields.items()
        }

    def ts_prep_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        subexprs = []
        for name, subtype in self.fields.items():
            ts_name = to_camel(name)
            field_ref = f"{ts_expression}.{ts_name}"
            subexprs.append(f"{ts_name}: {subtype.ts_prep_json(ctx, field_ref)}")

        return f"{{{', '.join(subexprs)}}}"

    def ts_parse_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        subexprs = []
        for name, subtype in self.fields.items():
            ts_name = to_camel(name)
            field_ref = f"{ts_expression}.{ts_name}"
            subexprs.append(f"{ts_name}: {subtype.ts_parse_json(ctx, field_ref)}")

        return f"{{{', '.join(subexprs)}}}"


@dataclass()
class Primitive(AbstractNode):
    pytype: type

    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if pytype in PRIMITIVE_TYPES:
            return Primitive(pytype=pytype)

    def ts_repr(self, ctx):
        return PRIMITIVE_TYPES[self.pytype]

    def parse_json(self, struct):
        return self.pytype(struct)

    def prepare_json(self, pystruct):
        return pystruct


@dataclass()
class DateTime(AbstractNode):
    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if pytype == datetime.datetime:
            return DateTime()

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        return "Date"

    def ts_prep_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        prep_function_name = "formatISODateString"
        iso_formatter_ts = f"const {prep_function_name} = (d: Date): string => d.toISOString().split('.')[0] + 'Z';"
        ctx.add(prep_function_name, iso_formatter_ts)
        return f"{prep_function_name}({ts_expression})"

    def parse_json(self, struct):
        assert isinstance(struct, str)
        return datetime.datetime.strptime(struct, "%Y-%m-%dT%H:%M:%SZ")

    def prepare_json(self, pystruct):
        assert isinstance(pystruct, datetime.datetime)
        return pystruct.strftime("%Y-%m-%dT%H:%M:%SZ")

    def ts_parse_json(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"new Date({ts_expression})"


type_registry = [Primitive, List, Object, DateTime]
