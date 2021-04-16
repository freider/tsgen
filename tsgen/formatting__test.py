from tsgen.formatting import to_snake


def test_to_snake():
    assert to_snake("foo") == "Foo"
    assert to_snake("foo_bar") == "FooBar"
    assert to_snake("_nisse") == "Nisse"