from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from flask import Flask, Response, request

from tsgen.flask_integration import typed, cli_blueprint, dev_reload_hook

app = Flask(__name__)
app.register_blueprint(cli_blueprint)


@dataclass
class Foo:
    one_field: str


@app.route("/api/foo/<id>")
@typed()
def get_foo(id) -> Foo:
    return Foo(one_field=f"hello {id}")


@dataclass
class Bar:
    sub_field: Foo
    other_field: str


@app.route("/api/bar", methods=["POST"])
@typed()
def create_bar(bar: Bar) -> Foo:
    return bar.sub_field


@app.route("/api/raw", methods=["POST"])
@typed()
def only_inject_endpoint(the_foo: Foo):
    assert the_foo.one_field == request.json["oneField"]
    return Response(status=201)


@app.route("/api/failing")
@typed()
def failing():
    return Response(status=400)


@app.route("/api/next-day", methods=["POST"])
@typed()
def next_day(dt: datetime.datetime) -> datetime.datetime:
    return dt + datetime.timedelta(1)


@app.route("/api/reverse", methods=["POST"])
@typed()
def reverse(items: list[int]) -> list[int]:
    items.reverse()
    return items


# enable hot reloads in development mode
dev_reload_hook(app, str(Path(__file__).parent / "frontend/generated"))


if __name__ == '__main__':
    app.run()
