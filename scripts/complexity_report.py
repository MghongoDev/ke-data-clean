"""Per-function cyclomatic complexity for src/ke_data_clean, McCabe-style.

The enforced gate is ruff's C901 at complexity 10 (pyproject.toml). This
report measures every function so drift is visible before it trips the
gate; the counts follow the usual McCabe rules (one point per branch,
loop, except handler, boolean operand, ternary, comprehension clause and
match case, plus one for the function itself). Nested functions are
reported separately.

Run from the repository root::

    python scripts/complexity_report.py

Exits non-zero when any function exceeds the gate, so it can run in CI
next to ``ruff check``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SOURCE_DIR = Path("src/ke_data_clean")
GATE = 10

_BRANCH_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Assert)
_CALLABLE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _points(node: ast.AST) -> int:
    """Decision points contributed by this single node."""
    if isinstance(node, _BRANCH_NODES):
        return 1
    if isinstance(node, ast.BoolOp):
        return len(node.values) - 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    if isinstance(node, ast.match_case):
        return 1
    return 0


def _count_body(node: ast.AST) -> int:
    """Decision points in a function body, excluding nested functions."""
    total = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _CALLABLE_NODES):
            continue
        total += _points(child) + _count_body(child)
    return total


def main() -> int:
    functions = _functions_all()
    if not functions:
        print("no functions found under", SOURCE_DIR)
        return 1
    over_gate = [entry for entry in functions if entry[2] > GATE]
    print("| Complexity | Function | Gate |")
    print("|-----------:|----------|:----:|")
    for module, name, complexity in sorted(functions, key=lambda entry: (-entry[2], entry[1])):
        mark = "over" if complexity > GATE else "ok"
        print(f"| {complexity} | `{module}.{name}` | {mark} |")
    print(f"\n{len(functions)} functions, {len(over_gate)} over the gate of {GATE}.")
    return 1 if over_gate else 0


def _functions_all() -> list[tuple[str, str, int]]:
    functions: list[tuple[str, str, int]] = []
    for path in sorted(SOURCE_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        functions.extend(_functions(tree, path.stem))
    return functions


def _functions(tree: ast.AST, module: str) -> list[tuple[str, str, int]]:
    """(module, qualified name, complexity) for every function, parents first."""
    found: list[tuple[str, str, int]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, _CALLABLE_NODES):
                visit(child, prefix)
                continue
            name = f"{prefix}{child.name}"
            found.append((module, name, 1 + _count_body(child)))
            visit(child, f"{name}.")

    visit(tree, "")
    return found


if __name__ == "__main__":
    sys.exit(main())
