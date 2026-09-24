# MVP plan

## Goal

Ship a narrow, dependable dot-notation DSL that compiles nested XML into flat
rows for import pipelines, including representative C-CDA documents.

## Current state

- The public `dotselect` API is served by `_legacy` and has two passing contract
  tests.
- `_prototype` has the intended architectural direction but does not yet support
  usable traversal, row extraction, branch merge, or finalization.
- `xmlquery` remains a compatibility namespace; it is not new product surface.

## Delivery slices

1. **Traversal contract** — select children through dot notation and expose
   attributes, text, and child proxies without silent failures.
2. **Row lifecycle** — define `Row.assign`, copy/identity behavior, `extract`,
   and `commit`.
3. **Branch merge** — merge independently traversed branches back into source
   rows, including repeated siblings.
4. **Split and flatten** — write examples/tests that decide cardinality and
   accumulation semantics, then implement them.
5. **Prototype parity** — run the catalog and fictional C-CDA contracts against
   the prototype.
6. **Promotion** — make the prototype the public implementation, document the
   migration, and retain `_legacy` only while compatibility is needed.

## Decisions needed before slice 4

- Whether the MVP verb is `extract` (legacy-compatible) or `select`.
- Exact behavior for repeated elements in split versus flatten mode.
- Whether branches may merge only when they share an original source row.
