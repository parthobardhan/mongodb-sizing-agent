# MongoDB Sizing Agent — agent workflow

## Phases

1. **Intake** — Validate `intake.json` (useCaseName, queryLatencySlaMs, optional `productionRowCounts`, `dataModelingNotes`); read `schema.sql`, `indexes.sql`, ERD images. Ask when embed vs reference, hot paths, or keys are unclear.
2. **Model** — Write `cases/{useCase}/outputs/data-model.md` with disposition table, mapping, samples, index strategy, **Rationale**, **Assumptions**, approval block (`pending`). For non-obvious embed vs reference, use `/mongodb-schema-design`, then map to disposition via `/mongodb-document-modeling`.
3. **Sizing gate** — Write `cases/{useCase}/outputs/sizing_inputs.json` (agent-generated only): `productionDocumentCount` per top-level collection; `avgCardinality` for embedded (derive from `intake.json` `productionRowCounts` when possible).
4. **Approval** — User says `approve`; set status to `approved` in `data-model.md`. **Do not** write `seed.py`, start Docker, or run sizing before approval.
5. **Generate** — `seed.py` (500 docs per top-level collection), `mongodb_indexes.json` (no redundant compound prefixes).
6. **Tools** — `run_local_stack.sh` → seed → `apply_indexes.py` → `size_from_dbstats.py` → optional cleanup.

## Gates

- Missing anchor production count → ask (or document assumption in Assumptions); prefer `intake.json` `productionRowCounts`.
- Embedded cardinality: prefer `childCount / parentCount` from `productionRowCounts` when both known.
- Never invent production row counts silently.

## Index generation

Emit **one** compound index per relational composite; do not also emit prefix-only indexes on the same fields/options. Document prefix coverage in `data-model.md`.

## Deterministic numbers

Atlas Disk/RAM come **only** from `scripts/size_from_dbstats.py` (dbStats scaling). Per-collection collStats rows are report detail, not summed for Disk/RAM.

## SDK

- Local runtime: `LocalAgentOptions(cwd=project_root, setting_sources=["project", "plugins"])`
- `mode="plan"` until approval; `SendOptions(mode="agent")` for implementation
- Persist `agent_id` in `outputs/session.json` for `--resume`
