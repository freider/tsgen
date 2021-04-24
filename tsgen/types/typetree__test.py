import datetime
from dataclasses import dataclass
from typing import Optional

import pytest

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.typetree import get_type_tree
from tsgen.types.dict import Dict
from tsgen.types.datetime import DateTime
from tsgen.types.object import Object
from tsgen.types.list import List
from tsgen.types.base import AbstractNode, Primitive, UnsupportedTypeError


# noinspection PyAbstractClass
class DummyTypeNode(AbstractNode):
    """Used for generic testing"""

    def ts_repr(self, ctx: CodeSnippetContext) -> str:
        return "*Dummy*"

    def ts_create_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"*makeDummyDto*({ts_expression})"

    def ts_parse_dto(self, ctx: CodeSnippetContext, ts_expression: str) -> Optional[str]:
        return f"*parseDummyDto*({ts_expression})"

    def dto_tree(self) -> AbstractNode:
        # noinspection PyAbstractClass
        class DummyDto(AbstractNode):
            def ts_repr(self, ctx):
                return "*DummyDto*"

        return DummyDto()


def test_primitives():
    assert get_type_tree(int) == Primitive(int)
    assert get_type_tree(float) == Primitive(float)
    assert get_type_tree(str) == Primitive(str)
    assert get_type_tree(bool) == Primitive(bool)


def test_datetime():
    assert get_type_tree(datetime.datetime) == DateTime()
    source = datetime.datetime(2020, 10, 1, 3, 2, 1)
    assert DateTime().create_dto(source) == "2020-10-01T03:02:01Z"
    assert DateTime().parse_dto("2020-10-01T03:02:01Z") == source


class TestObject:
    def test_object(self):
        @dataclass
        class Foo:
            some_field: str

        assert get_type_tree(Foo, locals()) == Object("Foo", Foo, {"some_field": Primitive(str)})

    def test_nested(self):
        @dataclass
        class Bar:
            other_field: str

        @dataclass
        class Foo:
            some_field: Bar
            list_field: list[Bar]

        expected_bar_node = Object("Bar", Bar, {"other_field": Primitive(str)})
        assert get_type_tree(Foo, locals()) == Object(
            "Foo",
            Foo,
            {
                "some_field": expected_bar_node,
                "list_field": List(expected_bar_node)
            }
        )

    def test_object_ts_repr(self):
        ctx = CodeSnippetContext()

        @dataclass()
        class Foo:
            my_field: int
            other_field: str

        tree = Object.match(Foo)
        assert tree.ts_repr(ctx) == "Foo"
        assert ctx.top_level_snippets() == {"Foo"}
        assert ctx.get_snippet("Foo") == """
interface Foo {
  myField: number;
  otherField: string;
}"""

    def test_ts_create_dto_generic(self):
        ctx = CodeSnippetContext()
        t = Object("GenObj", lambda: None, {
            "d1": DummyTypeNode(),
        })
        parse_expr = t.ts_create_dto(ctx, "*dtoVar*")
        assert parse_expr == "{d1: *makeDummyDto*(*dtoVar*.d1)}"

    def test_ts_create_dto_json_compatible(self):
        ctx = CodeSnippetContext()
        t = Object("GenObj", lambda: None, {
            "d1": Primitive(bool),
        })
        parse_expr = t.ts_create_dto(ctx, "*dtoVar*")
        assert parse_expr == "*dtoVar*"

    def test_ts_create_dto_partially_json_compatible(self):
        ctx = CodeSnippetContext()
        t = Object("GenObj", lambda: None, {
            "d1": Primitive(bool),
            "d2": DummyTypeNode(),
        })
        parse_expr = t.ts_create_dto(ctx, "*dtoVar*")
        assert parse_expr == "{...*dtoVar*, d2: *makeDummyDto*(*dtoVar*.d2)}"


# interface generation tests

class TestCombinations:
    def test_list_ts_repr(self):
        ctx = CodeSnippetContext()
        assert List(Primitive(int)).ts_repr(ctx) == "number[]"
        assert List(Primitive(str)).ts_repr(ctx) == "string[]"
        assert List(List(Primitive(str))).ts_repr(ctx) == "string[][]"

    def test_deep_nested_tree_ts_repr(self):
        @dataclass
        class Baz:
            nano: int

        @dataclass
        class Bar:
            micro: list[Baz]

        @dataclass
        class Foo:
            my_field: Bar

        tree = Object.match(Foo)
        ctx = CodeSnippetContext()
        assert tree.ts_repr(ctx) == "Foo"

        assert "Foo" in ctx
        assert ctx.get_snippet("Foo") == """
interface Foo {
  myField: Bar;
}"""
        assert "Bar" in ctx
        assert ctx.get_snippet("Bar") == """
interface Bar {
  micro: Baz[];
}"""

        assert "Baz" in ctx
        assert ctx.get_snippet("Baz") == """
interface Baz {
  nano: number;
}"""

        assert ctx.topological_dependencies("Foo") == ["Baz", "Bar", "Foo"]


class TestList:
    def test_tree_parsing(self):
        assert get_type_tree(list[str]) == List(Primitive(str))
        assert get_type_tree(list[list[bool]]) == List(List(Primitive(bool)))

    def test_list_dto(self):
        t = List.match(list[str])
        assert t.create_dto(["hello", "world"]) == ["hello", "world"]

    def test_ts_repr(self):
        ctx = CodeSnippetContext()
        t = List(DummyTypeNode())
        assert t.ts_repr(ctx) == "*Dummy*[]"

    def test_ts_create_dto(self):
        ctx = CodeSnippetContext()
        t = List(DummyTypeNode())
        assert t.ts_create_dto(ctx, "*listVar*") == "*listVar*.map(item => (*makeDummyDto*(item)))"

    def test_ts_create_dto_with_json_compatible_element(self):
        ctx = CodeSnippetContext()
        t = List(Primitive(str))
        create_expr = t.ts_create_dto(ctx, "*listVar*")
        assert "*listVar*" == create_expr

    def test_ts_parse_dto(self):
        ctx = CodeSnippetContext()
        t = List(DummyTypeNode())
        parse_expr = t.ts_parse_dto(ctx, "*dtoVar*")
        assert "*dtoVar*.map(item => (*parseDummyDto*(item)))" == parse_expr

    def test_ts_parse_dto_with_json_compatible_element(self):
        ctx = CodeSnippetContext()
        t = List(Primitive(int))
        parse_expr = t.ts_parse_dto(ctx, "*dtoVar*")
        assert "*dtoVar*" == parse_expr


class TestDict:
    def test_tree_parsing(self):
        assert get_type_tree(dict[str, int]) == Dict(Primitive(int))
        with pytest.raises(UnsupportedTypeError):
            get_type_tree(dict[int, str])

    def test_ts_repr(self):
        assert Dict(DummyTypeNode()).ts_repr(CodeSnippetContext()) == "{ [key: string]: *Dummy* }"

    def test_ts_parse_dto_generic(self):
        ctx = CodeSnippetContext()
        parse_expr = Dict(DummyTypeNode()).ts_parse_dto(ctx, "*dtoVar*")
        assert parse_expr == "_mapObject(*dtoVar*, val => (*parseDummyDto*(val)))"

    def test_ts_create_dto_generic(self):
        ctx = CodeSnippetContext()
        parse_expr = Dict(DummyTypeNode()).ts_create_dto(ctx, "*dtoVar*")
        assert parse_expr == "_mapObject(*dtoVar*, val => (*makeDummyDto*(val)))"

    def test_ts_create_dto_json_compatible(self):
        ctx = CodeSnippetContext()
        parse_expr = Dict(Primitive(str)).ts_create_dto(ctx, "*dtoVar*")
        assert parse_expr == "*dtoVar*"
