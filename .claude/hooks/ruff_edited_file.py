"""Claude Code PostToolUse hook: format and lint the Python file Claude just edited.

Reads the hook payload on stdin. Exit code 2 sends ruff's findings back to Claude.
"""

import json
import subprocess
import sys


def main() -> int:
    """Run ruff on the edited file; return 2 if lint errors remain."""
    path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py"):
        return 0
    ruff = [sys.executable, "-m", "ruff"]
    subprocess.run([*ruff, "format", "--quiet", path], check=False)  # noqa: S603
    # F401 stays unfixed: an import added before its first use would be deleted.
    check = subprocess.run(  # noqa: S603
        [*ruff, "check", "--fix", "--unfixable", "F401", "--quiet", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode:
        print(check.stdout, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
