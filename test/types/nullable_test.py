from typing import Optional

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types import Primitive
from tsgen.types.nullable import Nullable as OptionalNode


def test_match():
    assert OptionalNode.match(Optional[str]) == OptionalNode(Primitive(str))


def test_parse_dto():
    t = OptionalNode(Primitive(str))
    assert t.parse_dto(None) is None
    assert t.parse_dto("foo") == "foo"


def test_ts_repr():
    t = OptionalNode(Primitive(str))
    assert t.ts_repr(CodeSnippetContext()) == "string | null"
