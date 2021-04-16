import dataclasses
from typing import Optional

import jinja2
from tsgen.formatting import to_camel

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


@dataclasses.dataclass
class TSGenFunctionInfo:
    import_name: str
    ts_function_name: str
    return_value_py_type: type

    payload: Optional[tuple[str, type]]


def build_ts_func(info: TSGenFunctionInfo, formatted_url, url_args, method, ts_context):
    ts_args = []
    for arg in url_args:
        ts_arg_name = to_camel(arg)
        formatted_url = formatted_url.replace(f"<{arg}>", f"${{{ts_arg_name}}}")
        ts_args.append((ts_arg_name, "string"))  # TODO: add support for typed flask arguments i.e. <foo:int>

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
        "url_pattern": formatted_url
    })
    return ts_function_code