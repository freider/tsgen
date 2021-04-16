import dataclasses
import re
from collections import defaultdict
from dataclasses import is_dataclass
from functools import wraps
from types import FunctionType, GenericAlias
from typing import Optional

import flask
import jinja2
from flask import Blueprint, jsonify, request

bp = Blueprint("tsgen", __name__)


@dataclasses.dataclass
class TSGenFunctionInfo:
    import_name: str
    ts_function_name: str
    return_value_py_type: type

    payload: Optional[tuple[str, type]]


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


TS_FUNC_TEMPLATE = """
export const {{function_name}} = async ({% for arg_name, type in args %}{{arg_name}}: {{type}}{{ ", " if not loop.last else "" }}{% endfor %}): Promise<{{response_type_name}}> => {
  const resp = await fetch(`{{url_pattern}}`, {
    method: '{{method}}'
    {%- if payload_name != None %}
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({{payload_name}}),
    {%- endif %}
  });
  const data: {{response_type_name}} = await resp.json();
  return data;
}
"""


TS_INTERFACE_TEMPLATE = """
interface {{name}} {
{%- for field_name, type in fields %}
  {{field_name}}: {{type}};
{%- endfor %}
}
"""


def to_snake(s: str):
    def replacer(g: re.Match) -> str:
        gs = g.group(0).lstrip("_")
        return gs[0].upper() + gs[1:]

    return re.sub(r"(^|[_])[a-zA-Z]", replacer, s)


def to_camel(s: str):
    s = to_snake(s)
    return s[0].lower() + s[1:]


class CircularDependency(Exception):
    def __init__(self, name):
        self.name = name


class TSTypeContext:
    """
    Context object for building typescript interfaces from dataclasses

    Keeps track of inter-dependencies between those interfaces
    """
    def __init__(self):
        self.base_types: dict[type, str] = {
            str: "string",
            int: "number",
            float: "number",
            bool: "boolean",
        }
        self.dataclass_types: dict[type, str] = {}
        self.interfaces: dict[str, str] = {}
        self.dependencies: dict[str, set[str]] = defaultdict(set)

    def top_level_interfaces(self) -> set[str]:
        without_dependents = set(self.interfaces.keys())
        for parent, deps in self.dependencies.items():
            if parent is not None:
                without_dependents -= set(deps)
        return without_dependents

    def natural_order(self) -> list[str]:
        ret = []
        for top in self.top_level_interfaces():
            deps = self.topological_dependencies(top)
            for d in deps:
                if d not in ret:
                    ret.append(d)
        return ret

    def topological_dependencies(self, ts_typename: str) -> list[str]:
        """
        Get all interfaces that a typescript type depends on, in topological order

        :param ts_typename: The name of the typescript type
        :return: List of typescript interfaces names, in leaf -> root order
        :raises: CircularDependency if a type direcltly or indirectly depends on itself (currently not supported)

        """
        used = set()
        result: list[str] = []

        def rec(t, ancestors):
            if t in ancestors:
                raise CircularDependency(t)
            if t in used:
                return
            unused = self.dependencies[t] - used
            if not unused:  # no unused dependency, this is a leaf!
                result.append(t)
                used.add(t)
                return

            for dep in unused:
                rec(dep, ancestors | {t})

        while True:
            rec(ts_typename, set())
            if result[-1] == ts_typename:  # toplevel dependency resolved
                break

        return result

    def py_to_js_type(self, t: type, parent_ts_type: Optional[str] = None):
        if is_dataclass(t):
            if t not in self.dataclass_types:
                self._add_interface(t)
            ts_name = self.dataclass_types[t]
            self.dependencies[parent_ts_type].add(ts_name)
            return ts_name
        if isinstance(t, GenericAlias) and t.__origin__ == list:
            #  e.g. list[int]
            return self._list_type(t, parent_ts_type)
        return self.base_types[t]

    def _list_type(self, t: GenericAlias, parent_ts_type: Optional[str] = None):
        assert len(t.__args__) == 1
        argtype = t.__args__[0]
        subtype = self.py_to_js_type(argtype, parent_ts_type)
        return f"{subtype}[]"

    def _add_interface(self, dc):
        typename = to_snake(dc.__name__)

        assert dc not in self.dataclass_types and typename not in self.dataclass_types.values()
        self.dataclass_types[dc] = typename
        dc_fields = dataclasses.fields(dc)
        fields = []

        for field in dc_fields:
            field_ts_type = self.py_to_js_type(field.type, typename)
            field_ts_name = to_camel(field.name)
            fields.append((field_ts_name, field_ts_type))

        declaration_template = jinja2.Template(TS_INTERFACE_TEMPLATE)
        self.interfaces[typename] = declaration_template.render(
            name=typename,
            fields=fields
        )


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


def build_ts_func(info: TSGenFunctionInfo, formatted_url, url_args, method, ts_context):
    ts_args = []
    for arg in url_args:
        ts_arg_name = to_camel(arg)
        formatted_url = formatted_url.replace(f"<{arg}>", f"${{{ts_arg_name}}}")
        ts_args.append((ts_arg_name, "string"))  # TODO: add support for typed flask arguments i.e. <foo:int>

    ts_return_type = ts_context.py_to_js_type(info.return_value_py_type)

    if info.payload:
        payload_name, payload_py_type = info.payload
        ts_payload_type = ts_context.py_to_js_type(payload_py_type)
        payload_arg_name = to_camel(payload_name)
        ts_args.append((payload_arg_name, ts_payload_type))
    else:
        payload_arg_name = None

    ts_function_code = jinja2.Template(TS_FUNC_TEMPLATE).render({
        "function_name": info.ts_function_name,
        "response_type_name": ts_return_type,
        "payload_name": payload_arg_name,
        "args": ts_args,
        "method": method,
        "url_pattern": formatted_url
    })
    return ts_function_code


@bp.cli.command("build")
def build():
    build_ts_api()
