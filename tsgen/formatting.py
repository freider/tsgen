import re


def to_snake(s: str):
    def replacer(g: re.Match) -> str:
        gs = g.group(0).lstrip("_")
        return gs[0].upper() + gs[1:]

    return re.sub(r"(^|[_])[a-zA-Z]", replacer, s)


def to_camel(s: str):
    s = to_snake(s)
    return s[0].lower() + s[1:]