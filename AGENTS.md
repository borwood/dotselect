# dotselect agent workflow

## Product boundary

- `dotselect` is the canonical public package.
- `dotselect._legacy` is the supported compatibility implementation.
- `dotselect._prototype` is the MVP replacement under development; do not expose
  it from `dotselect` until it passes the public contract suite.
- `xmlquery` is a compatibility namespace only. Do not add new behavior there.

## Test-first rule

Run `python -m pytest` before handing off work. For behavior changes, write a
focused failing test locally before implementation; only commit the slice once
the full suite is green. Keep `main` green.

## Source-of-truth behavior

The tests in `tests/` are the executable public contract. The current contract
covers dot traversal, filtering, extraction, branch merging, CSV output, and a
fictional namespaced C-CDA document. Do not weaken a test merely to match a
prototype defect; discuss intentional contract changes in `docs/mvp-plan.md`.

## Worktree scope

Use one worktree and one owner per implementation area. Parallel agents may
review code or add non-overlapping tests, but only the designated implementation
agent edits `src/dotselect/_prototype/` for a slice.

## Fixtures and generated files

`tests/fixtures/synthetic_ccda.xml` is fictional sample data and is approved
for tests. Do not commit generated CSVs, bytecode, virtual environments, or
package metadata.

## Handoffs

Report: public behavior changed, tests added/updated, full test result, and any
unresolved design decision. Keep commits small and semantic.
