---
name: mongodb-document-modeling
description: Propose MongoDB collections, disposition, sizing inputs gate, and data-model.md for sizing agent.
---

# MongoDB document modeling

## Disposition (per relational table)

- **anchor** — top-level collection; 1 row ≈ 1 document
- **separate_collection** — own collection with references
- **embedded** — array/subdocument in parent; needs avgCardinality

## data-model.md sections

Use case, disposition table, mapping, sample docs, embedding rationale, sizing inputs summary, index strategy (prefix coverage), Rationale, Assumptions, Approval block.

## Post-model gate

1. List every top-level collection + anchor table.
2. Write `outputs/sizing_inputs.json` (agent-generated; never in `inputs/`).
3. Set `productionDocumentCount` per top-level collection; derive embedded `avgCardinality` from `intake.json` `productionRowCounts`.
4. Set `databaseProductionDocumentCount` (sum of top-level collection docs).
5. Present for user verification; status `pending` until `approve`.

## References

- [MongoDB data modeling best practices](https://www.mongodb.com/docs/manual/data-modeling/best-practices/)
