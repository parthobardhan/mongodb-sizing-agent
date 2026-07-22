# Data model: claims-document-history

**Approval status:** approved

## 1. Use case summary

Claims document history workload: anchor claim documents with embedded line-level detail for the dominant read path (parent plus all lines in one round trip, 50 ms SLA). Release rows live in a separate collection, keyed by composite natural key `(cKey, cKey_Type, cCopy_Number)`.

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
| CLIENT_DOCUMENT_DETAIL_HISTORY.cClaim_Number | client_document_history.detailLines[].cClaim_Number |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cLine_Number | client_document_history.detailLines[].cLine_Number |
| CLIENT_DOCUMENT_DETAIL_HISTORY.cAmount | client_document_history.detailLines[].cAmount |
| CLIENT_RELEASE_TABLE.cKey | client_release_table.cKey |
| CLIENT_RELEASE_TABLE.cKey_Type | client_release_table.cKey_Type |
| CLIENT_RELEASE_TABLE.cCopy_Number | client_release_table.cCopy_Number |
| CLIENT_RELEASE_TABLE.cRelease_Date | client_release_table.cRelease_Date |

## 4. Collections (sample documents)

Database: `sizing_claims_document_history`

**client_document_history** — average 5 `detailLines` per document.

```json
{
  "cKey": "CLM2026072200000000001",
  "cSuper_Key": "SUP2026072200000000001",
  "cClaim_Number": "CLM-2026-000001",
  "cStatus": "A",
  "cCreated_Date": "2026-07-22T10:00:00Z",
  "detailLines": [
    {
      "cClaim_Number": "CLM-2026-000001",
      "cLine_Number": 1,
      "cAmount": 1250.00
    }
  ]
}
```

**client_release_table** — one document per release row.

```json
{
  "cKey": "CLM2026072200000000001",
  "cKey_Type": "OR",
  "cCopy_Number": 1,
  "cRelease_Date": "2026-07-22T15:30:00Z"
}
```

## 5. Embedding vs referencing

- **Embed detail lines:** Intake guidance says detail lines are read with the parent claim document on every hot-path query. Embedding removes the relational join and serves the complete aggregate with one lookup.
- **Separate release rows:** Release rows have their own composite natural key and can be addressed independently. Keeping them separate avoids inflating claim history documents and preserves direct composite-key lookups.

## 6. Sizing inputs summary

- Database production document count: **20,000,000**
- `client_document_history`: **12,000,000** (anchor)
- `client_release_table`: **8,000,000** (separate collection)
- Embedded `CLIENT_DOCUMENT_DETAIL_HISTORY`: **60,000,000 / 12,000,000 = 5** average detail lines

## 7. Index strategy

| Collection | Index | Relational source |
|------------|-------|-------------------|
| `client_document_history` | `{ cKey: 1 }` unique | primary key / `idx_history_ckey` |
| `client_release_table` | `{ cKey: 1, cKey_Type: 1, cCopy_Number: 1 }` unique | primary key / `idx_release_composite` |

- The embedded detail table's `(cKey, cLine_Number)` index is replaced by the parent `cKey` lookup; line numbers remain local to `detailLines`.
- The release compound index covers prefix lookups on `(cKey)` and `(cKey, cKey_Type)`, so no redundant prefix indexes are emitted.

## 8. Rationale

Three relational tables become two MongoDB collections. Embedding bounded detail lines matches the declared hot path and reduces query latency by eliminating a join. Release rows remain separate because their composite natural key and independent row count indicate a distinct access path and lifecycle.

## 9. Assumptions

- Detail cardinality remains bounded around the production average of 5 lines per claim document.
- Release rows are queried by the supplied composite natural key.
- `cKey` remains an explicit field with a unique index to preserve relational key parity.

## 10. Approval

- Status: **approved**
- Approved by: partho.bardhan88
- Approved at: 2026-07-22T22:02:38Z
