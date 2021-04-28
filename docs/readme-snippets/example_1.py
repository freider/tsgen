from dataclasses import dataclass

from flask import Flask
from tsgen.flask_integration import typed, cli_blueprint

app = Flask(__name__)
app.register_blueprint(cli_blueprint)


@dataclass
class Foo:
    one_field: str


@app.route("/foo/<foo_id>")
@typed()
def get_foo(foo_id) -> Foo:
    return Foo(one_field=f"hello {foo_id}")
