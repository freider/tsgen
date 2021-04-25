import dataclasses
from dataclasses import dataclass, is_dataclass
from typing import get_type_hints, Callable, Optional

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_pascal, to_camel
from tsgen.types.base import AbstractNode
from tsgen.types.typetree import get_type_tree

TS_INTERFACE_TEMPLATE = """
{%- if name %}{{ prefix }}interface {{name}} {% endif %}{
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
    name: Optional[str]   # when name is none the type will be inlined instead of declared
    constructor: Callable  # python constuctor for the object, taking keyword arguments for each field
    fields: dict[str, AbstractNode]

    # configurable options for specific use cases
    public: bool = True
    translate_name: bool = True

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
        if self.name:
            interface_name = to_pascal(self.name) if self.translate_name else self.name
            if interface_name not in ctx:
                subctx = ctx.subcontext(interface_name)
                code = self._render_ts_interface(interface_name, subctx)
                ctx.add(interface_name, code)
            return interface_name
        else:
            return self._render_ts_interface(None, ctx)

    def _render_ts_interface(self, interface_name: Optional[str], ctx: CodeSnippetContext):
        ts_fields = []

        for field_name, sub_node in self.fields.items():
            field_ts_type = sub_node.ts_repr(ctx)
            field_ts_name = to_camel(field_name)
            ts_fields.append((field_ts_name, field_ts_type))

        declaration_template = jinja2.Template(TS_INTERFACE_TEMPLATE)
        return declaration_template.render(
            name=interface_name,
            fields=ts_fields,
            prefix="export " if self.public else ""
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

    def _dto_recode_helper(self, ctx: CodeSnippetContext, ts_expression: str, func_getter):
        subexprs = []
        for name, subtype in self.fields.items():
            ts_name = to_camel(name)
            field_ref = f"{ts_expression}.{ts_name}"
            sub_expr = func_getter(subtype)(ctx, field_ref)
            if sub_expr != field_ref:
                subexprs.append(f"{ts_name}: {sub_expr}")

        if not subexprs:
            return ts_expression
        if len(subexprs) == len(self.fields):
            return f"{{{', '.join(subexprs)}}}"
        return f"{{...{ts_expression}, {', '.join(subexprs)}}}"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return self._dto_recode_helper(ctx, ts_expression, lambda t: t.ts_create_dto)

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return self._dto_recode_helper(ctx, ts_expression, lambda t: t.ts_parse_dto)

    def dto_tree(self) -> AbstractNode:
        def failing_constructor():
            raise RuntimeError("Dto object type should never be instantiated on the Python side")

        return Object(
            name=f"_{self.name}Dto",
            constructor=failing_constructor,
            fields={
                name: field_tree.dto_tree() for name, field_tree in self.fields.items()
            },
            public=False,
            translate_name=False,
        )
