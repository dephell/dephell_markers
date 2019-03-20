# Dephell Markers

Work with environment markers (PEP-496).

## Installation

Install from [PyPI](https://pypi.org/project/dephell-markers/):

```bash
python3 -m pip install --user dephell_markers
```

## Usage

```python
from dephell_markers import Markers

m = Markers('os_name == "posix" and python_version >= "2.7"')

m.get_version(name='python_version')
# '>=2.7'

m.get_string(name='os_name')
# 'posix'

Markers('python_version >= "2.4" or python_version <= "2.7"').get_version(name='python_version')
'<=2.7 || >=2.4'

Markers('python_version >= "2.4" or python_version <= "2.7"').python_version
# RangeSpecifier(<=2.7 || >=2.4)


# Nothing better than lie:
Markers('python_version == "2.4" or os_name == "linux"').get_version(name='python_version')
# None

```
