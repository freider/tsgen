from collections import defaultdict
from functools import wraps
from pathlib import Path
from types import FunctionType

import click
import flask
import jinja2
import sys
from flask import request, jsonify, Blueprint

from tsgen.apis import build_ts_func, TSGenFunctionInfo, get_endpoint_info
from tsgen.interfaces import TSTypeContext
from tsgen.serde import parse_json, prepare_json


def typed():
    """Decorator to mark flask view function for typescript client support

    * Mark a view for typescript client code generation
    * Inject any dataclass argument by parsing the request payload
    * Allow the endpoint to return a dataclass as the top level return value

    :param import_name: Determines which file the generated typescript will go into
    """
    def generator(func: FunctionType):
        func._ts_gen = info = get_endpoint_info(func)

        @wraps(func)
        def new_f(**kwargs):
            # if dataclass arg has been specified, build one and add it as an arg
            new_kwargs = kwargs.copy()
            if info.payload:
                payload_name, payload_type = info.payload
                new_kwargs[payload_name] = parse_json(payload_type, request.json)

            resp = func(**new_kwargs)
            # always jsonify, so that endpoint can return a single dataclass
            if info.return_value_py_type is None:
                return resp  # unannotated return value returns raw response
            return jsonify(prepare_json(resp))

        return new_f

    return generator


TS_FILE_PATTERN = """// Generated source code - do not modify this file
{%- for entity in entities %}
{{entity}}
{% endfor %}
"""


def build_ts_api(app: flask.Flask):
    client_function_ts = defaultdict(list)
    ts_contexts = defaultdict(TSTypeContext)  # one context per ts file

    for rule in app.url_map.iter_rules():
        func = app.view_functions[rule.endpoint]

        if hasattr(func, "_ts_gen"):
            info: TSGenFunctionInfo = func._ts_gen
            import_name = info.import_name
            ts_context = ts_contexts[import_name]

            method = "GET"
            if "POST" in rule.methods:
                method = "POST"
            elif "PUT" in rule.methods:
                method = "PUT"

            url_pattern = rule.rule
            url_args = rule.arguments

            ts_function_code = build_ts_func(info, url_pattern, url_args, method, ts_context)
            client_function_ts[import_name].append(ts_function_code)

    file_contents = {}
    for import_name, client_functions in client_function_ts.items():
        ts_context = ts_contexts[import_name]
        interfaces = [
            ts_context.interfaces[ts_interface_name]
            for ts_interface_name in ts_context.natural_order()
        ]

        entities = interfaces + client_functions
        file_contents[import_name] = jinja2.Template(TS_FILE_PATTERN).render(entities=entities)

    return file_contents


def save_api_to_files(root_dir: str, file_contents: dict[str, str]):
    root_path = Path(root_dir)
    for dotpath, content in file_contents.items():
        ts_filename = dotpath.replace(".", "/") + ".ts"
        file_path = root_path / ts_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf8") as fp:
            fp.write(content)


def build_and_save_api(app: flask.Flask, root_dir: str):
    app.logger.info(f"Writing client code to {root_dir}")
    file_contents = build_ts_api(app)
    save_api_to_files(root_dir, file_contents)


cli_blueprint = Blueprint("tsgen", __name__)


def dev_reload_hook(app: flask.Flask, root_dir: str):
    """Rebuild typescript every time the flask app is (re)started

    Call this at module scope in your flask app main file.
    Only triggers in development mode.
    """
    if app.config["ENV"] != "development":
        return
    if sys.argv[-2:] == ["tsgen", "build"]:
        return  # when running the explicit generation command

    build_and_save_api(app, root_dir)


@cli_blueprint.cli.command("build")
@click.argument('root_dir', nargs=1)
def build(root_dir):
    build_and_save_api(flask.current_app, root_dir)
