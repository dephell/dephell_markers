# built-in
from typing import Optional

# external
from dephell_specifier import Specifier
from packaging.markers import Op, Value
from packaging.version import parse

# app
from .._cached_property import cached_property
from ._base import BaseMarker
from .._constants import REVERSED_OPERATIONS


class VersionMarker(BaseMarker):

    def __attrs_post_init__(self):
        if isinstance(self.lhs, Value):
            self.lhs, self.rhs = self.rhs, self.lhs
            self.op = Op(value=REVERSED_OPERATIONS[self.op.value])
        super().__attrs_post_init__()

    def get_string(self, name: str) -> Optional[str]:
        return None

    def get_version(self, name: str) -> Optional[str]:
        if name != self.variable:
            return None
        return self.operator + self.value

    @cached_property
    def version(self):
        return parse(self.value)

    @cached_property
    def specifier(self):
        return Specifier(self.op.value + self.value)

    def __str__(self):
        return '{lhs} {op} "{rhs}"'.format(
            lhs=self.lhs.value,
            op=self.op.value,
            rhs=self.rhs.value,
        )

    def __add__(self, other: 'VersionMarker'):
        try:
            spec = self.specifier + other.specifier
        except TypeError:
            return NotImplemented
        return type(self)(
            lhs=self.lhs,
            op=Op(value=spec.operator),
            rhs=Value(value=str(spec.version)),
        )
