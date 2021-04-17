from collections import defaultdict
from functools import wraps
from types import FunctionType

import flask
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


def build_ts_api():
    generated_ts = defaultdict(list)
    ts_contexts = defaultdict(TSTypeContext)  # one context per ts file

    for rule in flask.current_app.url_map.iter_rules():
        func = flask.current_app.view_functions[rule.endpoint]

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
            generated_ts[import_name].append(ts_function_code)

    for import_name, ts_snippets in generated_ts.items():
        ts_context = ts_contexts[import_name]
        print(f">>> File: {import_name}.ts\n")

        interfaces = [
            ts_context.interfaces[ts_interface_name]
            for ts_interface_name in ts_context.natural_order()
        ]

        print("\n\n".join(interfaces + ts_snippets))
        print()


cli_blueprint = Blueprint("tsgen", __name__)


@cli_blueprint.cli.command("build")
def build():
    build_ts_api()

