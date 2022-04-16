import datetime
from uuid import UUID

import pytest
import sanic
from sanic_testing.testing import SanicASGITestClient

from tsgen.integrations.sanic_integration import typed

app = sanic.Sanic("testapp")

DUMMY_DATE = datetime.date(2020, 12, 31)


@app.route("/foo")
@typed()
async def foo(req) -> datetime.date:
    return DUMMY_DATE


@app.route("/bar/<arg>", methods={sanic.HTTPMethod.POST})
@typed()
async def bar(req: sanic.Request, arg) -> datetime.date:
    return DUMMY_DATE


@app.route("/baz/<arg:uuid>")
@typed()
async def baz(req, arg: UUID) -> str:
    return str(arg)


@pytest.fixture
def client() -> SanicASGITestClient:
    yield app.asgi_client


@pytest.mark.asyncio
async def test_simple(client: SanicASGITestClient):
    _, res = await client.get("/foo")
    assert res.json == str(DUMMY_DATE)

    _, res = await client.post("/bar/nisse")
    assert res.json == str(DUMMY_DATE)

    _, res = await client.get("/baz/9b29e304-7d96-498c-9e7f-ac43cab82d53")
    assert res.json == "9b29e304-7d96-498c-9e7f-ac43cab82d53"

