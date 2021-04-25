import datetime
from dataclasses import dataclass
from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.base import AbstractNode, Primitive


@dataclass()
class DateTime(AbstractNode):
    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if pytype == datetime.datetime:
            return DateTime()

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        return "Date"

    def parse_dto(self, struct):
        assert isinstance(struct, str)
        return datetime.datetime.strptime(struct, "%Y-%m-%dT%H:%M:%SZ")

    def create_dto(self, pystruct):
        assert isinstance(pystruct, datetime.datetime)
        return pystruct.strftime("%Y-%m-%dT%H:%M:%SZ")

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"new Date({ts_expression})"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        prep_function_name = "_formatISODateTimeString"
        if prep_function_name not in ctx:
            iso_formatter_ts = f"const {prep_function_name} = (d: Date): string => d.toISOString().split('.')[0] + 'Z';"
            ctx.add(prep_function_name, iso_formatter_ts)
        return f"{prep_function_name}({ts_expression})"

    def dto_tree(self) -> AbstractNode:
        return Primitive(str)


@dataclass()
class Date(AbstractNode):
    @classmethod
    def match(cls, pytype: type, localns=None) -> Optional[AbstractNode]:
        if pytype == datetime.date:
            return Date()

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        return "Date"

    def parse_dto(self, struct):
        assert isinstance(struct, str)
        return datetime.datetime.strptime(struct, "%Y-%m-%d").date()

    def create_dto(self, pystruct):
        assert isinstance(pystruct, datetime.datetime)
        return pystruct.strftime("%Y-%m-%d")

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"new Date({ts_expression})"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        prep_function_name = "_formatISODateString"
        if prep_function_name not in ctx:
            iso_formatter_ts = f"const {prep_function_name} = (d: Date): string => d.toISOString().split('T')[0] + 'Z';"
            ctx.add(prep_function_name, iso_formatter_ts)
        return f"{prep_function_name}({ts_expression})"

    def dto_tree(self) -> AbstractNode:
        return Primitive(str)
