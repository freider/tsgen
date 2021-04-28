import datetime

from flask import Flask

from tsgen import typed
from tsgen.flask_integration import build_ts_api

app = Flask(__name__)


@app.route("/some-dates/")
@typed()
def some_dates() -> list[datetime.datetime]:
    return [
        datetime.datetime.utcnow(),
        datetime.datetime.utcnow() + datetime.timedelta(1)
    ]


if __name__ == "__main__":
    client_builder = build_ts_api(app)
    for modulepath, content in client_builder.get_files().items():
        print(content)
