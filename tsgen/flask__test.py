import json
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


def test_request_response():
    with app.test_client() as client:
        resp: app.response_class = client.post(
            "/api/foo",
            data=json.dumps({
                "otherField": "hello",
                "subField": {
                    "oneField": "world",
                },
            }),
            content_type='application/json'
        )
        assert resp.status_code == 200
        assert {"oneField": "world"} == resp.json
