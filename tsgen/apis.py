import dataclasses
from dataclasses import is_dataclass
from typing import Optional

import jinja2
from tsgen.formatting import to_camel

TS_FUNC_TEMPLATE = """
export const {{function_name}} = async ({% for arg_name, type in args %}{{arg_name}}: {{type}}{{ ", " if not loop.last else "" }}{% endfor %}): Promise<{{response_type_name}}> => {
  const resp = await fetch(`{{url_pattern}}`, {
    method: '{{method}}'
    {%- if payload_name != None %},
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({{payload_name}}),
    {%- endif %}
  });
  {%- if response_type_name != "void" %}
  const data: {{response_type_name}} = await resp.json();
  return data;
  {%- endif %}
}
"""


@dataclasses.dataclass
class TSGenFunctionInfo:
    import_name: str
    ts_function_name: str
    return_value_py_type: type

    payload: Optional[tuple[str, type]]


def build_ts_func(info: TSGenFunctionInfo, url_pattern, url_args, method, ts_context):
    ts_args = []
    for arg in url_args:
        ts_arg_name = to_camel(arg)
        url_pattern = url_pattern.replace(f"<{arg}>", f"${{{ts_arg_name}}}")
        ts_args.append((ts_arg_name, "string"))

    if info.return_value_py_type is None:
        ts_return_type = "void"  # TODO: test this on frontend
    else:
        ts_return_type = ts_context.py_to_ts_type(info.return_value_py_type)

    if info.payload:
        payload_name, payload_py_type = info.payload
        ts_payload_type = ts_context.py_to_ts_type(payload_py_type)
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
        "url_pattern": url_pattern
    })
    return ts_function_code


def get_endpoint_info(func):
    annotations = func.__annotations__.copy()
    return_value_py_type = annotations.pop("return", None)
    payloads = {n: t for n, t in annotations.items() if is_dataclass(t)}
    assert len(payloads) <= 1
    return TSGenFunctionInfo(
        import_name=func.__module__,
        ts_function_name=to_camel(func.__name__),
        return_value_py_type=return_value_py_type,
        payload=list(payloads.items())[0] if payloads else None
    )