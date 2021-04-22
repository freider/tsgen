import dataclasses
from typing import Optional, get_type_hints

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_camel
from tsgen.typetree import get_type_tree, AbstractNode

TS_FUNC_TEMPLATE = """
export const {{function_name}} = async ({% for arg_name, type in args %}{{arg_name}}: {{type}}{{ ", " if not loop.last else "" }}{% endfor %}): Promise<{{response_type_name}}> => {
  const response = await fetch(`{{url_pattern}}`, {
    method: '{{method}}'
    {%- if payload_expression != None %},
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({{payload_expression}}),
    {%- endif %}
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }
  {%- if response_type_name != "void" %}
  const dto = await response.json();
  return {{return_expression}};
  {%- endif %}
}
"""


@dataclasses.dataclass
class TSGenFunctionInfo:
    import_name: str
    ts_function_name: str
    return_type_tree: Optional[AbstractNode]

    payloads: dict[str, AbstractNode]


def build_ts_func(info: TSGenFunctionInfo, url_pattern: str, url_args: list[str], method: str, ctx: CodeSnippetContext):
    ts_args = []
    for arg in url_args:
        ts_arg_name = to_camel(arg)
        url_pattern = url_pattern.replace(f"<{arg}>", f"${{{ts_arg_name}}}")
        ts_args.append((ts_arg_name, "string"))

    if info.return_type_tree is None:
        ts_return_type = "void"
        return_expression = None
    else:
        ts_return_type = info.return_type_tree.ts_repr(ctx)
        return_expression = info.return_type_tree.ts_parse_dto(ctx, "dto")

    payload_args = set(info.payloads.keys()) - set(url_args)
    assert len(payload_args) <= 1
    if payload_args:
        payload_name = list(payload_args)[0]
        payload_type_tree = info.payloads[payload_name]
        ts_payload_type = payload_type_tree.ts_repr(ctx)
        payload_arg_name = to_camel(payload_name)
        payload_expression = payload_type_tree.ts_create_dto(ctx, payload_arg_name)
        ts_args.append((payload_arg_name, ts_payload_type))
    else:
        payload_expression = None

    ts_function_code = jinja2.Template(TS_FUNC_TEMPLATE).render({
        "function_name": info.ts_function_name,
        "response_type_name": ts_return_type,
        "payload_expression": payload_expression,
        "args": ts_args,
        "method": method,
        "url_pattern": url_pattern,
        "return_expression": return_expression,
    })
    return ts_function_code


def get_endpoint_info(func, localns=None) -> TSGenFunctionInfo:
    annotations = get_type_hints(func)
    return_value_py_type = annotations.pop("return", None)
    return_type_tree = None
    if return_value_py_type is not None:
        return_type_tree = get_type_tree(return_value_py_type, localns=localns)

    payloads = {n: get_type_tree(t, localns=localns) for n, t in annotations.items()}

    return TSGenFunctionInfo(
        import_name=func.__module__,
        ts_function_name=to_camel(func.__name__),
        return_type_tree=return_type_tree,
        payloads=payloads
    )
