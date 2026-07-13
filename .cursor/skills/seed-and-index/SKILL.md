---
name: seed-and-index
description: Generate seed.py and prefix-aware mongodb_indexes.json after data-model approval.
---

# Seed and index generation

Run only after `data-model.md` status is **approved**.

## seed.py

- Database: `sizing_{useCaseSlug}`
- **500** documents per top-level collection
- `RANDOM_SEED` constant for reproducibility
- Embedded arrays: average size from `outputs/sizing_inputs.json` → `embedded.*.avgCardinality`
- CLI: `--clear`, `--uri`

## mongodb_indexes.json

1. Map relational composites to **one** compound index (correct field order / ESR when applicable).
2. **Do not** emit prefix indexes subsumed by a longer compound on the same collection (unless unique/sparse/partial differ).
3. Optional `prefix_coverage` array for documentation.
4. `scripts/apply_indexes.py` creates indexes as-is (no runtime dedup).

## Example (release table)

Relational indexes on `(cKey)`, `(cKey, cKey_Type)`, `(cKey, cKey_Type, cCopy_Number)` → emit only the 3-field compound with `unique: true`.
