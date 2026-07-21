# Data model: claims-document-history

**Approval status:** pending

## 1. Use case summary

Claims document history workload: anchor claim documents with embedded line-level detail for the dominant read path (parent + all lines in one round trip, 50 ms SLA). Release rows live in a separate collection, keyed by composite natural key `(cKey, cKey_Type, cCopy_Number)`.

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| CLIENT_DOCUMENT_HISTORY | anchor | `client_document_history` |
| CLIENT_DOCUMENT_DETAIL_HISTORY | embedded | `detailLines[]` in `client_document_history` |
| CLIENT_RELEASE_TABLE | separate_collection | `client_release_table` |

## 3. Relational → MongoDB mapping

| Table / column | Collection / field |
|----------------|-------------------|
| CLIENT_DOCUMENT_HISTORY.cKey | client_document_history.cKey |
| CLIENT_DOCUMENT_HISTORY.cSuper_Key | client_document_history.cSuper_Key |
| CLIENT_DOCUMENT_HISTORY.cClaim_Number | client_document_history.cClaim_Number |
| CLIENT_DOCUMENT_HISTORY.cStatus | client_document_history.cStatus |
| CLIENT_DOCUMENT_HISTORY.cCreated_Date | client_document_history.cCreated_Date |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cKey | *(parent key; not duplicated in array elements)* |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cLine_Number | client_document_history.detailLines[].cLine_Number |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cClaim_Number | client_document_history.detailLines[].cClaim_Number |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cAmount | client_document_history.detailLines[].cAmount |
| CLIENT_RELEASE_TABLE.cKey | client_release_table.cKey |
| CLIENT_RELEASE_TABLE.cKey_Type | client_release_table.cKey_Type |
| CLIENT_RELEASE_TABLE.cCopy_Number | client_release_table.cCopy_Number |
| CLIENT_RELEASE_TABLE.cRelease_Date | client_release_table.cRelease_Date |

## 4. Collections (sample documents)

Database: `sizing_claims_document_history`

**client_document_history** — ~5 `detailLines` per doc (avgCardinality 5).

```json
{
  "cKey": "CLM2026071400000000001",
  "cSuper_Key": "SUP2026071400000000001",
  "cClaim_Number": "CLM-2026-000001",
  "cStatus": "A",
  "cCreated_Date": "2026-07-14T10:00:00Z",
  "detailLines": [
    {
      "cLine_Number": 1,
      "cClaim_Number": "CLM-2026-000001",
      "cAmount": 1250.00
    },
    {
      "cLine_Number": 2,
      "cClaim_Number": "CLM-2026-000001",
      "cAmount": 340.50
    }
  ]
}
```

**client_release_table** — one doc per release row; unique compound on `(cKey, cKey_Type, cCopy_Number)`.

```json
{
  "cKey": "CLM2026071400000000001",
  "cKey_Type": "OR",
  "cCopy_Number": 1,
  "cRelease_Date": "2026-07-14T15:30:00Z"
}
```

## 5. Embedding vs referencing

- **Embed detail lines:** `dataModelingNotes` state that detail lines are read with the parent claim document on every hot-path query. The relational schema joins history to detail on `cKey` with a composite primary key `(cKey, cLine_Number)` on detail — lines are always scoped to a parent document. Embedding eliminates the JOIN and satisfies the 50 ms SLA with a single `find_one`.
- **Separate release rows:** Release rows are keyed by a distinct composite natural key `(cKey, cKey_Type, cCopy_Number)` and are not described as co-read with history on the hot path. Storing them in `client_release_table` avoids bloating history documents (8M release rows vs 12M history docs) and supports direct composite lookups without loading parent aggregates.

## 6. Sizing inputs summary

- Database production document count: **20,000,000**
- `client_document_history`: 12,000,000 (anchor)
- `client_release_table`: 8,000,000 (separate)
- Embedded CLIENT_DOCUMENT_DETAIL_HISTORY: **12000000:60000000** → avg **5** (derived from `intake.json` `productionRowCounts`)

## 7. Index strategy

| Collection | Index | Relational source | Query path |
|------------|-------|-------------------|------------|
| `client_document_history` | `{ cKey: 1 }` unique | `idx_history_ckey` / PK | Parent + embedded detail lookup by `cKey` |
| `client_release_table` | `{ cKey: 1, cKey_Type: 1, cCopy_Number: 1 }` unique | `idx_release_composite` / PK | Composite natural-key lookup |

- **No index on embedded `detailLines`:** relational `idx_detail_ckey` on `(cKey, cLine_Number)` is subsumed by parent `cKey` lookup when lines are embedded.
- **No redundant prefix compounds:** the release composite index covers prefix lookups on `(cKey)`, `(cKey, cKey_Type)`, and the full natural key; no shorter duplicate compounds on the same fields.

## 8. Rationale

Three relational tables collapse to two MongoDB collections. Embedding detail lines matches the dominant access pattern described in intake (parent + all lines in one round trip) and the relational join key on `cKey`. Release rows remain in a separate collection to support composite natural-key lookups and an independent row lifecycle without inflating history documents.

## 9. Assumptions

- Average 5 detail lines per claim document at production scale (60M / 12M), per `intake.json` `productionRowCounts`.
- Release rows are a separate bounded collection; not embedded in history documents, per composite-key access pattern in `dataModelingNotes`.
- `cKey` is stored as a field with a unique index (not MongoDB `_id`), preserving natural-key parity with the relational primary key.

## 10. Approval

- Status: **pending**
- Approved at: *(not yet approved)*
