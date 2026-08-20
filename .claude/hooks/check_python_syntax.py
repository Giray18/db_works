"""PostToolUse hook (Edit|Write matcher): verifies the .py file Claude just touched still
compiles. Silent on success; on a syntax error, surfaces it to the user AND feeds it back to
Claude as additionalContext so it can fix the file in the same turn instead of the mistake
surviving to the next `python` run or pipeline deploy.
"""
import json
import sys

payload = json.load(sys.stdin)
file_path = payload.get("tool_input", {}).get("file_path", "")

if not file_path.endswith(".py"):
    sys.exit(0)

with open(file_path, "rb") as f:
    source = f.read()

try:
    compile(source, file_path, "exec")
except SyntaxError as e:
    print(json.dumps({
        "systemMessage": f"Python syntax error in {file_path}",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"Syntax error in {file_path} line {e.lineno}: {e.msg}",
        },
    }))
