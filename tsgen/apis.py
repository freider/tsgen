import dataclasses
from collections import defaultdict
from pathlib import Path
from types import FunctionType
from typing import Optional, get_type_hints

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_camel
from tsgen.types import get_type_tree, AbstractNode


TS_FILE_PATTERN = """// Generated source code - do not modify this file
{%- for entity in entities %}
{{entity}}
{% endfor %}
"""

TS_API_ERROR = """
export class ApiError extends Error {
  constructor(public message: string, public response: Response) {
    super(message);
    // https://github.com/Microsoft/TypeScript/wiki/FAQ#why-doesnt-extending-built-ins-like-error-array-and-map-work
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}
"""


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
  const dto: {{ response_dto_type }} = await response.json();
  return {{return_expression}};
  {%- endif %}
}
"""


@dataclasses.dataclass
class TSGenFunctionInfo:
    """Used for storing information about functions for later use

    Type hints are (often) easier to evaluate at the point they are declared
    so instead of storing python types directly, this can be used to store
    evaluated type trees for functions (see `tsgen.types`) for later use.
    """
    return_type_tree: Optional[AbstractNode]
    arg_type_trees: dict[str, AbstractNode]


def prepare_function(func, localns=None) -> TSGenFunctionInfo:
    annotations = get_type_hints(func)
    return_value_py_type = annotations.pop("return", None)
    return_type_tree = None
    if return_value_py_type is not None:
        return_type_tree = get_type_tree(return_value_py_type, localns=localns)

    arg_type_trees = {n: get_type_tree(t, localns=localns) for n, t in annotations.items()}

    info = TSGenFunctionInfo(
        return_type_tree=return_type_tree,
        arg_type_trees=arg_type_trees
    )
    func.tsgen_info = info
    return func


def get_prepared_info(func: FunctionType) -> TSGenFunctionInfo:
    # noinspection PyUnresolvedReferences
    return func.tsgen_info


def has_prepared_info(func: FunctionType) -> bool:
    return hasattr(func, "tsgen_info")


def build_ts_func(
        name: str,
        return_type_tree: Optional[AbstractNode],
        payload: Optional[tuple[str, AbstractNode]],
        url_pattern: str,
        url_args: list[str],
        method: str,
        ctx: CodeSnippetContext
    ):
    ts_args = []
    for arg in url_args:
        ts_arg_name = to_camel(arg)
        url_pattern = url_pattern.replace(f"<{arg}>", f"${{{ts_arg_name}}}")
        ts_args.append((ts_arg_name, "string"))

    if return_type_tree is None:
        ts_return_type = "void"
        return_expression = None
        response_dto_type = None
    else:
        ts_return_type = return_type_tree.ts_repr(ctx)
        return_expression = return_type_tree.ts_parse_dto(ctx, "dto")
        response_dto_type = return_type_tree.dto_tree().ts_repr(ctx)

    if payload:
        payload_name, payload_type_tree = payload
        ts_payload_type = payload_type_tree.ts_repr(ctx)
        payload_arg_name = to_camel(payload_name)
        payload_expression = payload_type_tree.ts_create_dto(ctx, payload_arg_name)
        ts_args.append((payload_arg_name, ts_payload_type))
    else:
        payload_expression = None

    ctx.add("ApiError", TS_API_ERROR)
    ts_function_code = jinja2.Template(TS_FUNC_TEMPLATE).render({
        "function_name": name,
        "response_type_name": ts_return_type,
        "response_dto_type": response_dto_type,
        "payload_expression": payload_expression,
        "args": ts_args,
        "method": method,
        "url_pattern": url_pattern,
        "return_expression": return_expression,
    })
    return ts_function_code


@dataclasses.dataclass()
class ClientBuilder:
    file_snippets: dict[str, CodeSnippetContext] = dataclasses.field(default_factory=lambda: defaultdict(CodeSnippetContext))

    def add_endpoint(self, func: FunctionType, url_pattern: str, url_args: list[str], method: str):
        import_name=func.__module__
        function_name=func.__name__
        info = get_prepared_info(func)
        ts_context = self.file_snippets[import_name]
        ts_function_name = to_camel(function_name)
        non_url_args = set(info.arg_type_trees.keys()) - set(url_args)
        assert len(non_url_args) <= 1
        payload: Optional[tuple[str, AbstractNode]] = None
        if non_url_args:
            payload_arg_name = list(non_url_args)[0]
            payload = (payload_arg_name, info.arg_type_trees[payload_arg_name])

        ts_function_code = build_ts_func(
            ts_function_name,
            info.return_type_tree,
            payload,
            url_pattern,
            url_args,
            method,
            ts_context,
        )
        ts_context.add(ts_function_name, ts_function_code)

    def get_files(self) -> dict[str, str]:
        """Get contents of all client files built

        :return: {<file name>: <file content string>}
        """
        file_contents = {}
        for import_name, ctx in self.file_snippets.items():
            all_snippets = [
                ctx.get_snippet(ts_interface_name)
                for ts_interface_name in ctx.natural_order()
            ]
            file_contents[import_name] = jinja2.Template(TS_FILE_PATTERN).render(entities=all_snippets)

        return file_contents

    def save_to_disk(self, root_dir: str):
        root_path = Path(root_dir)
        for dotpath, content in self.get_files().items():
            ts_filename = dotpath.replace(".", "/") + ".ts"
            file_path = root_path / ts_filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf8") as fp:
                fp.write(content)