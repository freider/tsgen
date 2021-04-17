from dataclasses import dataclass

from flask import Flask

from tsgen.flask import typed

app = Flask(__name__)


@dataclass
class Bar:
    one_field: str


@dataclass
class Foo:
    other_field: str
    sub_field: Bar


@app.route("/api/foo", methods=["POST"])
@typed()
def foo(the_foo: Foo) -> Bar:
    return the_foo.sub_field


if __name__ == '__main__':
    app.run()
