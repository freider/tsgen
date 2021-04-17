from dataclasses import dataclass

from flask import Flask, Response, request

from tsgen.flask import typed, cli_blueprint

app = Flask(__name__)
app.register_blueprint(cli_blueprint)


@dataclass
class Foo:
    one_field: str


@app.route("/foo/<id>")
@typed()
def get_foo(id) -> Foo:
    return Foo(one_field=f"hello {id}")


@dataclass
class Bar:
    sub_field: Foo
    other_field: str


@app.route("/bar/", methods=["POST"])
@typed()
def create_bar(bar: Bar) -> Foo:
    return bar.sub_field


@app.route("/api/raw_response", methods=["POST"])
@typed()
def only_inject_endpoint(the_foo: Foo):
    assert the_foo.one_field == request.json["one_field"]
    return Response(status=201)


if __name__ == '__main__':
    app.run()