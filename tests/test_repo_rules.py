"""Repo-wide rules of the root CLAUDE.md that a test can check.

Each app checks its own rules in its unit tests (`test_*rules.py`, `test_layers.py`).
"""

import ast
import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
APPS = sorted(path for path in (ROOT / "apps").iterdir() if path.is_dir())
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
DOCKERFILES = sorted(
    [*ROOT.glob("apps/*/Dockerfile"), *ROOT.glob("scripts/*/Dockerfile")]
)

APP_FILES = (
    "Dockerfile",
    "README.md",
    "pyproject.toml",
    ".env.example",
    "docs/architecture.md",
    "docs/architecture.py",
    "docs/architecture.png",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
)
# "No AI in production": no app may depend on an LLM.
LLM_SDKS = re.compile(
    r"anthropic|openai|google-genai|google-generativeai|mistralai|cohere|litellm|langchain.*"
)


def package(app: Path) -> str:
    return app.name.replace("-", "_")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def imported_modules(tree: ast.Module) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def is_pinned(image: str) -> bool:
    """An explicit tag other than `latest`, or a digest."""
    if "@sha256:" in image:
        return True
    name, _, tag = image.rpartition("/")[2].partition(":")
    return bool(name) and tag not in {"", "latest"}


@pytest.mark.parametrize("app", APPS, ids=lambda app: app.name)
def test_app_has_the_standard_layout(app):
    expected = [f"src/{package(app)}", *APP_FILES]

    assert [path for path in expected if not (app / path).exists()] == []


@pytest.mark.parametrize("app", APPS, ids=lambda app: app.name)
def test_app_never_imports_another_app(app):
    others = tuple(package(other) for other in APPS if other != app)
    imports = [
        f"{relative(path)}: {module}"
        for path in app.rglob("*.py")
        for module in imported_modules(ast.parse(path.read_text(encoding="utf-8")))
        if module.split(".")[0] in others
    ]

    assert imports == []


@pytest.mark.parametrize("app", APPS, ids=lambda app: app.name)
def test_only_config_reads_the_environment(app):
    # Config is validated at startup in one place, not read ad hoc.
    readers = [
        f"{relative(path)}:{node.lineno}"
        for path in (app / "src").rglob("*.py")
        if path.name != "config.py"
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr in {"environ", "getenv"}
        )
        or (
            isinstance(node, ast.ImportFrom)
            and node.module == "os"
            and {alias.name for alias in node.names} & {"environ", "getenv"}
        )
    ]

    assert readers == []


@pytest.mark.parametrize("app", APPS, ids=lambda app: app.name)
def test_app_does_not_depend_on_an_llm(app):
    project = tomllib.loads((app / "pyproject.toml").read_text(encoding="utf-8"))
    names = [
        re.split(r"[\s<>=!~\[;]", dep)[0].lower()
        for dep in project["project"]["dependencies"]
    ]

    assert [name for name in names if LLM_SDKS.fullmatch(name)] == []


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_workflow_pins_actions_and_declares_permissions(workflow):
    content = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    uses = [
        step_or_job["uses"]
        for job in content["jobs"].values()
        for step_or_job in [job, *job.get("steps", [])]
        if "uses" in step_or_job
    ]

    assert "permissions" in content, "least privilege: set the token's permissions"
    assert [
        action
        for action in uses
        if not action.startswith("./")
        and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", action)
    ] == [], "pin actions by commit SHA"


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=relative)
def test_dockerfile_pins_its_base_images(dockerfile):
    stages, unpinned = set(), []
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        match = re.match(r"FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
        if not match:
            continue
        image, stage = match.groups()
        if image not in stages and not is_pinned(image):
            unpinned.append(image)
        stages.add(stage)

    assert unpinned == []


def test_compose_pins_pulled_images():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    pulled = [
        service["image"]
        for service in compose["services"].values()
        if "image" in service and "build" not in service
    ]
    # Services sharing a built image name it without building it again.
    built = {
        s["image"]
        for s in compose["services"].values()
        if "build" in s and "image" in s
    }

    assert [
        image for image in pulled if image not in built and not is_pinned(image)
    ] == []


def test_env_files_are_gitignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in ignored
