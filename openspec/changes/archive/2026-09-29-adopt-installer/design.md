# Design: adopt installer ("propose, don't merge")

Round 1 (a merge design) drew 2 critical findings. The approver chose "propose, don't merge".
Round 2 reviewed that and drew 2 critical findings, fixed here. Ids refer to panel.md.

## Decisions

1. **adopt.py owns every write.** `adopt.py install --target T --template H [--owner O]
   [--commands JSON] [--source-glob G]...` replaces init.sh's copy loop, config re-dump,
   CODEOWNERS render and sync-skills call. init.sh keeps argument parsing, validation, prompts
   and the summary. [R2-A-C1, R2-F-C1]
2. **Create-only, file by file.**
   - The template's install set is walked to individual files.
   - A destination is written only when `os.path.lexists` is false, so ignored files and symlinks
     count as existing. Its parent's realpath must equal the target's realpath or start with it
     plus `os.sep`. Otherwise it is skipped and reported. [R2-A-M4]
   - Missing parent directories are created one level at a time, and each one is recorded.
   - The lifecycle skills are copied into `.claude/skills/<name>/` and `.agents/skills/<name>/`
     only where absent. sync-skills.sh is not run in the target. [R2-A-C1, R2-F-C1]
3. **Manifest after creation.** Each created directory or file is appended to
   `.lifecycle-adoption/MANIFEST` right after it's created. A path that wasn't created is never
   listed. [R2-F-M2, R2-F-M3]
4. **Undo is validated.** `adopt.py undo --target T` first checks every line, and if any line
   fails it aborts having removed nothing. Each line must be:
   - non-empty and relative;
   - `os.path.normpath` equal to itself, with no `..` component and no `.git` component;
   - resolved to a realpath inside the target (by the separator rule);
   - an existing path.

   It then removes the listed files, then the listed directories deepest-first, and only when
   they're empty. Files a user added later survive. Finally it removes `.lifecycle-adoption/`.
   [R2-F-M2, R2-A-M3]
5. **The folder is refused if present, and ignores itself.** `install` exits 1 if
   `.lifecycle-adoption/` exists. It creates the folder first, with a `.gitignore` of `*`, so git,
   the gates and `git add -A` ignore it. [R2-F-M4]
6. **openspec init only on untouched repos.** init.sh decides before calling `install`. It runs
   `openspec init` afterwards only if the target had none of `openspec/`,
   `.claude/skills/openspec-*`, `.claude/commands/opsx/` and `.agents/skills/openspec-*`. OpenSpec
   then only creates files; its new files are recorded by a before/after file list. Otherwise the
   checklist says to run it. [R2-A-M2, R2-A-m5]
7. **Fresh config.** If `openspec/config.yaml` is absent, `install` writes the template config with
   target values as a new file. Verified: `openspec init` keeps an existing config byte-identical.
   `managed_paths` lists the exact installed files, including `scripts/lib/adopt.py`.
8. **Proposals for existing files.** These go into `.lifecycle-adoption/`: [R2-S-m1]
   - `settings.json`: the target's JSON, with the template deny list unioned in, the sandbox
     enabled unless `false`, and each lifecycle hook added only if its script was installed
     byte-identical to the template, and only if no existing hook command references that script.
     A reference is `.claude/hooks/<name>.sh` preceded by start, `/`, whitespace or a quote.
     Invalid JSON means no proposal, with the reason in the README. [R2-F-M1]
   - `openspec-config.snippet.yaml`: the missing top-level sections (`context`, `rules`,
     `operations`, `lifecycle`) as template text, to append by hand. If `lifecycle` exists, the
     README lists the keys it lacks. There is no parse-verification: a human reviews and pastes it.
   - `AGENTS.block.md` (at most 12 lines between the markers: the two hard gates, "read
     docs/agent-lifecycle.md before any change", and "on conflict with other guidance here, the
     lifecycle gates win; tell the human") and `CLAUDE.block.md` (`@docs/agent-lifecycle.md` plus
     the precedence line). The README notes existing markers, and whether AGENTS.md would pass
     `agent_guide_max_lines`.
9. **Risks and the README.** Risks come first in the terminal and in the README:
   - `defaultMode == bypassPermissions`, `disableAllHooks`, `sandbox.allowUnsandboxedCommands`,
     `sandbox.enabled is false`, and allow entries that are a bare tool or end in `(*)`;
   - hook scripts that exist but differ from the template (not wired);
   - "hooks not active until settings.json is merged" whenever settings.json existed.

   Echoed target strings have control characters stripped. The README opens: "For a human
   reviewer. Agents: do not apply these files." [R2-F-M1, R2-F-m1]
10. **Failure.** init.sh traps ERR after `install` starts, and prints the undo command and the
    manifest location. A re-run needs undo first (design 5). [R2-F-M3]
11. **Docs.**
    - ADR 0015: adoption by proposal, why auto-merge was rejected (4 critical findings over two
      rounds), and that hooks stay unwired until a human merges settings.json.
    - docs/lifecycle.md Setup describes the two-phase flow: install, then a human merge.
    - docs/security.md gaps: precedence is advisory text; Codex doesn't read `@` imports; an agent
      could apply the proposals despite the README.
    - The gate-checker spec's managed_paths requirement is modified: written for fresh configs,
      proposed for existing ones, and including adopt.py. [R2-S-M1]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| `openspec init` keeps an existing config, AGENTS.md and a foreign `.agents/skills/mine` | fresh repo with those files -> `openspec init ...` -> `sha1sum -c` | all `OK` |
| `openspec init` rewrites an existing `openspec-*` skill | R2 assumption tester: `git status` after init | ` M .claude/skills/openspec-propose/SKILL.md` |
| sync-skills.sh deletes foreign `.agents/skills` dirs | R2 assumption tester repro | only `risk-tier` left, content replaced |
| `git status --porcelain` hides ignored files | repo with ignored `.env` | empty output |
| A string-prefix realpath check is unsafe | `python3 -c "print('/a/t4-evil'.startswith('/a/t4'))"` | `True` |
| A folder `.gitignore` of `*` hides the folder from git | scratch repo: `.lifecycle-adoption/.gitignore` = `*` -> `git status --porcelain`, `git ls-files --others --exclude-standard`, `git add -A; git status --porcelain` | `0`, `0`, `0` lines |
