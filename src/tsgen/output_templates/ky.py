import jinja2

from tsgen.code_snippet_context import CodeSnippetContext

TS_FUNC_TEMPLATE = """
export async function {{function_name}}({% for arg_name, type in args %}{{arg_name}}: {{type}}{{ ", " if not loop.last else "" }}{% endfor %}): Promise<{{response_type_name}}> {
  const response = await ky.{{method | lower}}(
  {%- if payload_expression != None %}
    json: {{payload_expression}}
  {%- endif %});

  {%- if response_type_name != "void" %}
  {%- if return_expression == "dto" %}
  return await response.json();
  {%- else %}
  const dto: {{ response_dto_type }} = await response.json();
  return {{return_expression}};
  {%- endif %}
  {%- endif %}
}
"""

IMPORTS = """import ky from "ky";"""   # TODO: move to file template to ensure imports at top


def render_ts_accessor(
        ctx: CodeSnippetContext,
        *,
        name: str,
        ts_return_type: str,
        response_dto_type: str,
        payload_expression: str,
        ts_args: list[tuple[str, str]],  # argument name, argument type script type
        method: str,
        url_pattern: str,  # flask style url pattern e.g., "/foo/<arg>"
        return_expression: str,
):
    dependencies_ctx = ctx.subcontext(name)
    dependencies_ctx.add("imports", IMPORTS)

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

