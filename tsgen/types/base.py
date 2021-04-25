from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext


class AbstractNode:
    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        raise NotImplementedError(repr(cls))

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        raise NotImplementedError(repr(self))

    def parse_dto(self, struct):
        raise NotImplementedError(repr(self))

    def create_dto(self, pystruct):
        raise NotImplementedError(repr(self))

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        raise NotImplementedError(repr(self))

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        raise NotImplementedError(repr(self))

    def dto_tree(self) -> AbstractNode:
        raise NotImplementedError(repr(self))


PRIMITIVE_TYPES: dict[type, str] = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
}


@dataclass()
class Primitive(AbstractNode):
    """Directly json compatible types of a "leaf" character in a type tree"""
    pytype: type

    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if pytype in PRIMITIVE_TYPES:
            return Primitive(pytype=pytype)

    def ts_repr(self, ctx):
        return PRIMITIVE_TYPES[self.pytype]

    def parse_dto(self, struct):
        return self.pytype(struct)

    def create_dto(self, pystruct):
        return pystruct

    def dto_tree(self) -> AbstractNode:
        return self

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return ts_expression

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> str:
        return ts_expression


class UnsupportedTypeError(Exception):
    def __init__(self, pytype):
        super(UnsupportedTypeError, self).__init__(f"Unsupported python type {pytype}")