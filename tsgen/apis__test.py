from dataclasses import dataclass

from tsgen import apis
from tsgen.apis import get_endpoint_info
from tsgen.interfaces import TSTypeContext


def test_api_gen():
    @dataclass
    class Foo:
        pass

    def get_foo(my_id) -> Foo:
        return Foo()

    ts_context = TSTypeContext()
    info = get_endpoint_info(get_foo)
    func_code = apis.build_ts_func(info, "/api/foo/<my_id>", ["my_id"], "GET", ts_context)
    assert func_code == """
export const getFoo = async (myId: string): Promise<Foo> => {
  const resp = await fetch(`/api/foo/${myId}`, {
    method: 'GET'
  });
  const data: Foo = await resp.json();
  return data;
}"""
    assert set(ts_context.interfaces.keys()) == {"Foo"}
