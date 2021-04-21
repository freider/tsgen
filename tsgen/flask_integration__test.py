from __future__ import annotations
import json
from dataclasses import dataclass

import pytest
from flask import Flask, Response

from tsgen.flask_integration import typed

test_app = Flask(__name__)


@pytest.fixture
def client():
    test_app.config['TESTING'] = True

    with test_app.test_client() as client:
        yield client


@dataclass
class Bar:
    one_field: str


@dataclass
class Foo:
    other_field: str
    sub_field: Bar


@test_app.route("/api/request_response_endpoint", methods=["POST"])
@typed()
def request_response_endpoint(the_foo: Foo) -> Bar:
    return the_foo.sub_field


def test_request_response(client):
    response: test_app.response_class = client.post(
        "/api/request_response_endpoint",
        data=json.dumps({
            "otherField": "hello",
            "subField": {
                "oneField": "world",
            },
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    assert {"oneField": "world"} == response.json


@test_app.route("/api/raw_response", methods=["POST"])
@typed()
def raw_response_endpoint(the_foo: Foo):
    if the_foo.other_field != "hello":
        return Response(status=400)
    return Response(status=201)


def test_raw_response(client):
    response: test_app.response_class = client.post(
        "/api/raw_response",
        data=json.dumps({
            "otherField": "hello",
            "subField": {
                "oneField": "world",
            },
        }),
        content_type="application/json"
    )
    assert response.status_code == 201
    assert response.data == b''
