"""PostToolUse hook: after Edit/Write to app/<module>.py, run tests/test_<module>.py
if it exists, reinforcing this project's TDD workflow (test file per app module).
Reads the standard Claude Code hook JSON from stdin.
"""
import json
import os
import subprocess
import sys


def main() -> int:
    data = json.load(sys.stdin)
    f = data.get("tool_response", {}).get("filePath") or data.get("tool_input", {}).get("file_path") or ""
    f = f.replace("\\", "/")
    if "app" not in f.split("/") or not f.endswith(".py"):
        return 0

    module = os.path.basename(f)[:-3]
    test_file = f"tests/test_{module}.py"
    if not os.path.isfile(test_file):
        return 0

    for candidate in (os.path.join(".venv", "Scripts", "pytest.exe"), os.path.join(".venv", "bin", "pytest")):
        if os.path.isfile(candidate):
            pytest_exe = os.path.abspath(candidate)
            break
    else:
        pytest_exe = "pytest"

    result = subprocess.run([pytest_exe, test_file, "-q"], capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
