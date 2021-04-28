import os
from functools import wraps
from pathlib import Path
from types import FunctionType

import click
import flask
import sys
from flask import request, jsonify, Blueprint, Flask

from tsgen.apis import prepare_function, ClientBuilder, get_prepared_info, has_prepared_info


def typed(localns=None):
    """Decorator to mark flask view function for typescript client support

    * Mark a view for typescript client code generation
    * Inject an attached json body as a typed argument
    * Allow for custom data <-> json conversions in injected and returned data
    * Always return json for return-value-annotated views
    """
    def generator(func: FunctionType):
        prepare_function(func, localns=localns)
        info = get_prepared_info(func)

        @wraps(func)
        def new_f(**kwargs):
            # if dataclass arg has been specified, build one and add it as an arg
            new_kwargs = kwargs.copy()
            payload_args = set(info.arg_type_trees.keys()) - set(kwargs.keys())
            if payload_args:
                payload_name = list(payload_args)[0]
                payload_tree = info.arg_type_trees[payload_name]
                new_kwargs[payload_name] = payload_tree.parse_dto(request.json)

            response = func(**new_kwargs)
            if info.return_type_tree is None:
                return response  # unannotated return value returns raw response
            return jsonify(info.return_type_tree.create_dto(response))

        return new_f

    return generator


def build_ts_api(app: flask.Flask) -> ClientBuilder:
    """Generate typescript clients and types for a flask app

    :param app: Flask app with @typed()-decorated api routes
    :return: dictionary {filename: typescript_source_code}
    """
    client_builder = ClientBuilder()

    for rule in app.url_map.iter_rules():
        func = app.view_functions[rule.endpoint]

        if has_prepared_info(func):
            method = "GET"
            if "POST" in rule.methods:
                method = "POST"
            elif "PUT" in rule.methods:
                method = "PUT"
            url_pattern = rule.rule
            url_args = rule.arguments

            client_builder.add_endpoint(func, url_pattern, url_args, method)

    return client_builder


def build_and_save_api(app: flask.Flask, root_dir: str = None):
    if root_dir is None:
        root_dir = os.environ.get("TSGEN_OUTPUT_DIR")
    if not root_dir:
        root_dir = (Path(app.instance_path) / "tsgen_output").as_posix()

    app.logger.info(f"Writing client code to {root_dir}")
    client_builder = build_ts_api(app)
    client_builder.save_to_disk(root_dir)


def dev_reload_hook(app: flask.Flask, root_dir: str = None):
    """Rebuild typescript every time the flask app is (re)started

    Call this at module scope in your flask app main file.
    Only triggers in development mode.
    """
    # noinspection PyBroadException
    try:
        if app.config["ENV"] != "development":
            return
        if "tsgen build" in " ".join(sys.argv):
            return  # when running the explicit generation command

        build_and_save_api(app, root_dir)
    except Exception:
        app.logger.exception("An error occurred during tsgen reload hook")


cli_blueprint = Blueprint("tsgen", __name__)


@cli_blueprint.cli.command("build")
@click.option('--output-dir', default=None)
def build(output_dir):
    build_and_save_api(flask.current_app, output_dir)


def init_tsgen(app: Flask):
    app.register_blueprint(cli_blueprint)
