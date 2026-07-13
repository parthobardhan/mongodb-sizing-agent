---
name: relational-intake
description: Intake checklist for relational schema, indexes, and case inputs for MongoDB sizing agent.
---

# Relational intake

When starting a case under `cases/{useCase}/inputs/`:

1. Validate `intake.json` (useCaseName, queryLatencySlaMs; optional `productionRowCounts`, `dataModelingNotes`).
2. Read `schema.sql` / `schema.txt` or ERD image paths.
3. Read `indexes.sql` or `indexes.json` when provided.
4. Ask when: 1:N vs M:N unclear, partition/shard key unknown, embed vs reference unclear, or user claimed indexes but none provided.
5. `productionRowCounts` in intake are relational table row counts (customer-provided). Do not require them to name MongoDB dispositions.

Record clarifications in `data-model.md` Assumptions if the user cannot answer.
