from unittest.mock import Mock

from orig_index.util import _unpack_range, rank


def test_rank():
    expected = [
        (Mock(package_type="sdist", filename="foo.tar.gz"), 10),
        (Mock(package_type="wheel", filename="foo-py3-none-any.whl"), 5),
        (Mock(package_type="wheel", filename="foo-py2.py3-none-any.whl"), 4),
        (Mock(package_type="wheel", filename="foo-abi3-cp310-x86_64-any.whl"), 2),
        (Mock(package_type="wheel", filename="foo-cp312-x86_64-any.whl"), 1),
        (Mock(package_type="wheel", filename="foo-cp310-x86_64-any.whl"), 0),
        (Mock(package_type="dumb", filename="foo-x86_64.tar"), -1),
    ]

    for pkg, e in expected:
        assert rank(pkg) == e


def test_unpack_range():
    assert _unpack_range("3,5-9") == {3, 5, 6, 7, 8, 9}
