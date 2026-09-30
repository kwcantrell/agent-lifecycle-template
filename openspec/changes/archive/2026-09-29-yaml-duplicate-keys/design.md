# Design: YAML duplicate keys fail

Revised after the panel (see panel.md).

## Decisions

1. **Collect, don't raise.** `TolerantLoader` gains a `construct_mapping(node, deep=False)`
   override. Before calling `super()`, it walks `node.value`, skips merge pairs
   (`tag:yaml.org,2002:merge`), constructs each key, and records it. A repeat is appended to
   `self.duplicates` as `(text, line)`. `text` is the key as written (`key_node.value` for a scalar,
   so `on`, not `True`). `line` is `key_node.start_mark.line + 1`. For an alias key it's the anchor's
   line: a known limitation. [A-m2, A-m4]
   - Unhashable keys aren't special-cased: `super()` already raises `found unhashable key`, which
     is reported as a parse problem as today. [A-m3]
   - Key construction is cached in `constructed_objects`, so there are no side effects or double
     cost. The per-mapping set is O(n), and files over 1 MiB are already skipped. [F-m2]
2. **Key identity** is Python equality of the constructed key: `yes`/`true`, `1`/`1.0`/`true` and
   `null`/`~` collide, and `1`/`"1"` don't. That's exactly what PyYAML's dict would silently merge.
   [S-m3, F-m1]
3. **Merge keys are exempt**, including several `<<` keys and `<<: [*a, *b]`, because PyYAML
   merges them by design. A quoted `"<<"` is an ordinary key. [A-m1]
4. **Introduced vs inherited.** `yaml_problem` returns the parse problem (or None) and the file's
   duplicates.
   - For a file with duplicates, the base version (`git show <merge-base>:<path>`) is loaded the same
     way, and its duplicate key texts form a multiset.
   - Duplicates beyond the base's count for the same key text are **introduced**, and FAIL at every
     stage. The rest are **inherited**, and WARN at every stage.
   - A file absent on the base (new, or no base) counts every duplicate as introduced.
   - Parse problems keep the existing stage logic.

   [F-M1, F-M2]
5. **Tagged mappings.** `_any_tag` calls `loader.construct_mapping`, so `!Sub` mappings are
   checked, and that's intended. [F-m3]
6. **Docs.** The docs/lifecycle.md yaml row gains "or a change introduces a duplicate key". ADR 0017
   gets a dated amendment in Decision, and the Consequences sentence "Duplicate keys still pass" is
   replaced. The rule (check `yaml`) is the same, so no new ADR. [S-M1, S-m1]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| Duplicates are silently accepted today | `yaml.load("a: 1\na: 2", Loader=TolerantLoader)` | `{'a': 2}` |
| The override sees `<<` pairs before flattening | panel prototype | merge pairs visible in `node.value` |
| `_any_tag` reaches `construct_mapping` | panel: `x: !Sub\n a: 1\n a: 2` | `duplicate key 'a'`, line 3 |
| Merge lists and override orders pass | panel: `d: {<<: [*a,*b], p: 9}` | `{'q': 2, 'p': 9}` |
| Python-equality collisions | panel: `1/1.0`, `null/~`, GHA `on`/`on` | all flagged; `1`/`"1"` not |
| No repo YAML file has duplicates | panel: 15 files under the prototype loader | none |
| PyYAML version | `python3 -c "import yaml;print(yaml.__version__)"` | 6.0.1 |
