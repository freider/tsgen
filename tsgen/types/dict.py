from dataclasses import dataclass
from types import GenericAlias
from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.base import AbstractNode, UnsupportedTypeError
from tsgen.types.typetree import get_type_tree


@dataclass()
class Dict(AbstractNode):
    value_type: AbstractNode
    MAP_OBJECT_TS_HELPER = """
const _mapObject = <T, U>(o: { [key: string]: T }, f: (t: T) => U) : { [key: string]: U } => {
  const result: { [key: string]: U } = {};
  Object.keys(o).forEach((key) => {
    result[key] = f(o[key]);
  });
  return result;
}
"""

    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if isinstance(pytype, GenericAlias) and pytype.__origin__ == dict:
            if pytype.__args__[0] != str:
                raise UnsupportedTypeError(pytype.__args__[0])  # js objects only properly support string keys
            return Dict(
                get_type_tree(pytype.__args__[1], localns=localns)
            )

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        subtype = self.value_type.ts_repr(ctx)
        return f"{{ [key: string]: {subtype} }}"

    def parse_dto(self, struct):
        return {key: self.value_type.parse_dto(value) for key, value in struct.items()}

    def create_dto(self, pystruct):
        return {key: self.value_type.create_dto(value) for key, value in pystruct.items()}

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        ctx.add("_mapObject", self.MAP_OBJECT_TS_HELPER)
        sub_expr = self.value_type.ts_parse_dto(ctx, "val")
        if sub_expr == "val":
            return ts_expression
        return f"_mapObject({ts_expression}, val => ({sub_expr}))"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        ctx.add("_mapObject", self.MAP_OBJECT_TS_HELPER)
        sub_expr = self.value_type.ts_create_dto(ctx, "val")
        if sub_expr == "val":
            return ts_expression
        return f"_mapObject({ts_expression}, val => ({sub_expr}))"

    def dto_tree(self) -> AbstractNode:
        return Dict(value_type=self.value_type.dto_tree())