from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_OUTPUT = "result=42\n"
EXPECTED_ROOT_ACK = "ROOT_POLICY_V1"
EXPECTED_SCOPED_ACK = "SMOKE_POLICY_V1"
ALLOWED_WORKTREE_PATHS = {"smoke/output.txt", "smoke/codex-result.json"}


def git_paths(*args: str) -> set[str]:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def main() -> int:
    output_path = Path("smoke/output.txt")
    result_path = Path("smoke/codex-result.json")

    checks: dict[str, bool] = {
        "output_exists": output_path.is_file(),
        "result_exists": result_path.is_file(),
    }

    result: dict[str, Any] = {}
    if checks["result_exists"]:
        try:
            parsed = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                result = parsed
                checks["result_json_object"] = True
            else:
                checks["result_json_object"] = False
        except (OSError, json.JSONDecodeError):
            checks["result_json_object"] = False
    else:
        checks["result_json_object"] = False

    checks["output_exact"] = (
        output_path.read_text(encoding="utf-8") == EXPECTED_OUTPUT
        if checks["output_exists"]
        else False
    )
    checks["status_pass"] = result.get("status") == "PASS"
    checks["root_agents_loaded"] = result.get("root_policy_ack") == EXPECTED_ROOT_ACK
    checks["scoped_agents_loaded"] = result.get("scoped_policy_ack") == EXPECTED_SCOPED_ACK

    reported = result.get("changed_files")
    checks["reported_changed_files_exact"] = isinstance(reported, list) and set(reported) in (
        {"output.txt"},
        {"smoke/output.txt"},
    )
    checks["no_blocking_reason"] = result.get("blocking_reason") is None

    modified = git_paths("diff", "--name-only")
    untracked = git_paths("ls-files", "--others", "--exclude-standard")
    actual_paths = modified | untracked
    checks["scope_guard"] = actual_paths <= ALLOWED_WORKTREE_PATHS
    checks["output_was_modified"] = "smoke/output.txt" in actual_paths

    status = "PASS" if all(checks.values()) else "FAIL"
    summary = {
        "status": status,
        "checks": checks,
        "actual_changed_paths": sorted(actual_paths),
    }
    summary_path = Path("smoke/verification-summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name, passed in checks.items():
        print(f"VERIFY_{name.upper()}={'PASS' if passed else 'FAIL'}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
