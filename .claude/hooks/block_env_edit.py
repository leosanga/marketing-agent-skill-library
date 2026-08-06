"""PreToolUse hook: block Edit/Write to a literal .env file (not .env.example
or similar) to prevent accidentally leaking GROQ_API_KEY / ALLOWED_ORIGIN.
Reads the standard Claude Code hook JSON from stdin.
"""
import json
import os
import sys


def main() -> int:
    data = json.load(sys.stdin)
    f = data.get("tool_input", {}).get("file_path") or ""
    name = os.path.basename(f.replace("\\", "/"))
    if name == ".env":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "Direct edits to .env are blocked to avoid leaking "
                    "GROQ_API_KEY / ALLOWED_ORIGIN. Edit .env.example instead, "
                    "or set the real value in your shell / Render dashboard."
                ),
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
