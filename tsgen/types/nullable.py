import typing
from dataclasses import dataclass

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.base import AbstractNode
from tsgen.types.typetree import get_type_tree


@dataclass()
class Nullable(AbstractNode):
    subtype: AbstractNode

    # noinspection PyUnresolvedReferences
    @classmethod
    def match(cls, pytype: type, localns=None) -> typing.Optional[AbstractNode]:
        if (
            hasattr(pytype, "__origin__")   # isinstance(Union[...], GenericAlias) returns False
            and pytype.__origin__ == typing.Union
            and len(pytype.__args__) == 2
            and type(None) in pytype.__args__
        ):
            other = [arg for arg in pytype.__args__ if arg is not type(None)][0]
            return Nullable(get_type_tree(other))

    def parse_dto(self, struct):
        if struct is None:
            return None
        return self.subtype.parse_dto(struct)

    def create_dto(self, pystruct):
        if pystruct is None:
            return None
        return self.subtype.create_dto(pystruct)

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        return f"{self.subtype.ts_repr(ctx)} | null"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return self.subtype.ts_create_dto(ctx, ts_expression)

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return self.subtype.ts_parse_dto(ctx, ts_expression)

    def dto_tree(self) -> AbstractNode:
        return self.subtype.dto_tree()
