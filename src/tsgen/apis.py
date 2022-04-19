import dataclasses
import inspect
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Optional, get_type_hints, Collection, Callable, Protocol, Union

import jinja2

from tsgen.code_snippet_context import CodeSnippetContext
from tsgen.formatting import to_camel
from tsgen.output_templates import fetch, auto
from tsgen.types import get_type_tree, AbstractNode

TS_FILE_PATTERN = """// Generated source code - do not modify this file
{%- for entity in entities %}
{{entity}}
{% endfor %}
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


class _PreparedObject(Protocol):
    tsgen_info: TSGenFunctionInfo


PreparedCallableType = Union[Callable, _PreparedObject]


def prepare_function(func, localns=None, ignore_args: int = 0, ignore_kwargs: Collection[str] = ()) -> PreparedCallableType:
    annotations = get_type_hints(func)
    return_value_py_type = annotations.pop("return", None)
    return_type_tree = None
    if return_value_py_type is not None:
        return_type_tree = get_type_tree(return_value_py_type, localns=localns)

    ignore = set(list(inspect.signature(func).parameters.keys())[:ignore_args])
    ignore |= set(ignore_kwargs)

    arg_type_trees = {n: get_type_tree(t, localns=localns) for n, t in annotations.items() if n not in ignore}

    info = TSGenFunctionInfo(
        return_type_tree=return_type_tree,
        arg_type_trees=arg_type_trees
    )
    func.tsgen_info = info
    return func


def get_prepared_info(func: PreparedCallableType) -> TSGenFunctionInfo:
    # noinspection PyUnresolvedReferences
    return func.tsgen_info


def has_prepared_info(func: PreparedCallableType) -> bool:
    return hasattr(func, "tsgen_info")


class ClientBuilder:
    file_snippets: defaultdict[str, CodeSnippetContext]  # source module -> CodeSnippetContext

    def __init__(self, output_template=auto):
        self.file_snippets = defaultdict(CodeSnippetContext)
        self.output_template = output_template

    def build_ts_func(
        self,
        name: str,
        return_type_tree: Optional[AbstractNode],
        payload: Optional[tuple[str, AbstractNode]],
        url_pattern: str,
        url_args: list[str],
        method: str,
        ctx: CodeSnippetContext
    ):
        dependencies_ctx = ctx.subcontext(name)

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
            ts_return_type = return_type_tree.ts_repr(dependencies_ctx)
            return_expression = return_type_tree.ts_parse_dto(dependencies_ctx, "dto")
            response_dto_type = return_type_tree.dto_tree().ts_repr(dependencies_ctx)

        if payload:
            payload_name, payload_type_tree = payload
            ts_payload_type = payload_type_tree.ts_repr(dependencies_ctx)
            payload_arg_name = to_camel(payload_name)
            payload_expression = payload_type_tree.ts_create_dto(dependencies_ctx, payload_arg_name)
            ts_args.append((payload_arg_name, ts_payload_type))
        else:
            payload_expression = None

        ts_function_code = self.output_template.render_ts_accessor(
            ctx,
            name=name,
            ts_return_type=ts_return_type,
            response_dto_type=response_dto_type,
            payload_expression=payload_expression,
            ts_args=ts_args,
            method=method,
            url_pattern=url_pattern,
            return_expression=return_expression,
        )
        ctx.add(name, ts_function_code)
        return ts_function_code

    def add_endpoint(self, func: PreparedCallableType, url_pattern: str, url_args: list[str], method: str):
        import_name = func.__module__
        function_name = func.__name__
        info = get_prepared_info(func)
        ts_context = self.file_snippets[import_name]
        ts_function_name = to_camel(function_name)
        non_url_args = set(info.arg_type_trees.keys()) - set(url_args)
        assert len(non_url_args) <= 1
        payload: Optional[tuple[str, AbstractNode]] = None
        if non_url_args:
            payload_arg_name = list(non_url_args)[0]
            payload = (payload_arg_name, info.arg_type_trees[payload_arg_name])

        self.build_ts_func(
            ts_function_name,
            info.return_type_tree,
            payload,
            url_pattern,
            url_args,
            method,
            ts_context,
        )

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
        content = list(self.get_files().items())

        if not content:
            warnings.warn("No exported api endpoints - did you forget to annotate your views with @typed?")

        for dotpath, content in content:
            ts_filename = dotpath.replace(".", "/") + ".ts"
            file_path = root_path / ts_filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, "utf-8")
