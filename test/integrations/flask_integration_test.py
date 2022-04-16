from __future__ import annotations

import datetime
import json
from dataclasses import dataclass

import pytest
from flask import Flask, Response

from tsgen.integrations.flask_integration import typed, collect_endpoints

app = Flask(__name__)


@pytest.fixture
def client():
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


@dataclass
class Bar:
    one_field: datetime.datetime


@dataclass
class Foo:
    other_field: str
    sub_field: Bar


@app.route("/api/request_response_endpoint", methods=["POST"])
@typed()
def request_response_endpoint(the_foo: Foo) -> Bar:
    return Bar(one_field=the_foo.sub_field.one_field + datetime.timedelta(hours=12))


@app.route("/api/raw_response", methods=["POST"])
@typed()
def raw_response_endpoint(the_foo: Foo):
    if the_foo.other_field != "hello":
        return Response(status=400)
    return Response(status=201)


@app.route("/api/floatify", methods=["POST"])
@typed()
def floatify(the_foo: str) -> float:
    return float(the_foo.strip("#"))


def test_non_dataclass_payloads(client):
    response = client.post("/api/floatify", data=json.dumps("#3.5#"), content_type="application/json")
    assert response.status_code == 200
    assert 3.5 == response.json


def test_request_response(client):
    response: app.response_class = client.post(
        "/api/request_response_endpoint",
        data=json.dumps({
            "otherField": "hello",
            "subField": {
                "oneField": "2020-10-02T05:04:03Z",
            },
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    assert {"oneField": "2020-10-02T17:04:03Z"} == response.json


def test_raw_response(client):
    """view that returns responses still work like normal"""

    response: app.response_class = client.post(
        "/api/raw_response",
        data=json.dumps({
            "otherField": "hello",
            "subField": {
                "oneField": "2020-10-02T05:04:03Z",
            },
        }),
        content_type="application/json"
    )
    assert response.status_code == 201
    assert response.data == b''


def test_build_ts_api():
    files = collect_endpoints(app).get_files()
    assert len(files) == 1
    file_contents = list(files.values())[0]
    assert "Generated source code" in file_contents
    assert "class ApiError extends Error" in file_contents
    assert "interface Foo {" in file_contents
    assert "interface Bar {" in file_contents
    assert "const requestResponseEndpoint = async (theFoo: Foo)" in file_contents
