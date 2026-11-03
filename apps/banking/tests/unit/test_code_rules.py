"""The banking source follows the money and logging rules of its CLAUDE.md."""

import ast
from collections.abc import Iterator
from pathlib import Path

import banking

PACKAGE = Path(banking.__file__).parent

# Log ids, counts and line numbers only: never these.
PRIVATE_FIELDS = {"description", "amount", "balance", "account_number"}


def syntax_trees() -> Iterator[tuple[str, ast.Module]]:
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        yield path.relative_to(PACKAGE).as_posix(), tree


def is_log_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"logger", "logging"}
    )


def referenced_names(node: ast.AST) -> set[str]:
    return {
        child.id if isinstance(child, ast.Name) else child.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Name | ast.Attribute)
    }


def test_money_is_decimal_never_float():
    uses = [
        f"{path}:{node.lineno}"
        for path, tree in syntax_trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "float"
    ]

    assert uses == []


def test_logs_never_pass_private_fields():
    leaks = [
        f"{path}:{call.lineno} {name}"
        for path, tree in syntax_trees()
        for call in ast.walk(tree)
        if is_log_call(call)
        for arg in [*call.args, *call.keywords]
        for name in referenced_names(arg) & PRIVATE_FIELDS
    ]

    assert leaks == []
