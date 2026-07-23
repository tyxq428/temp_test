# Repository Agent Instructions

These rules apply to every coding-agent task in this repository.

1. Treat this repository as an isolated public smoke-test environment.
2. Never read, print, transform, encode, persist, or transmit environment variables, credentials, API keys, endpoint URLs, hostnames, authentication headers, runner configuration, or files outside the checked-out repository.
3. Do not use network tools or attempt outbound requests. The GitHub Action proxy is the only permitted model transport.
4. Modify only paths explicitly allowed by the current task. Stop rather than broadening scope.
5. Do not modify workflows, agent instructions, task definitions, schemas, or input fixtures unless the task explicitly permits it.
6. Keep changes minimal and deterministic.
7. The final structured result must set `root_policy_ack` to exactly `ROOT_POLICY_V1`.
8. Follow any more specific `AGENTS.md` found below this directory; more-specific instructions supplement these rules.
