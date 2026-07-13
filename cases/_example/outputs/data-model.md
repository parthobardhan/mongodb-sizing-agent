# Data model: claims-document-history

**Approval status:** approved

## 1. Use case summary

Document history workload: anchor claim documents with embedded line-level detail; release rows in a separate collection keyed by composite natural key.

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| CLIENT_DOCUMENT_HISTORY | anchor | `client_document_history` |
| CLIENT_DOCUMENT_DETAIL_HISTORY | embedded | `detailLines[]` in history doc |
| CLIENT_RELEASE_TABLE | separate_collection | `client_release_table` |

## 3. Relational → MongoDB mapping

| Table / column | Collection / field |
|----------------|-------------------|
| CLIENT_DOCUMENT_HISTORY.cKey | client_document_history.cKey |
| CLIENT_DOCUMENT_DETAIL_HISTORY.* | client_document_history.detailLines[] |
| CLIENT_RELEASE_TABLE.* | client_release_table.* |

## 4. Collections (sample documents)

**client_document_history** — ~5 `detailLines` per doc (avgCardinality 5).

**client_release_table** — one doc per release row; unique compound on (cKey, cKey_Type, cCopy_Number).

## 5. Embedding vs referencing

Detail lines are read with the parent claim; embedded array avoids joins for hot path.

## 6. Sizing inputs summary

- Database production document count: **20,000,000**
- `client_document_history`: 12,000,000 (anchor)
- `client_release_table`: 8,000,000 (separate)
- Embedded CLIENT_DOCUMENT_DETAIL_HISTORY: **1000:5000** → avg **5** (derived)

## 7. Index strategy

- History: single-field `cKey` for lookups by natural key.
- Release: one compound index `(cKey, cKey_Type, cCopy_Number)` covers relational prefix indexes; no redundant shorter compounds.

## 8. Rationale

Reduced seven relational tables to two MongoDB collections plus embedded detail to match access pattern and SLA.

## 9. Assumptions

- Example smoke case uses simplified three-table schema.

## 10. Approval

- Status: **approved**
- Approved at: 2026-06-03T00:00:00Z
