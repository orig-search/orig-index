"""
Normalize source code to remove common sources of churn like whitespace changes.

This doesn't call ast.unparse, thus does not validate that the resulting source
code is anything close to valid.  Tests, as well as orig_index.split use, do.

Past bugs here have basically been removing the only statement where at least
one statement was required (e.g. docstring -> pass).
"""

import ast
from typing import Optional


class RemoveDocstringsAndTypes(ast.NodeTransformer):

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.Assign | ast.AnnAssign:
        if not node.value:
            return node
        return ast.copy_location(
            ast.Assign(targets=[node.target], value=node.value),
            node,
        )

    def visit_arg(self, node: ast.arg) -> ast.arg:
        return ast.copy_location(
            ast.arg(arg=node.arg),
            node,
        )

    def visit_Expr(self, node: ast.Expr) -> Optional[ast.Expr]:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        return node

    def visit_something_with_body(self, node: ast.AST) -> ast.AST:
        # This is not used directly (the name is not magic), but is assigned to
        # other visit_ methods below.
        modified = self.generic_visit(node)
        assert hasattr(modified, "body")
        if not modified.body:
            modified.body.append(ast.Pass())
        # if hasattr(modified, "returns"):
        #     modified.returns = None
        return modified

    visit_FunctionDef = visit_something_with_body
    visit_ClassDef = visit_something_with_body
    visit_If = visit_something_with_body
    visit_ExceptHandler = visit_something_with_body
    visit_Try = visit_something_with_body
    # N.b. Try has finalbody, but it can safely be empty


def normalize(mod: ast.Module) -> ast.Module:
    return RemoveDocstringsAndTypes().visit(mod)
