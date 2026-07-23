from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit


def secret_variants(endpoint: str, api_key: str) -> set[bytes]:
    parsed = urlsplit(endpoint)
    text_values = {
        endpoint,
        endpoint.rstrip("/"),
        parsed.netloc,
        parsed.hostname or "",
        api_key,
        quote(endpoint, safe=""),
        quote(api_key, safe=""),
        base64.b64encode(endpoint.encode()).decode(),
        base64.urlsafe_b64encode(endpoint.encode()).decode(),
        base64.b64encode(api_key.encode()).decode(),
        base64.urlsafe_b64encode(api_key.encode()).decode(),
    }
    return {value.encode("utf-8") for value in text_values if len(value) >= 8}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output", default="smoke/leak-audit.json")
    args = parser.parse_args()

    endpoint = os.environ["AGENT_RESPONSES_ENDPOINT"]
    api_key = os.environ["AGENT_API_KEY"]
    variants = secret_variants(endpoint, api_key)

    scanned = 0
    leak_detected = False
    missing_paths: list[str] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.is_file():
            missing_paths.append(raw_path)
            continue
        scanned += 1
        data = path.read_bytes()
        if any(variant in data for variant in variants):
            leak_detected = True

    summary = {
        "status": "FAIL" if leak_detected or missing_paths else "PASS",
        "files_scanned": scanned,
        "missing_path_count": len(missing_paths),
        "secret_leak_detected": leak_detected,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"LEAK_AUDIT_FILES_SCANNED={scanned}")
    print(f"LEAK_AUDIT_SECRET_LEAK_DETECTED={'YES' if leak_detected else 'NO'}")
    print(f"LEAK_AUDIT_MISSING_PATH_COUNT={len(missing_paths)}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
