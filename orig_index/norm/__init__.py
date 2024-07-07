import ast
from typing import Optional


class RemoveDocstringsAndTypes(ast.NodeTransformer):
    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.Assign:
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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        modified = self.generic_visit(node)
        if not modified.body:
            modified.body.append(ast.Pass())
        return modified

    visit_ClassDef = visit_FunctionDef
    visit_If = visit_FunctionDef
    visit_ExceptHandler = visit_FunctionDef
    visit_Try = visit_FunctionDef
    # N.b. Try has finalbody, but it can safely be empty


def normalize(mod: ast.Module) -> ast.Module:
    return RemoveDocstringsAndTypes().visit(mod)
