# Stop hook surfaces warnings

Tier: 2
Tier reason: touches .claude/hooks/ and scripts/lib/check_change.py (high-risk paths); changes agent-facing guardrail behaviour.

Approved-by: Kalen 2026-09-29

## Why

The Stop hook runs `check-change.sh --stage hook --quiet` and only speaks on failure. Warnings that
exist for the agent never reach it when it's wrapping up:
- the size budget exceeded before commit (ADR 0007, amended);
- pre-existing broken YAML, and duplicate keys already on the base (ADR 0017);
- duplicate ADR numbers (ADR 0018);
- a grandfathered change (ADR 0014).

## What Changes

- **Warnings reach the human every time.** Every stop where the checks pass with warnings emits
  `systemMessage` listing them. Claude Code shows it to the user without blocking.
- **Actionable warnings reach the agent once.** Only the size warning is one the agent can act on
  in this change (split it, or ask for `size-override`). It blocks the stop once per session with
  `{"decision": "block", "reason": ...}`, keyed on the check name, so a changing line count can't
  re-arm it. Pre-existing warnings (broken YAML, inherited duplicate keys, duplicate ADR numbers)
  and grandfathered-change warnings go to the human only, and never cost the agent a turn.
- **Repo text is treated as untrusted.** Warning text includes file names and YAML keys. It's
  limited to a safe character set, capped at 200 characters per line and 1 KB in total, and
  placed after the instruction, inside an "untrusted check output" delimiter.
- **Robust to a failed write.** WARN extraction tolerates no matches under `set -e`, and a marker
  that can't be written falls back to `systemMessage` only.
- **Failures are unchanged:** exit 2, and give up after 3 attempts.
- **Quiet output includes the warnings that matter.** `check-change.sh --quiet` also prints the
  grandfathered `change` and `risk-floor` warnings.
- **Installing is a reviewed human step.** The agent writes the hook to the change folder, and the
  change's tasks and PR record its sha256. The human checks that sha256, reads the diff, and copies
  it to `.claude/hooks/stop-check.sh`, which agents can't edit. Code owners review `.claude/hooks/`.

## Non-goals

- Changing which checks run, or their severities.
- Upgrading existing installs. The installer never overwrites a target's hook (ADR 0015); targets
  keep the old hook until the planned update change.
- Surfacing informational warnings (commands not configured, tests-with-code inactive).

## Impact

- `.claude/hooks/stop-check.sh` (replaced by the human; about 45 lines), `scripts/lib/check_change.py`
  (1 line), `tests/test_check_change.py`, `docs/lifecycle.md`, `docs/decisions/0004-evidence-and-stop-hook.md`.
