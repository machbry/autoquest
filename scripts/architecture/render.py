"""Render every app's `docs/architecture.py` to `docs/architecture.png`.

Usage: `docker compose run --rm --build architecture [app ...]` (default: all apps).
"""

import os
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
APPS_DIR = SCRIPTS_DIR.parents[1] / "apps"


def render(app: str) -> Path:
    """Run an app's architecture script from its docs folder; return the PNG path."""
    docs = APPS_DIR / app / "docs"
    source = docs / "architecture.py"
    if not source.is_file():
        raise FileNotFoundError(f"{source} not found")
    cwd = Path.cwd()
    os.chdir(docs)
    try:
        runpy.run_path(str(source), run_name="__main__")
    finally:
        os.chdir(cwd)
    return docs / "architecture.png"


def main(argv: list[str]) -> int:
    """Render the given apps, or all of them; warn about apps without a diagram."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    apps = argv or sorted(p.name for p in APPS_DIR.iterdir() if p.is_dir())
    missing = 0
    for app in apps:
        try:
            print(f"rendered {render(app).relative_to(APPS_DIR.parent)}")
        except FileNotFoundError as exc:
            print(f"warning: {exc}", file=sys.stderr)
            missing += 1
    return 1 if argv and missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
