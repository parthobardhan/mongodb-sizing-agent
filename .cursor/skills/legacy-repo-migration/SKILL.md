---
name: legacy-repo-migration
description: Translate legacy JDBC DAO methods into PyMongo repository and pytest after data-model approval.
---

# Legacy repository migration

Run only after `data-model.md` status is **approved** and `inputs/legacy/*` exists.

## Inputs

- `inputs/legacy/*.java` (or other legacy DAO) — method names and embedded SQL are the source of truth for parity.
- `outputs/data-model.md` — approved collection names, embedded arrays, index strategy.
- `outputs/mongodb_indexes.json` — compound indexes for query paths.

## mongo_repository.py

1. **Method parity**: one Python method per legacy DAO method; use snake_case names derived from legacy camelCase (e.g. `findByKey` → `find_by_key`).
2. **SQL in docstrings**: each method docstring cites the original SQL from the legacy artifact.
3. **Join → embed**: `JOIN` to detail/history becomes a single `find_one` on the anchor collection; return embedded `detailLines` as part of the document or as a projected list.
4. **Composite keys**: multi-column `WHERE` on release rows becomes `find_one` with a filter matching all key fields; rely on compound index from `mongodb_indexes.json`.
5. **Aggregates**: `COUNT(*)` / `GROUP BY` become `count_documents` or a minimal aggregation pipeline only when needed.
6. **Connection**: accept `MongoClient` or database handle in constructor; database name `sizing_{slugified_use_case}` from intake `useCaseName`.
7. **Collections**: use names from approved `data-model.md` (e.g. `client_document_history`, `client_release_table`).

## test_mongo_repository.py

1. Connect via `MONGODB_URI` env (default `mongodb://localhost:27017`); database `sizing_{slug}`.
2. Assume seed has run (500 docs per top-level collection); tests are integration-style against live local Mongo.
3. Cover each repository method with at least one assertion:
   - `find_by_key`: returns doc with `detailLines` list for a known seeded `cKey` (e.g. `K0000000000000000000001`).
   - `find_detail_lines`: returns ordered lines for same key.
   - `find_release`: returns a release doc when composite key matches seeded data (read one doc from collection first if needed).
   - `count_by_status`: returns count > 0 for status present in seed (e.g. `"A"`).
4. Use `pytest`; no mocks for MongoDB in this file.
5. Import repository from same directory (`mongo_repository.py` in `outputs/`).

## Do not

- Generate repository or tests before approval.
- Run legacy Java/SQL code — translation only.
- Invent collection or field names not in approved `data-model.md`.
