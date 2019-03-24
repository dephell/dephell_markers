# built-in
from copy import copy
from typing import Optional, Union, Set

# external
from dephell_specifier import RangeSpecifier
from packaging import markers as packaging
from packaging.markers import Variable

# app
from ._marker import BaseMarker, StringMarker, VersionMarker
from ._operation import OrMarker, AndMarker, Operation
from ._constants import STRING_VARIABLES, VERSION_VARIABLES


class Markers:
    def __init__(self, markers: Union[list, str, 'Markers', packaging.Marker]):
        markers = self._parse(markers)
        if isinstance(markers, list):
            self._marker = self._convert(markers)
        else:
            self._marker = markers

    # properties

    @property
    def variables(self) -> Set[str]:
        if isinstance(self._marker, BaseMarker):
            return {self._marker.variable}
        return self._marker.variables

    @property
    def compat(self) -> bool:
        for variable in self.variables:
            if variable in STRING_VARIABLES:
                if self.get_string(variable) is None:
                    return False
            if variable in VERSION_VARIABLES:
                if self.get_version(variable) is None:
                    return False

        if 'python_version' in self.variables:
            if not self.python_version.python_compat:
                return False
        return True

    @property
    def python_version(self) -> Optional[RangeSpecifier]:
        value = self.get_version('python_version')
        if value is not None:
            return RangeSpecifier(value)
        return None

    @property
    def extra(self) -> Optional[str]:
        return self.get_string('extra')

    # public methods

    def get_string(self, name: str) -> Optional[str]:
        return self._marker.get_string(name=name)

    def get_version(self, name: str) -> Optional[str]:
        return self._marker.get_version(name=name)

    def add(self, *, name: str, value, operator: str = '==') -> BaseMarker:
        if operator in {'in', 'not in'}:
            msg = 'unsupported operation: {}'
            raise ValueError(msg.format(operator))

        if name in STRING_VARIABLES:
            marker_cls = StringMarker
        elif name in VERSION_VARIABLES:
            marker_cls = VersionMarker
        marker = marker_cls(
            lhs=packaging.Variable(name),
            op=packaging.Op(operator),
            rhs=packaging.Value(value),
        )
        self &= marker
        return marker

    # private methods

    @staticmethod
    def _parse(markers: Union[list, str, 'Markers', packaging.Marker]) -> list:
        if isinstance(markers, list):
            return markers

        if isinstance(markers, str):
            # https://github.com/pypa/packaging/blob/master/packaging/markers.py
            try:
                return packaging._coerce_parse_result(packaging.MARKER.parseString(markers))
            except packaging.ParseException as e:
                err_str = "invalid marker: {0!r}, parse error at {1!r}".format(
                    markers,
                    markers[e.loc:e.loc + 8],
                )
                raise packaging.InvalidMarker(err_str)

        if hasattr(markers, '_markers'):
            return markers._markers

        if hasattr(markers, '_marker'):
            return markers._marker

        raise ValueError('invalid marker')

    @classmethod
    def _convert(cls, markers: list) -> Operation:
        groups = [[]]  # list of nodes and operations between them
        for marker in markers:
            # single marker
            if isinstance(marker, tuple):
                lhs, op, rhs = marker
                var = lhs.value if isinstance(lhs, Variable) else rhs.value
                if var in STRING_VARIABLES:
                    marker_cls = StringMarker
                elif var in VERSION_VARIABLES:
                    if op.value in {'in', 'not in'}:
                        msg = 'unsupported operation for version marker {}: {}'
                        raise ValueError(msg.format(var, op.value))
                    marker_cls = VersionMarker
                else:
                    raise LookupError('unknown marker: {}'.format(var))
                groups[-1].append(marker_cls(lhs=lhs, op=op, rhs=rhs))
                continue

            # sub-collection
            if isinstance(marker, list):
                groups[-1].append(cls._convert(marker))
                continue

            # operation
            if isinstance(marker, str):
                if marker == 'or':
                    groups.append([])
                continue

            raise LookupError('invalid node type')

        new_groups = []
        for group in groups:
            if len(group) == 1:
                new_groups.append(group[0])
            elif len(group) > 1:
                new_groups.append(AndMarker(*cls._deduplicate(group)))

        if len(new_groups) == 1:
            return new_groups[0]
        return OrMarker(*cls._deduplicate(new_groups))

    @staticmethod
    def _deduplicate(group: list) -> list:
        new_group = []
        for node in group:
            for merged_node in new_group:
                if type(node) is not type(merged_node):
                    continue
                if merged_node == node:
                    break
            else:
                new_group.append(node)
        return new_group

    def _merge(self, other, container):
        if isinstance(other, Markers):
            other = other._marker

        # do not add new node if it's already added
        if isinstance(self._marker, Operation):
            if other in self._marker.nodes:
                return self
        if isinstance(self._marker, BaseMarker) and isinstance(other, BaseMarker):
            if other == self._marker:
                return self

        if isinstance(other, (Operation, BaseMarker)):
            self._marker = container(self._marker, other)
            return self
        return NotImplemented

    # magic methods

    def __and__(self, other):
        """self & other
        """
        new = copy(self)
        new &= other
        return new

    def __iand__(self, other: Union['Markers', BaseMarker, Operation]):
        """self &= other
        """
        return self._merge(other=other, container=AndMarker)

    def __or__(self, other):
        """self | other
        """
        new = copy(self)
        new |= other
        return new

    def __ior__(self, other: Union['Markers', BaseMarker, Operation]):
        """self |= other
        """
        return self._merge(other=other, container=OrMarker)

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self._marker)

    def __str__(self):
        return str(self._marker).strip('()')
