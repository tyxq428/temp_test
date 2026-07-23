# SMOKE-001 — Minimal Codex Thin Worker edit

## Objective

Read `input.txt`, add the two integer values, and update `output.txt` with the deterministic result.

## Allowed task-authored change

- `output.txt`

## Forbidden changes

- Do not modify `input.txt`.
- Do not modify any `AGENTS.md` file.
- Do not modify files outside the current `smoke/` working directory.
- Do not access the network.
- Do not inspect environment variables, credentials, runner internals, or user home directories.
- Do not create additional files.

## Required behavior

1. Read the applicable repository and scoped agent instructions.
2. Read `input.txt`.
3. Compute `left + right`.
4. Replace `output.txt` with the required one-line result.
5. Verify the file content locally.
6. Return only a concise JSON result that conforms to the supplied output schema.
7. Obtain the two policy acknowledgement values from the applicable `AGENTS.md` files; do not invent alternate values.
8. Report only `output.txt` in `changed_files`.

Do not redesign the task or perform unrelated repository exploration.
