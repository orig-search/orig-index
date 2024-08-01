"""
Splits (normalized) source code into segments.

A segment is basically an outer function (or the stuff between such functions).
It is just a (generally multiline) string, and might not be valid source code
when considered individually.  For avoidance of doubt, you would generally pass
in the normalized module resulting from `orig_index.norm` operating on it, and
line numbers are thrown away explicitly but statements are kept in the same
order.

An example:

```
class X:
    def func():
        pass
    var1 = 1
var2 = 2
```

is three segments, the `class X: pass`, the `def func(): pass`, and then the two
`var` lines (retaining their relative indention).  If there were imports, they
would be part of the `class X` segment.

If the segments are concatenated in their original order, it should be valid
python again.
"""

import ast
import re
import textwrap

WHITESPACE_RE = re.compile(r"\s+")


class ShortCircuitingVisitor(ast.NodeVisitor):
    """
    This visitor behaves more like libcst.CSTVisitor in that a visit_ method
    can return true or false to specify whether children get visited, and the
    visiting of children is not the responsibility of the visit_ method.
    """

    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        rv = visitor(node)
        if rv:
            self.visit_children(node)

    def visit_children(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def generic_visit(self, node) -> bool:
        return True


class FunctionFinder(ShortCircuitingVisitor):
    def __init__(self):
        self.covered_ranges = {}

    def visit_FunctionDef(self, node):
        first_node = node.decorator_list[0] if node.decorator_list else node
        self.covered_ranges[(first_node.lineno - 1, node.end_lineno)] = node


def remove_whitespace_bookending(lines):
    while lines and WHITESPACE_RE.fullmatch(lines[0]):
        lines.pop(0)
    while lines and WHITESPACE_RE.fullmatch(lines[-1]):
        lines.pop(-1)
    return lines


def segment(mod: ast.Module):
    # Ensure we don't have unexpected positions by roundtripping first to lose
    # all potentially-custom whitespace, comments
    whitespace_removed_source = ast.unparse(mod)
    mod = ast.parse(whitespace_removed_source)

    ff = FunctionFinder()
    ff.visit(mod)
    lines = whitespace_removed_source.splitlines(True)
    prev = 0
    for (i, j), node in sorted(ff.covered_ranges.items()):
        if prev != i:
            between = "".join(remove_whitespace_bookending(lines[prev:i]))
            if between and not WHITESPACE_RE.fullmatch(between):
                yield (prev, i, textwrap.dedent(between))
        yield (i, j, ast.unparse(node))
        prev = j

    if prev != len(lines):
        between = "".join(remove_whitespace_bookending(lines[prev : len(lines)]))
        if between and not WHITESPACE_RE.fullmatch(between):
            yield (prev, len(lines), textwrap.dedent(between))
