import datetime

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types import typetree, Primitive, DateTime
from tsgen.types.tuple import Tuple
from tsgen.types.typetree__test import DummyTypeNode


def test_match_tuple():
    assert Tuple([Primitive(int), Primitive(str)]) == typetree.get_type_tree(tuple[int, str])


def test_basic_repr():
    ctx = CodeSnippetContext()
    t = Tuple([Primitive(int), Primitive(str)])
    assert t.ts_repr(ctx) == "[number, string]"
    assert ctx.natural_order() == []


def test_create_dto_simple():
    t = Tuple([Primitive(int), Primitive(str)])
    assert [12, "24"] == t.create_dto([12, "24"])


def test_create_dto_transform():
    t = Tuple([DateTime(), Primitive(int)])
    assert ["2021-04-25T00:00:00Z", 10] == t.create_dto([datetime.datetime(2021, 4, 25), 10])


def test_parse_dto_transform():
    t = Tuple([DateTime(), Primitive(int)])
    assert (datetime.datetime(2021, 4, 25), 10) == t.parse_dto(["2021-04-25T00:00:00Z", 10])


def test_ts_parse_dto_transform():
    ctx = CodeSnippetContext()
    t = Tuple([DummyTypeNode(), Primitive(int)])
    assert "[*parseDummyDto*(*dtoVar*[0]), *dtoVar*[1]]" == t.ts_parse_dto(ctx, "*dtoVar*")


def test_ts_create_dto_transform():
    ctx = CodeSnippetContext()
    t = Tuple([Primitive(int), DummyTypeNode()])
    assert "[*sourceVar*[0], *makeDummyDto*(*sourceVar*[1])]" == t.ts_create_dto(ctx, "*sourceVar*")

