from dataclasses import dataclass
from types import GenericAlias
from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.base import AbstractNode
from tsgen.types.typetree import get_type_tree


@dataclass()
class List(AbstractNode):
    element_node: AbstractNode

    @classmethod
    def match(cls, pytype: type, localns=None):
        if isinstance(pytype, GenericAlias) and pytype.__origin__ == list:
            subtype = pytype.__args__[0]
            return List(element_node=get_type_tree(subtype, localns=localns))

    def ts_repr(self, ctx):
        return f"{self.element_node.ts_repr(ctx)}[]"

    def parse_dto(self, struct):
        assert isinstance(struct, list)
        return [self.element_node.parse_dto(it) for it in struct]

    def create_dto(self, pystruct):
        return [self.element_node.create_dto(it) for it in pystruct]

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        sub_expression = self.element_node.ts_create_dto(ctx, "item")
        if sub_expression == "item":
            return ts_expression
        return f"{ts_expression}.map(item => ({sub_expression}))"

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        sub_expression = self.element_node.ts_parse_dto(ctx, "item")
        if sub_expression == "item":
            return ts_expression
        return f"{ts_expression}.map(item => ({sub_expression}))"

    def dto_tree(self) -> AbstractNode:
        return List(self.element_node.dto_tree())
