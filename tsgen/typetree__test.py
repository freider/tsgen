import datetime
from dataclasses import dataclass

from tsgen.typetree import get_type_tree, Primitive, List, Object, DateTime
from tsgen.code_snippet_context import CodeSnippetContext


def test_primitives():
    assert get_type_tree(int) == Primitive(int)
    assert get_type_tree(float) == Primitive(float)
    assert get_type_tree(str) == Primitive(str)
    assert get_type_tree(bool) == Primitive(bool)


def test_list():
    assert get_type_tree(list[str]) == List(Primitive(str))
    assert get_type_tree(list[list[bool]]) == List(List(Primitive(bool)))


def test_datetime():
    assert get_type_tree(datetime.datetime) == DateTime()
    source = datetime.datetime(2020, 10, 1, 3, 2, 1)
    assert DateTime().prepare_json(source) == "2020-10-01T03:02:01Z"
    assert DateTime().parse_json("2020-10-01T03:02:01Z") == source


def test_object():
    @dataclass
    class Foo:
        some_field: str

    assert get_type_tree(Foo, locals()) == Object(Foo, {"some_field": Primitive(str)})


def test_nested():
    @dataclass
    class Bar:
        other_field: str

    @dataclass
    class Foo:
        some_field: Bar
        list_field: list[Bar]

    expected_bar_node = Object(Bar, {"other_field": Primitive(str)})
    assert get_type_tree(Foo, locals()) == Object(
        Foo, {
            "some_field": expected_bar_node,
            "list_field": List(expected_bar_node)
        }
    )


# interface generation tests


def test_list_ts_repr():
    ctx = CodeSnippetContext()
    assert List(Primitive(int)).ts_repr(ctx) == "number[]"
    assert List(Primitive(str)).ts_repr(ctx) == "string[]"
    assert List(List(Primitive(str))).ts_repr(ctx) == "string[][]"


def test_object_ts_repr():
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


def test_deep_nested_tree_tsrepr():
    @dataclass
    class Baz:
        nano: int

    @dataclass
    class Bar:
        micro: Baz

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
  micro: Baz;
}"""

    assert "Baz" in ctx
    assert ctx.get_snippet("Baz") == """
interface Baz {
  nano: number;
}"""

    assert ctx.topological_dependencies("Foo") == ["Baz", "Bar", "Foo"]


def test_list_of_dataclass_tsrepr():
    ctx = CodeSnippetContext()
    @dataclass
    class Bar:
        my_field: int

    @dataclass
    class Foo:
        bars: list[Bar]

    tree = Object.match(Foo)

    assert tree.ts_repr(ctx) == "Foo"
    assert ctx.natural_order() == ["Bar", "Foo"]
