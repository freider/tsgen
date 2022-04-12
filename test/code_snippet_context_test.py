from tsgen.code_snippet_context import CodeSnippetContext


def test_snippet_context_single_snippet():
    ctx = CodeSnippetContext()
    ctx.add("foo", "dummy")
    assert "foo" in ctx
    assert ctx.top_level_snippets() == {"foo"}
    assert ctx.natural_order() == ["foo"]


def test_snippet_context_subcontext():
    ctx = CodeSnippetContext()
    ctx.add("foo", "dummy")
    sub = ctx.subcontext("foo")
    sub.add("bar", "dummy")
    ctx.add("baz", "dummy")
    assert "foo" in ctx
    assert "bar" in ctx
    assert ctx.top_level_snippets() == {"foo", "baz"}
    assert ctx.natural_order() == ["baz", "bar", "foo"]
