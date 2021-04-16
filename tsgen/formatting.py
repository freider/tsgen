import re


def to_pascal(s: str):
    def replacer(g: re.Match) -> str:
        gs = g.group(0).lstrip("_")
        return gs[0].upper() + gs[1:]

    return re.sub(r"(^|[_])[a-zA-Z]", replacer, s)


def to_camel(s: str):
    s = to_pascal(s)
    return s[0].lower() + s[1:]
