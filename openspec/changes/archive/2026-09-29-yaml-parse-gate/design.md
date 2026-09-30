# Design: YAML parse gate

Revised after the panel (see panel.md).

## Decisions

1. **Which files.** Tracked: `git ls-files -z -- '*.yml' '*.yaml'`, where the pathspec `*` crosses
   directories. When not in CI, untracked files are added: `git ls-files -z --others
   --exclude-standard -- '*.yml' '*.yaml'`. Symlinks and anything that isn't a regular file are
   skipped and counted in the message. [A-m1]
2. **Loader.** A `SafeLoader` subclass with `add_multi_constructor("!", f)`, where `f` builds scalar,
   sequence and mapping nodes non-deep. The `!` prefix doesn't match `!!python/...` tags, which
   resolve to `tag:yaml.org,2002:python/*`, so those stay rejected and nothing is constructed or
   executed (verified). Aliases share objects, so a 9^9 alias bomb parses in about 1 ms.
   [A-m3 evidence]
3. **Per-file isolation.** Each file is read as UTF-8 and loaded with `list(yaml.load_all(...))`
   inside `try/except Exception`. The error becomes `path:line: problem` when a `problem_mark`
   exists, and `path: ExcType: message` otherwise: ValueError from `!!int abc`, RecursionError from
   deep nesting, UnicodeDecodeError. Files over 1 MiB are listed as "too large to check" in a WARN,
   never skipped silently. [A-M1, F-M4]
4. **pre-commit shape.** For `.pre-commit-config.yaml` at the repo root, after parsing: the document
   is a mapping, `repos` is a list, each repo is a mapping with `repo` and a `hooks` list, and each
   hook is a mapping with an `id`. A failure is reported like a parse error. [F-M3]
5. **Stage-aware severity.** `changed` = `ctx.changed`, which already includes staged and untracked
   files.
   - `pr` stage: any failing file means FAIL.
   - `commit` and `hook` stages: a failing file in `changed` means FAIL; a failing untouched file
     means WARN, "pre-existing broken YAML: fix in its own change".
   - `--only yaml` behaves like `pr`.

   The WARN is printed under `--quiet`, like size. Why not changed-files-only everywhere: the
   incident file was committed in the initial commit, so it would never have been rechecked.
   [F-M1, S-m4]
6. **No `parse_exclude`.** Dropping it removes an unbounded bypass [F-M2]. It also avoids a
   default that's missing on older bases [S-M1, A-M2] and a Helm glob that misses common layouts
   [A-M3], and it isn't needed in this repo [S-M2]. The known limitation, templated YAML, is in
   ADR 0016.
7. **Grandfathering.** `yaml` isn't in `GRANDFATHER_SKIPS`: a grandfathered change still must not
   break YAML. [F-m1]
8. **Installer.** No change. `render_lifecycle` copies the template's lifecycle keys, and no key is
   added. [S-m3]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| The old file fails to parse | PR #6 evidence | `ScannerError: mapping values are not allowed here`, line 26 col 42 |
| safe_load rejects custom tags by default | `python3 -c "import yaml;yaml.safe_load('a: !Ref b')"` | `ConstructorError` |
| The `!` multi-constructor parses CFN and Ansible tags without enabling `!!python` | panel: `!Ref`, `!Sub`, `!GetAtt a.b`, `!If [..]`, `!vault \|`, `!!python/object/apply:os.system` | plain values; python tag -> `ConstructorError`, nothing executed |
| Constructor-phase errors aren't YAMLError | panel: `!!int abc`, `!!timestamp foo`, 100k-deep nesting | ValueError, AttributeError, RecursionError, no mark |
| Alias bombs are cheap | panel: 9^9 references | ~1 ms, ~10 MB |
| `git ls-files` returns tracked symlinks | panel: `ln -s x.yml link.yml` | `link.yml` listed |
| Every YAML file on main parses today | loop over `git ls-files '*.yml' '*.yaml'` | no failures |
