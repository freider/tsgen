import datetime

import pytest
import sanic
from sanic_testing.testing import SanicASGITestClient

from tsgen.integrations.sanic_integration import typed

app = sanic.Sanic("testapp")


@app.route("/foo")
@typed()
async def foo(req) -> datetime.date:
    return datetime.date.today()


@pytest.fixture
def client() -> SanicASGITestClient:
    yield app.asgi_client


@pytest.mark.asyncio
async def test_simple(client: SanicASGITestClient):
    _, res = await client.get("/foo")
    assert res.json == str(datetime.date.today())
