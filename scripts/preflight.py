from __future__ import annotations

import json
import os
from pathlib import Path

from endpoint_utils import normalize_responses_endpoint


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    endpoint = os.environ.get("AGENT_RESPONSES_ENDPOINT", "").strip()
    api_key = os.environ.get("AGENT_API_KEY", "").strip()
    model = os.environ.get("AGENT_MODEL", "").strip()

    checks: dict[str, bool] = {
        "endpoint_present": bool(endpoint),
        "api_key_present": bool(api_key),
        "model_present": bool(model),
        "debug_disabled": not truthy(os.environ.get("ACTIONS_STEP_DEBUG"))
        and not truthy(os.environ.get("ACTIONS_RUNNER_DEBUG")),
        "api_key_minimum_shape": len(api_key) >= 8,
    }

    try:
        normalize_responses_endpoint(endpoint)
    except ValueError:
        checks["endpoint_normalizable_to_https_responses"] = False
    else:
        checks["endpoint_normalizable_to_https_responses"] = True

    status = "PASS" if all(checks.values()) else "FAIL"
    summary = {"status": status, "checks": checks}
    output = Path("smoke/preflight-summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name, passed in checks.items():
        print(f"PREFLIGHT_{name.upper()}={'PASS' if passed else 'FAIL'}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
