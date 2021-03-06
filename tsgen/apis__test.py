from __future__ import annotations

from dataclasses import dataclass

from tsgen.apis import build_ts_func
from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.types.typetree import get_type_tree


@dataclass
class Foo:
    pass


def test_api_gen():
    foo_type_tree = get_type_tree(Foo)
    ctx = CodeSnippetContext()
    func_code = build_ts_func(
        "getFoo",
        foo_type_tree,
        None,
        "/api/foo/<my_id>",
        ["my_id"],
        "GET",
        ctx
    )
    expected_func_code = """
export const getFoo = async (myId: string): Promise<Foo> => {
  const response = await fetch(`/api/foo/${myId}`, {
    method: 'GET'
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }
  return await response.json();
}"""
    assert func_code == expected_func_code
    assert ctx.natural_order() == ["ApiError", "Foo"]
