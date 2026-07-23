from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

EXPECTED = "RELAY_SMOKE_OK"


def extract_text(value: Any) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node_type = node.get("type")
            if node_type in {"output_text", "response.output_text.done"}:
                text = node.get("text")
                if isinstance(text, str):
                    parts.append(text)
            delta = node.get("delta")
            if node_type == "response.output_text.delta" and isinstance(delta, str):
                parts.append(delta)
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)
    return "".join(parts)


def write_summary(summary: dict[str, Any]) -> None:
    path = Path("smoke/handshake-summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    endpoint = os.environ["AGENT_RESPONSES_ENDPOINT"]
    api_key = os.environ["AGENT_API_KEY"]
    model = os.environ["AGENT_MODEL"]

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Reply with exactly {EXPECTED} and nothing else.",
                    }
                ],
            }
        ],
        "max_output_tokens": 32,
        "stream": True,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "temp-test-safe-responses-handshake/1.0",
        },
        method="POST",
    )

    event_count = 0
    event_types: set[str] = set()
    text_parts: list[str] = []
    completed = False
    response_failed = False

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            http_status = int(response.status)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
            raw_non_sse: list[bytes] = []
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if not line.startswith("data:"):
                    raw_non_sse.append(raw_line)
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                event_count += 1
                event_type = event.get("type")
                if isinstance(event_type, str):
                    event_types.add(event_type)
                if event_type == "response.output_text.delta" and isinstance(event.get("delta"), str):
                    text_parts.append(event["delta"])
                elif event_type == "response.output_text.done" and isinstance(event.get("text"), str):
                    if not text_parts:
                        text_parts.append(event["text"])
                elif event_type == "response.completed":
                    completed = True
                    if not text_parts:
                        text_parts.append(extract_text(event))
                elif event_type == "response.failed":
                    response_failed = True

            if event_count == 0 and raw_non_sse:
                body = b"".join(raw_non_sse)
                try:
                    parsed = json.loads(body.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    parsed = None
                if parsed is not None:
                    text_parts.append(extract_text(parsed))
                    completed = True

        output_text = "".join(text_parts).strip()
        passed = (
            http_status == 200
            and completed
            and not response_failed
            and output_text == EXPECTED
        )
        summary = {
            "status": "PASS" if passed else "FAIL",
            "http_status_class": f"{http_status // 100}xx",
            "content_type_is_event_stream": content_type == "text/event-stream",
            "event_count": event_count,
            "event_types": sorted(event_types),
            "response_completed": completed,
            "response_failed": response_failed,
            "expected_output_matched": output_text == EXPECTED,
            "failure_class": None if passed else "PROTOCOL_OR_OUTPUT_MISMATCH",
        }
        write_summary(summary)
        for key in (
            "content_type_is_event_stream",
            "response_completed",
            "expected_output_matched",
        ):
            print(f"HANDSHAKE_{key.upper()}={'PASS' if summary[key] else 'FAIL'}")
        return 0 if passed else 1

    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        if status in {401, 403}:
            failure_class = "AUTH_FAILED"
        elif status == 404:
            failure_class = "RESPONSES_ENDPOINT_NOT_FOUND"
        elif status == 429:
            failure_class = "RATE_LIMITED"
        elif 500 <= status <= 599:
            failure_class = "UPSTREAM_SERVER_ERROR"
        else:
            failure_class = "HTTP_ERROR"
        write_summary(
            {
                "status": "FAIL",
                "http_status_class": f"{status // 100}xx",
                "failure_class": failure_class,
            }
        )
        print(f"HANDSHAKE_FAILURE_CLASS={failure_class}")
        return 1
    except urllib.error.URLError:
        write_summary({"status": "FAIL", "failure_class": "TRANSPORT_ERROR"})
        print("HANDSHAKE_FAILURE_CLASS=TRANSPORT_ERROR")
        return 1
    except Exception:
        write_summary({"status": "FAIL", "failure_class": "UNCLASSIFIED_SAFE_ERROR"})
        print("HANDSHAKE_FAILURE_CLASS=UNCLASSIFIED_SAFE_ERROR")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
