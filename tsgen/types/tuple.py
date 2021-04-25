from dataclasses import dataclass
from types import GenericAlias
from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.base import AbstractNode
from tsgen.types.typetree import get_type_tree


@dataclass
class Tuple(AbstractNode):
    fields: list[AbstractNode]

    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if isinstance(pytype, GenericAlias) and pytype.__origin__ == tuple:
            return Tuple([get_type_tree(f) for f in pytype.__args__])

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        subtypes = (f.ts_repr(ctx) for f in self.fields)
        return f"[{', '.join(subtypes)}]"

    def parse_dto(self, struct):
        return tuple(field_tree.parse_dto(item) for field_tree, item in zip(self.fields, struct))

    def create_dto(self, pystruct):
        return [field_tree.create_dto(item) for field_tree, item in zip(self.fields, pystruct)]

    def dto_tree(self) -> AbstractNode:
        return Tuple([subtree.dto_tree() for subtree in self.fields])

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        subs = [subtree.ts_create_dto(ctx, f"{ts_expression}[{i}]") for i, subtree in enumerate(self.fields)]
        return f"[{', '.join(subs)}]"

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        subs = [subtree.ts_parse_dto(ctx, f"{ts_expression}[{i}]") for i, subtree in enumerate(self.fields)]
        return f"[{', '.join(subs)}]"
