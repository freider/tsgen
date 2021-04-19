from __future__ import annotations

import datetime
from dataclasses import dataclass

from tsgen.interfaces import TSTypeContext


def test_list():
    t = TSTypeContext()
    assert t.py_to_ts_type(list[int]) == "number[]"
    assert t.py_to_ts_type(list[str]) == "string[]"
    assert t.py_to_ts_type(list[list[str]]) == "string[][]"


def test_dataclass():
    t = TSTypeContext()

    @dataclass
    class Foo:
        my_field: int
        other_field: str

    assert t.py_to_ts_type(Foo) == "Foo"
    assert t.top_level_interfaces() == {"Foo"}
    assert t.interfaces["Foo"] == """
interface Foo {
  myField: number;
  otherField: string;
}"""


def test_deep_nested_dataclass():
    t = TSTypeContext()

    @dataclass
    class Baz:
        nano: int

    @dataclass
    class Bar:
        micro: Baz

    @dataclass
    class Foo:
        my_field: Bar

    assert t.py_to_ts_type(Foo, localns=locals()) == "Foo"
    assert t.interfaces["Foo"] == """
interface Foo {
  myField: Bar;
}"""
    assert t.interfaces["Bar"] == """
interface Bar {
  micro: Baz;
}"""
    assert t.interfaces["Baz"] == """
interface Baz {
  nano: number;
}"""
    assert t.dependencies["Foo"] == {"Bar"}
    assert t.topological_dependencies("Foo") == ["Baz", "Bar", "Foo"]
    assert t.dependencies["Bar"] == {"Baz"}
    assert t.dependencies["Baz"] == set()


def test_list_of_dataclass():
    t = TSTypeContext()

    @dataclass
    class Bar:
        my_field: int

    @dataclass
    class Foo:
        bars: list[Bar]

    assert t.py_to_ts_type(Foo, localns=locals()) == "Foo"
    assert t.topological_dependencies("Foo") == ["Bar", "Foo"]
