# external
import pytest

# project
from dephell_markers import Markers


@pytest.mark.parametrize('marker, value', [
    ('os_name == "posix"', 'posix'),
    ('os_name == "posix" and os_name == "posix"', 'posix'),
    ('os_name == "posix" or os_name == "posix"', 'posix'),
    ('os_name == "posix" and python_version >= "2.7"', 'posix'),

    ('os_name == "posix" and os_name == "nt"', None),
    ('os_name == "nt" and os_name != "nt"', None),
    ('os_name == "posix" or python_version >= "2.7"', None),
])
def test_get_string(marker, value):
    m = Markers(marker)
    v = m.get_string(name='os_name')
    assert v == value


@pytest.mark.parametrize('marker, value', [
    ('python_version == "2.4"', '==2.4'),
    ('python_version >= "2.4" and python_version <= "2.7"', '<=2.7,>=2.4'),
    ('python_version >= "2.4" or python_version <= "2.7"', '<=2.7 || >=2.4'),
    ('python_version == "2.4" and os_name == "linux"', '==2.4'),

    # `or` contains different marker
    ('python_version == "2.4" or os_name == "linux"', None),
    # no needed marker
    ('os_name == "linux"', None),
])
def test_get_version(marker, value):
    m = Markers(marker)
    v = m.get_version(name='python_version')
    assert v == value


def test_python_version():
    m = Markers('python_version >= "2.4" and python_version <= "2.7"')
    v = m.python_version
    assert '2.4' in v
    assert '2.5' in v
    assert '2.3' not in v
    assert '3.4' not in v


def test_add_python_version():
    m = Markers('python_version >= "2.4"')
    assert '3.2' in m.python_version
    m.add(name='python_version', operator='<=', value='2.7')
    v = m.python_version
    assert '2.4' in v
    assert '2.5' in v
    assert '2.3' not in v
    assert '3.4' not in v


@pytest.mark.parametrize('given, expected', [
    (
        'python_version >= "2.4" and python_version <= "2.7"',
        'python_version >= "2.4" and python_version <= "2.7"',
    ),
    (
        '(python_version >= "2.4" and python_version <= "2.7")',
        'python_version >= "2.4" and python_version <= "2.7"',
    ),
    (
        '(python_version >= "2.4" or python_version <= "2.7") or os_name == "linux"',
        'python_version >= "2.4" or python_version <= "2.7" or os_name == "linux"',
    ),
    (
        '(python_version>="2.4" and python_version <= "2.7") or os_name == "linux"',
        'python_version >= "2.4" and python_version <= "2.7" or os_name == "linux"',
    ),
])
def test_str(given, expected):
    m = Markers(given)
    assert str(m) == expected


@pytest.mark.parametrize('given, expected', [
    ('os_name == "posix" and os_name == "posix"', 'os_name == "posix"',),
    ('os_name == "posix" or os_name == "posix"', 'os_name == "posix"',),

    ('os_name == "posix" and os_name == "win"', 'os_name == "posix" and os_name == "win"',),
    ('os_name == "posix" or os_name == "win"', 'os_name == "posix" or os_name == "win"',),

    (
        '(os_name == "nt" and sys_platform != "linux") or (os_name == "nt" and sys_platform != "linux")',
        'os_name == "nt" and sys_platform != "linux"',
    ),
    (
        'os_name == "nt" and sys_platform != "linux" and os_name == "nt" and sys_platform != "linux"',
        'os_name == "nt" and sys_platform != "linux"',
    ),
    (
        'os_name == "nt" and sys_platform != "linux" or os_name == "nt" and sys_platform == "linux"',
        'os_name == "nt" and sys_platform != "linux" or os_name == "nt" and sys_platform == "linux"',
    ),
])
def test_simplify_the_same(given, expected):
    m = Markers(given)
    assert str(m) == expected


@pytest.mark.parametrize('left, right, expected', [
    ('os_name == "nt"', 'sys_platform != "linux"', 'os_name == "nt" and sys_platform != "linux"'),
    ('os_name == "nt"', 'os_name == "nt"', 'os_name == "nt"'),
])
def test_and(left, right, expected):
    assert str(Markers(left) & Markers(right)) == str(Markers(expected))
    # inplace
    m = Markers(left)
    m &= Markers(right)
    assert str(m) == str(Markers(expected))


@pytest.mark.parametrize('left, right, expected', [
    ('os_name == "nt"', 'sys_platform != "linux"', 'os_name == "nt" or sys_platform != "linux"'),
    ('os_name == "nt"', 'os_name == "nt"', 'os_name == "nt"'),
])
def test_or(left, right, expected):
    assert str(Markers(left) | Markers(right)) == str(Markers(expected))
    # inplace
    m = Markers(left)
    m |= Markers(right)
    assert str(m) == str(Markers(expected))


@pytest.mark.parametrize('marker, expected', [
    ('os_name == "nt" and sys_platform != "linux"', {'os_name', 'sys_platform'}),
    ('os_name == "nt" and os_name != "nt"', {'os_name'}),
    ('os_name == "nt" and os_name != "unix"', {'os_name'}),
    ('os_name == "nt" and os_name == "unix"', {'os_name'}),
])
def test_variables(marker, expected):
    assert Markers(marker).variables == expected


@pytest.mark.parametrize('marker, ok', [
    ('os_name == "nt" and sys_platform == "linux"', True),
    ('os_name == "nt" and os_name == "posix"', False),
    # ('os_name == "nt" and sys_platform != "linux"', True),
    ('os_name == "nt" and os_name != "nt"', False),
    ('os_name == "nt" and os_name != "unix"', True),

    ('python_version >= "2.7" and python_version >= "3.4"', True),
    ('python_version >= "2.7" and python_version <= "3.4"', True),
    ('python_version <= "2.7" and python_version >= "3.4"', False),
    ('python_version <= "2.7" or python_version >= "3.4"', True),
])
def test_compat(marker, ok):
    assert Markers(marker).compat is ok


@pytest.mark.parametrize('marker, values', [
    ('extra == "lol"', {'lol'}),
    ('os_name == "nt"', set()),
    ('extra == "lol" and extra != "lal"', {'lol'}),
    ('extra == "lol" and extra == "lal"', {'lol', 'lal'}),
    ('extra == "lol" or extra == "lal"', {'lol', 'lal'}),
    ('extra == "lol" and extra == "lal" or extra == "nani"', {'lol', 'lal', 'nani'}),
])
def test_get_strings(marker, values):
    assert Markers(marker).get_strings('extra') == values


@pytest.mark.parametrize('before, after', [
    ('os_name == "nt"', 'os_name == "nt"'),
    ('os_name == "nt" and extra == "lol"', 'os_name == "nt"'),
    ('os_name == "nt" or extra == "lol"', 'os_name == "nt"'),
    ('extra == "lol"', ''),
])
def test_remove(before, after):
    marker = Markers(before)
    marker.remove('extra')
    assert str(marker) == after
