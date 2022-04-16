from collections import defaultdict


class CircularDependency(Exception):
    def __init__(self, name):
        self.name = name


class CodeSnippetContext:
    """Keep track of side-effect code snippets (e.g. interface declarations)
    """
    def __init__(self):
        self._parent_snippet = None
        self._snippets: dict[str, str] = {}  # name -> code
        self._dependencies: dict[str, set[str]] = defaultdict(set)  # name -> set of names

    def add(self, name, code):
        assert name not in self._snippets or self._snippets[name] == code, f"Same snippet {name!r} but different code"
        self._snippets[name] = code
        if self._parent_snippet:
            self._dependencies[self._parent_snippet].add(name)

    def __contains__(self, item):
        return item in self._snippets

    def top_level_snippets(self) -> set[str]:
        """Get all snippets that no other types depend on"""
        without_dependents = set(self._snippets.keys())
        for parent, deps in self._dependencies.items():
            if parent is not None:
                without_dependents -= set(deps)
        return without_dependents

    def natural_order(self) -> list[str]:
        """Get snippets in a natural order of definition

        Topologically sorted with leaves first and top level (root) snippets last
        Order between siblings is currently undefined
        """
        ret = []
        for top in sorted(self.top_level_snippets()):
            deps = self.topological_dependencies(top)
            for d in deps:
                if d not in ret:
                    ret.append(d)
        return ret

    def topological_dependencies(self, name: str) -> list[str]:
        """
        Get all snippet dependency types in topological order

        :param name: The name of the snippet
        :return: List of names, in leaf -> root order
        :raises: CircularDependency if a snippet directly or indirectly depends on itself (currently not supported)

        """
        used = set()
        result: list[str] = []

        def rec(t, ancestors):
            if t in ancestors:
                raise CircularDependency(t)
            if t in used:
                return
            unused = self._dependencies[t] - used
            if not unused:  # no unused dependency, this is a leaf!
                result.append(t)
                used.add(t)
                return

            for dep in unused:
                rec(dep, ancestors | {t})

        while True:
            rec(name, set())
            if result[-1] == name:  # toplevel dependency resolved
                break

        return result

    def subcontext(self, parent_snippet):
        """Get a shallow copy of the context with a parent snippet set

        A snippet with parent snippet set will automatically add
        dependencies between that parent and any added snippets.
        Anything added to a subcontext is implicitly added to
        its parent context as well, so all snippets will exist
        in the root context.
        """
        ctx = CodeSnippetContext()
        ctx._snippets = self._snippets  # ref to parent context
        ctx._dependencies = self._dependencies  # ref to parent context
        ctx._parent_snippet = parent_snippet
        return ctx

    def get_snippet(self, name):
        return self._snippets[name]
