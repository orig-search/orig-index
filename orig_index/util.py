from typing import Set

from pypi_simple import DistributionPackage


def rank(dp: DistributionPackage) -> int:
    if dp.package_type == "sdist":
        return 10
    elif "-py3-none-any" in dp.filename:
        return 5
    elif "-py2.py3-none-any" in dp.filename:
        return 4
    elif "abi3" in dp.filename:
        return 2
    elif "cp312" in dp.filename:
        return 1
    elif dp.package_type != "wheel":
        return -1
    return 0


def _unpack_range(s: str) -> Set[int]:
    rv: Set[int] = set()
    for x in s.split(","):
        if "-" in x:
            a, b = map(int, x.split("-", 1))
            rv.update(range(a, b + 1))
        else:
            rv.add(int(x))
    return rv
