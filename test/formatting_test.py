from tsgen.formatting import to_pascal


def test_to_snake():
    assert to_pascal("foo") == "Foo"
    assert to_pascal("foo_bar") == "FooBar"
    assert to_pascal("_nisse") == "Nisse"
