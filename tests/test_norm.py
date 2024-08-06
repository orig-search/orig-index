import ast

import pytest

from orig_index.norm import normalize


def test_noop():
    assert "x = 1" == ast.unparse(normalize(ast.parse("x=1")))


def test_annassign():
    assert "x = 1" == ast.unparse(normalize(ast.parse("x:int=1")))


def test_annassign_no_value():
    # not ideal, but there's no "local" statement that would do the
    # equivalent without a type or initial value
    assert "x: int" == ast.unparse(normalize(ast.parse("x:int")))


def test_funcdef():
    assert "def f(x):\n    pass" == ast.unparse(normalize(ast.parse("def f(x): pass")))


def test_funcdef_type():
    assert "def f(x):\n    pass" == ast.unparse(
        normalize(ast.parse("def f(x: int): pass"))
    )


@pytest.mark.xfail
def test_funcdef_ret_type():
    assert "def f(x):\n    pass" == ast.unparse(
        normalize(ast.parse("def f(x) -> None: pass"))
    )


def test_string_expr():
    # this does not change
    assert "x = 'f'" == ast.unparse(normalize(ast.parse("x = 'f'")))


def test_int_stmt():
    # this does not change
    assert "1" == ast.unparse(normalize(ast.parse("1")))


def test_string_stmt():
    assert "x" == ast.unparse(normalize(ast.parse("'f'\n'g'\nx\n'z'")))


def test_only_string_stmt():
    assert "def x():\n    pass" == ast.unparse(normalize(ast.parse("def x(): ''")))


# def test_norm_docstrings():
#    mod = ast.parse("''")
#    assert ast.unparse(normalize(mod)) == ""
#
#    mod = ast.parse("x=''")
#    assert ast.unparse(normalize(mod)) == "x = ''"
#
#    mod = ast.parse("2")
#    assert ast.unparse(normalize(mod)) == "2"
#
#
# def test_norm_assign():
#    mod = ast.parse("x: int = 2")
#    assert ast.unparse(normalize(mod)) == "x = 2"
#
#    # this is left alone because I don't konw if it defines the scope...
#    mod = ast.parse("x: int")
#    assert ast.unparse(normalize(mod)) == "x: int"
#
#
# def test_norm_func():
#    mod = ast.parse(
#        """
# def f(x: None) -> None:
#    'doc'
#    # comment
#    return (x)
# """
#    )
#    # TODO this encodes a bug that inadvertently exists, but will require
#    # reindexing the world once fixed...
#    assert (
#        ast.unparse(normalize(mod))
#        == """\
# def f(x) -> None:
#    return x"""
#    )
#
#
# def test_norm_tryexcept():
#    mod = ast.parse(
#        """
# try:
#    ""
# except:
#    ""
# finally:
#    ""
# """
#    )
#    assert (
#        ast.unparse(normalize(mod))
#        == """\
# try:
#    pass
# except:
#    pass"""
#    )
#
#
# def test_split_basic(
