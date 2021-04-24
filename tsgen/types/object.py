import dataclasses
from dataclasses import dataclass, is_dataclass
from typing import get_type_hints, Callable, Optional

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_pascal, to_camel
from tsgen.types.base import AbstractNode
from tsgen.types.typetree import get_type_tree

TS_INTERFACE_TEMPLATE = """
interface {{name}} {
{%- for field_name, type in fields %}
  {{field_name}}: {{type}};
{%- endfor %}
}
"""


def get_dataclass_type_hints(dc, localns=None):
    dc_types = get_type_hints(dc, localns=localns)
    return {
        field.name: dc_types[field.name]
        for field in dataclasses.fields(dc)
    }


@dataclass()
class Object(AbstractNode):
    name: str
    constructor: Callable
    fields: dict[str, AbstractNode]

    @classmethod
    def match(cls, pytype: type, localns=None):
        if is_dataclass(pytype):
            field_hints = get_dataclass_type_hints(pytype, localns=localns)
            fields = {
                field_name: get_type_tree(subtype, localns)
                for field_name, subtype in field_hints.items()
            }
            return Object(pytype.__name__, constructor=pytype, fields=fields)

    def ts_repr(self, ctx: CodeSnippetContext):
        interface_name = to_pascal(self.name)
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

    def parse_dto(self, struct):
        return self.constructor(**{
            name: subtype.parse_dto(struct[to_camel(name)])
            for name, subtype in self.fields.items()
        })

    def create_dto(self, pystruct):
        return {
            to_camel(name): subtype.create_dto(getattr(pystruct, name))
            for name, subtype in self.fields.items()
        }

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        subexprs = []
        for name, subtype in self.fields.items():
            ts_name = to_camel(name)
            field_ref = f"{ts_expression}.{ts_name}"
            subexprs.append(f"{ts_name}: {subtype.ts_create_dto(ctx, field_ref)}")

        return f"{{{', '.join(subexprs)}}}"

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        subexprs = []
        for name, subtype in self.fields.items():
            ts_name = to_camel(name)
            field_ref = f"{ts_expression}.{ts_name}"
            subexprs.append(f"{ts_name}: {subtype.ts_parse_dto(ctx, field_ref)}")

        return f"{{{', '.join(subexprs)}}}"

    def dto_tree(self) -> AbstractNode:
        # TODO: use TypedDict Node instead of named object type
        def failing_constructor():
            raise RuntimeError("Dto object type should never be instantiated on the Python side")

        return Object(self.name + "Dto", failing_constructor, {
            name: field_tree.dto_tree() for name, field_tree in self.fields.items()
        })