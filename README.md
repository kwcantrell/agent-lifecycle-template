# agent-lifecycle-template

A development lifecycle for repos where AI coding agents (Claude Code, Codex and others) do
much of the work. It is spec-driven with [OpenSpec](https://github.com/Fission-AI/OpenSpec),
review depth follows each change's risk tier, and hooks and CI enforce the gates instead of
trusting the agent to run them.

- **For agents:** [AGENTS.md](AGENTS.md), one page.
- **For humans:** [docs/lifecycle.md](docs/lifecycle.md) (how it works),
  [docs/security.md](docs/security.md) (threat model and forge setup), and
  [docs/decisions/](docs/decisions/) (why each rule exists).

## Install into a repo

Requires git, Python 3 with PyYAML, and OpenSpec (`npm install -g @fission-ai/openspec@1.13.2`).

```sh
scripts/init.sh --dry-run /path/to/repo   # see what it would copy
scripts/init.sh /path/to/repo             # asks for test/lint/typecheck/audit/build commands
```

init.sh only creates files. For files your repo already has (AGENTS.md, CLAUDE.md, settings,
OpenSpec config) it writes proposals into `.lifecycle-adoption/` for you to merge; see
[docs/lifecycle.md](docs/lifecycle.md). `python3 scripts/lib/adopt.py undo --target /path/to/repo`
removes exactly what it created. After installing, do the forge setup in
[docs/security.md](docs/security.md).

## Check a change

```sh
scripts/check-change.sh                 # all gates, as CI runs them
scripts/check-change.sh --stage hook    # what the agent's Stop hook runs
```

## Status

The template is new and has not yet run a real tier 1 or tier 2 change end to end. Its rules
come from two repos' experience (autologger-2, infisical) and the sources cited in the ADRs.
