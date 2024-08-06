import ast

from orig_index.split import segment


def test_basic_split():
    actual = list(segment(ast.parse("""def f():\n    pass\n\ndef g():\n    pass""")))
    assert actual[0] == (0, 2, "def f():\n    pass")
    assert actual[1] == (3, 5, "def g():\n    pass")


def test_split_between():
    actual = list(
        segment(ast.parse("""def f():\n    pass\n\nimport foo\n\ndef g():\n    pass"""))
    )
    # TODO inconsistency about trailing newline would require reindex to fix
    assert actual[0] == (0, 2, "def f():\n    pass")
    assert actual[1] == (2, 4, "import foo\n")
    assert actual[2] == (4, 6, "def g():\n    pass")


def test_split_after():
    actual = list(segment(ast.parse("""def f():\n    pass\n\nimport foo""")))
    assert actual[0] == (0, 2, "def f():\n    pass")
    assert actual[1] == (2, 3, "import foo")
