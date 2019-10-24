# built-in
from copy import copy
from typing import Optional, Set, Type, Union

# external
from dephell_specifier import RangeSpecifier
from packaging import markers as packaging
from packaging.markers import Op, Value, Variable

# app
from ._constants import STRING_VARIABLES, VERSION_VARIABLES
from ._marker import BaseMarker, StringMarker, VersionMarker
from ._operation import AndMarker, Operation, OrMarker


class Markers:
    def __init__(self, markers: Union[list, str, 'Markers', packaging.Marker, None] = None):
        if not markers:
            self._marker = None
            return
        markers = self._parse(markers)
        if isinstance(markers, list):
            self._marker = self._convert(markers)
        else:
            self._marker = markers

    # properties

    @property
    def variables(self) -> Set[str]:
        if self._marker is None:
            return set()
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
            python = self.python_version
            if python is not None and not python.python_compat:
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
        if self._marker is None:
            return None
        return self._marker.get_string(name=name)

    def get_version(self, name: str) -> Optional[str]:
        if self._marker is None:
            return None
        return self._marker.get_version(name=name)

    def get_strings(self, name: str) -> Set[str]:
        if self._marker is None:
            return set()
        return self._marker.get_strings(name=name)

    def remove(self, name: str) -> None:
        if self._marker is None:
            return
        if isinstance(self._marker, Operation):
            self._marker.remove(name=name)
            return
        if self._marker.variable == name:
            self._marker = None

    def extract(self, name: str) -> Set[str]:
        strings = self.get_strings(name=name)
        self.remove(name=name)
        return strings

    def add(self, *, name: str, value, operator: str = '==') -> BaseMarker:
        if operator in {'in', 'not in'}:
            msg = 'unsupported operation: {}'
            raise ValueError(msg.format(operator))

        if name in STRING_VARIABLES:
            marker_cls = StringMarker   # type: Type[BaseMarker]
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
    def _parse(markers: Union[list, str, 'Markers', packaging.Marker]):
        if isinstance(markers, list):
            return markers

        if isinstance(markers, str):
            # https://github.com/pypa/packaging/blob/master/packaging/markers.py
            try:
                return packaging._coerce_parse_result(packaging.MARKER.parseString(markers))
            except packaging.ParseException as e:
                err_str = 'invalid marker: {0!r}, parse error at {1!r}'.format(
                    markers,
                    markers[e.loc:e.loc + 8],
                )
                raise packaging.InvalidMarker(err_str)

        if hasattr(markers, '_markers'):
            return markers._markers  # type: ignore

        if hasattr(markers, '_marker'):
            return markers._marker  # type: ignore

        raise ValueError('invalid marker')

    @classmethod
    def _convert(cls, markers: list) -> Union[Operation, BaseMarker]:
        groups = [[]]  # type: ignore # list of nodes and operations between them
        for marker in markers:
            # single marker
            if isinstance(marker, tuple):
                groups[-1].append(cls._convert_single_marker(*marker))
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
    def _convert_single_marker(lhs: Union[Value, Variable], op: Op,
                               rhs: Union[Value, Variable]) -> Union[Operation, BaseMarker]:
        var = lhs.value if type(lhs) is Variable else rhs.value
        if var in STRING_VARIABLES:
            return StringMarker(lhs=lhs, op=op, rhs=rhs)

        if var not in VERSION_VARIABLES:
            raise LookupError('unknown marker: {}'.format(var))

        if op.value == 'in' and type(rhs) is Value:
            values = rhs.value.split()
            markers = [VersionMarker(lhs=lhs, op=Op('=='), rhs=Value(value)) for value in values]
            return OrMarker(*markers)

        if op.value in {'in' 'not in'}:
            msg = 'unsupported operation for version marker {}: {}'
            raise ValueError(msg.format(var, op.value))

        return VersionMarker(lhs=lhs, op=op, rhs=rhs)

    @staticmethod
    def _deduplicate(group: list) -> list:
        new_group = []  # type: list
        for node in group:
            for merged_node in new_group:
                if type(node) is not type(merged_node):
                    continue
                if merged_node == node:
                    break
            else:
                new_group.append(node)
        return new_group

    def _merge(self, other, container) -> 'Markers':
        if isinstance(other, Markers):
            other = other._marker

        if self._marker is None:
            self._marker = other
            return self
        if other is None:
            return self

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

    def __and__(self, other: Union['Markers', BaseMarker, Operation]) -> 'Markers':
        """self & other
        """
        new = copy(self)
        new &= other
        return new

    def __iand__(self, other: Union['Markers', BaseMarker, Operation]) -> 'Markers':
        """self &= other
        """
        return self._merge(other=other, container=AndMarker)

    def __or__(self, other: Union['Markers', BaseMarker, Operation]) -> 'Markers':
        """self | other
        """
        new = copy(self)
        new |= other
        return new

    def __ior__(self, other: Union['Markers', BaseMarker, Operation]) -> 'Markers':
        """self |= other
        """
        return self._merge(other=other, container=OrMarker)

    def __repr__(self) -> str:
        return '{}({!r})'.format(type(self).__name__, self._marker or '')

    def __str__(self) -> str:
        if not self._marker:
            return ''
        result = str(self._marker)
        if result[0] == '(' and result[-1] == ')':
            return result[1:-1]
        return result

    def __bool__(self) -> bool:
        return self._marker is not None
