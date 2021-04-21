from __future__ import annotations
from dataclasses import dataclass

from tsgen import apis
from tsgen.apis import get_endpoint_info
from tsgen.code_snippet_context import CodeSnippetContext


@dataclass
class Foo:
    pass


def test_api_gen():
    def get_foo(my_id) -> Foo:
        return Foo()

    ts_context = CodeSnippetContext()
    info = get_endpoint_info(get_foo)
    func_code = apis.build_ts_func(info, "/api/foo/<my_id>", ["my_id"], "GET", ts_context)
    expected_func_code = """
export const getFoo = async (myId: string): Promise<Foo> => {
  const response = await fetch(`/api/foo/${myId}`, {
    method: 'GET'
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }
  const dto = await response.json();
  return {};
}"""
    assert func_code == expected_func_code
    assert ts_context.natural_order() == ["Foo"]
