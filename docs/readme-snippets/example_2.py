from flask import Flask
from dataclasses import dataclass
from tsgen import typed
from tsgen.flask_integration import build, build_ts_api

app = Flask(__name__)


@dataclass()
class Bar:
    something: str


@app.route("/bar/", methods=["POST"])
@typed()
def create_bar(bar: Bar) -> str:
    return f"hello {bar.something}"


if __name__ == "__main__":
    client_builder = build_ts_api(app)
    for modulepath, content in client_builder.get_files().items():
        print(content)
