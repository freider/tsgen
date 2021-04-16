from collections import defaultdict
from dataclasses import is_dataclass
from functools import wraps
from types import FunctionType

import flask
from flask import request, jsonify, Blueprint
from tsgen.apis import build_ts_func, TSGenFunctionInfo
from tsgen.interfaces import TSTypeContext
from tsgen.formatting import to_camel


def typed(import_name):
    def generator(func: FunctionType):
        annotations = func.__annotations__.copy()
        return_value_py_type = annotations.pop("return")
        payloads = {n: t for n, t in annotations.items() if is_dataclass(t)}
        assert len(payloads) <= 1

        info = TSGenFunctionInfo(
            import_name=import_name,
            ts_function_name=to_camel(func.__name__),
            return_value_py_type=return_value_py_type,
            payload=list(payloads.items())[0] if payloads else None
        )
        func._ts_gen = info

        @wraps(func)
        def new_f(**kwargs):
            # if dataclass arg has been specified, build one and add it as an arg
            new_kwargs = kwargs.copy()
            if info.payload:
                payload_name, payload_type = info.payload
                # TODO: unpack nested json to dataclasses
                new_kwargs[payload_name] = payload_type(**request.json)

            resp = func(**new_kwargs)
            # always jsonify, so that endpoint can return a single dataclass
            return jsonify(resp)

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

            formatted_url = rule.rule
            url_args = rule.arguments

            ts_function_code = build_ts_func(info, formatted_url, url_args, method, ts_context)
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


cli_commands = Blueprint("tsgen", __name__)

@cli_commands.cli.command("build")
def build():
    build_ts_api()

