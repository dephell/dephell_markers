# built-in
from typing import Optional, Set

from .._cached_property import cached_property


class Operation:
    op = ''
    sep = ''

    def __init__(self, *nodes):
        new_nodes = []
        for node in nodes:
            if isinstance(node, type(self)):
                # get nodes from child node if this node has the same type
                new_nodes.extend(node.nodes)
            else:
                # if this is single marker or other Operation then just append
                new_nodes.append(node)
        self.nodes = new_nodes

    @cached_property
    def variables(self) -> Set[str]:
        variables = set()  # type: Set[str]
        for node in self.nodes:
            if isinstance(node, Operation):
                variables.union(node.variables)
            else:
                variables.add(node.variable)
        return variables

    def _get_values(self, name: str):
        raise NotImplementedError

    def get_string(self, name: str) -> Optional[str]:
        values = self._get_values(name=name)
        if values is None:
            return None

        # if var is equal only one value then return this value
        equal = set()
        non_equal = set()
        for op, val in values:
            if op == '==':
                equal.add(val)
            else:
                non_equal.add(val)
        if len(equal) == 1:
            val = next(iter(equal))
            if val not in non_equal:
                return val

        # TODO: support `in` operations
        return None

    def get_version(self, name: str) -> Optional[str]:
        values = self._get_values(name=name)
        if values is None:
            return None
        return self.sep.join(sorted(op + val for op, val in values))

    # magic methods

    def __eq__(self, other):
        if not isinstance(other, Operation):
            return NotImplemented
        return self.op == other.op and set(self.nodes) == set(other.nodes)

    def __hash__(self):
        return hash(self.nodes)

    def __str__(self):
        sep = ' ' + self.op + ' '
        return '(' + sep.join(map(str, self.nodes)) + ')'

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__,
            ', '.join(map(repr, self.nodes)),
        )
