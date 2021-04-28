from dataclasses import dataclass

from flask import Flask

from tsgen import init_tsgen
from tsgen.flask_integration import typed, build_ts_api

app = Flask(__name__)
init_tsgen(app)


@dataclass
class Foo:
    one_field: str


@app.route("/foo/<foo_id>")
@typed()
def get_foo(foo_id) -> Foo:
    return Foo(one_field=f"hello {foo_id}")


if __name__ == "__main__":
    client_builder = build_ts_api(app)
    for modulepath, content in client_builder.get_files().items():
        print(content)
