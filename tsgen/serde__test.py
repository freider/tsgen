import dataclasses

from tsgen.serde import parse_json, prepare_json


def test_parse_json_list():
    assert ["hello", "world"] == parse_json(list[str], ["hello", "world"])


def test_parse_nested_dataclass():
    @dataclasses.dataclass
    class Bar:
        string_field: str

    @dataclasses.dataclass
    class Foo:
        number_field: int
        sub_field: Bar

    assert Foo(1337, sub_field=Bar("elite")) == parse_json(Foo, {"numberField": 1337, "subField": {"stringField": "elite"}})


def test_parse_json_list_of_objects():
    @dataclasses.dataclass
    class Foo:
        bar: str

    assert [Foo(bar="baz")] == parse_json(list[Foo], [{"bar": "baz"}])


def test_prepare_json_nested_dataclass():
    @dataclasses.dataclass
    class Bar:
        string_field: str

    @dataclasses.dataclass
    class Foo:
        number_field: int
        sub_field: Bar

    assert {"numberField": 1337, "subField": {"stringField": "elite"}} == prepare_json(Foo(number_field=1337, sub_field=Bar("elite")))
