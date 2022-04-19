from collections import defaultdict


class CircularDependency(Exception):
    def __init__(self, nodes):
        self.nodes = nodes


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

    def topological_dependencies(self, root_snippet: str) -> list[str]:
        """
        Get all snippet dependencies in topological order, leaf(s) -> root

        * Ties are sorted alphabetically by snippet name
        * Includes the root snippet (always the last one).

        :param name: The name of the snippet
        :return: List of names, in leaf -> root order
        :raises: CircularDependency if a snippet directly or indirectly depends on itself (currently not supported)
        """

        remaining_nodes = self._snippets.keys()
        topological_snippets = []
        result_set = set()

        while remaining_nodes:
            leafs = []
            for n in sorted(remaining_nodes):
                remaining_deps = self._dependencies[n] - result_set
                if not remaining_deps:
                    leafs.append(n)
            if not leafs:
                raise CircularDependency(remaining_nodes)
            topological_snippets += leafs
            result_set |= set(leafs)
            remaining_nodes -= set(leafs)

        # extract nodes in subtree under root_snippet
        subtree = set()

        def rec(n):
            if n in subtree:
                return
            subtree.add(n)
            for d in self._dependencies[n]:
                rec(d)
        rec(root_snippet)

        return [n for n in topological_snippets if n in subtree]

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
