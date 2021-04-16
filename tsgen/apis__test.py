from dataclasses import dataclass

from flask import Flask
from tsgen import apis
from tsgen.flask import typed
from tsgen.interfaces import TSTypeContext


def test_api_gen():
    app = Flask(__name__)

    @dataclass
    class Foo:
        pass

    @app.route("/api/foo/<my_id>")
    @typed(__name__)
    def get_foo(my_id) -> Foo:
        return Foo()

    ts_context = TSTypeContext()
    func_code = apis.build_ts_func(get_foo._ts_gen, "/api/foo/<my_id>", ["my_id"], "GET", ts_context)
    assert func_code == """
export const getFoo = async (myId: string): Promise<Foo> => {
  const resp = await fetch(`/api/foo/${myId}`, {
    method: 'GET'
  });
  const data: Foo = await resp.json();
  return data;
}"""
