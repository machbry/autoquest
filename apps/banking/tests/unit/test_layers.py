"""The layers only depend downwards: api → services → databases, all → domains."""

import ast
from pathlib import Path

import pytest

import banking

PACKAGE = Path(banking.__file__).parent

# Package folder → packages its modules must not import.
FORBIDDEN_IMPORTS = {
    "domains": ("banking.api", "banking.services", "banking.databases"),
    "databases": ("banking.api", "banking.services"),
    "services": ("banking.api",),
    "api/routers": ("banking.databases",),
    "api/schemas": ("banking.databases", "banking.services"),
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize(("folder", "forbidden"), FORBIDDEN_IMPORTS.items())
def test_layer_does_not_import_upper_layers(folder, forbidden):
    violations = {
        f"{path.relative_to(PACKAGE)}: {module}"
        for path in (PACKAGE / folder).rglob("*.py")
        for module in imported_modules(path)
        if module.startswith(forbidden)
    }

    assert not violations


def test_only_routers_import_schemas():
    importers = {
        str(path.relative_to(PACKAGE).parent)
        for path in PACKAGE.rglob("*.py")
        if any(m.startswith("banking.api.schemas") for m in imported_modules(path))
    }

    assert importers <= {str(Path("api/routers")), str(Path("api/schemas"))}
