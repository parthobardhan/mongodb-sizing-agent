# Data model: payment-settlement-platform

**Approval status:** approved

## 1. Use case summary

Payment settlement platform workload: anchor payment instructions with embedded allocation lines for the dominant authorization/settlement read path (parent + all lines in one round trip, 40 ms SLA). Settlement batches live in a separate collection, keyed by composite natural key `(instructionId, settlementRail, batchSequence)`.

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| PAYMENT_INSTRUCTION | anchor | `payment_instruction` |
| PAYMENT_ALLOCATION_LINE | embedded | `allocationLines[]` in `payment_instruction` |
| SETTLEMENT_BATCH | separate_collection | `settlement_batch` |

## 3. Relational → MongoDB mapping

| Table / column | Collection / field |
|----------------|-------------------|
| PAYMENT_INSTRUCTION.instructionId | payment_instruction.instructionId |
| PAYMENT_INSTRUCTION.accountId | payment_instruction.accountId |
| PAYMENT_INSTRUCTION.paymentReference | payment_instruction.paymentReference |
| PAYMENT_INSTRUCTION.currencyCode | payment_instruction.currencyCode |
| PAYMENT_INSTRUCTION.totalAmount | payment_instruction.totalAmount |
| PAYMENT_INSTRUCTION.instructionStatus | payment_instruction.instructionStatus |
| PAYMENT_INSTRUCTION.valueDate | payment_instruction.valueDate |
| PAYMENT_INSTRUCTION.createdAt | payment_instruction.createdAt |
| PAYMENT_ALLOCATION_LINE.instructionId | *(parent key; not duplicated in array elements)* |
| PAYMENT_ALLOCATION_LINE.lineNumber | payment_instruction.allocationLines[].lineNumber |
| PAYMENT_ALLOCATION_LINE.beneficiaryAccount | payment_instruction.allocationLines[].beneficiaryAccount |
| PAYMENT_ALLOCATION_LINE.allocationAmount | payment_instruction.allocationLines[].allocationAmount |
| PAYMENT_ALLOCATION_LINE.costCenter | payment_instruction.allocationLines[].costCenter |
| SETTLEMENT_BATCH.instructionId | settlement_batch.instructionId |
| SETTLEMENT_BATCH.settlementRail | settlement_batch.settlementRail |
| SETTLEMENT_BATCH.batchSequence | settlement_batch.batchSequence |
| SETTLEMENT_BATCH.settlementStatus | settlement_batch.settlementStatus |
| SETTLEMENT_BATCH.settledAt | settlement_batch.settledAt |

## 4. Collections (sample documents)

Database: `sizing_payment_settlement_platform`

**payment_instruction** — ~3 `allocationLines` per doc (avgCardinality 3).

```json
{
  "instructionId": "PAY2026072200000000001",
  "accountId": "ACC00000000000000001",
  "paymentReference": "REF-2026-000001",
  "currencyCode": "USD",
  "totalAmount": 1500.00,
  "instructionStatus": "AU",
  "valueDate": "2026-07-22",
  "createdAt": "2026-07-22T10:00:00Z",
  "allocationLines": [
    {
      "lineNumber": 1,
      "beneficiaryAccount": "GB29NWBK60161331926819",
      "allocationAmount": 1000.00,
      "costCenter": "CC001"
    },
    {
      "lineNumber": 2,
      "beneficiaryAccount": "DE89370400440532013000",
      "allocationAmount": 500.00,
      "costCenter": "CC002"
    }
  ]
}
```

**settlement_batch** — one doc per settlement row; unique compound on `(instructionId, settlementRail, batchSequence)`.

```json
{
  "instructionId": "PAY2026072200000000001",
  "settlementRail": "ACH",
  "batchSequence": 1,
  "settlementStatus": "ST",
  "settledAt": "2026-07-22T15:30:00Z"
}
```

## 5. Embedding vs referencing

- **Embed allocation lines:** `dataModelingNotes` and legacy `findByInstructionId` confirm allocation lines are read with the parent payment on every authorization/settlement hot path (LEFT JOIN). `findAllocationLines` projects from the same parent document; lines are not queried independently at volume. Embedding eliminates the JOIN and satisfies the 40 ms SLA with a single `find_one`.
- **Separate settlement batches:** Settlement batches are keyed by a distinct composite natural key `(instructionId, settlementRail, batchSequence)` and reconciled independently via `findSettlementBatch`. Storing them in `settlement_batch` avoids bloating payment documents (6M batch rows vs 15M instructions) and supports direct composite lookups without loading parent aggregates.

## 6. Sizing inputs summary

- Database production document count: **21,000,000**
- `payment_instruction`: 15,000,000 (anchor)
- `settlement_batch`: 6,000,000 (separate)
- Embedded PAYMENT_ALLOCATION_LINE: **15000000:45000000** → avg **3** (derived from `intake.json` `productionRowCounts`)

## 7. Index strategy

| Collection | Index | Legacy source | Query path |
|------------|-------|---------------|------------|
| `payment_instruction` | `{ instructionId: 1 }` unique | `idx_payment_instruction_id` / PK | `findByInstructionId`, `findAllocationLines` |
| `payment_instruction` | `{ accountId: 1, instructionStatus: 1 }` | `idx_payment_account_status` | account + status filters |
| `payment_instruction` | `{ instructionStatus: 1 }` | *(added for DAO)* | `countByInstructionStatus` — status-only count not covered by account+status compound |
| `settlement_batch` | `{ instructionId: 1, settlementRail: 1, batchSequence: 1 }` unique | `idx_settlement_composite` / PK | `findSettlementBatch` |
| `settlement_batch` | `{ settlementRail: 1, settlementStatus: 1 }` | `idx_settlement_rail` | rail + status reconciliation filters |

- **No index on embedded `allocationLines`:** relational `idx_allocation_instruction_line` is subsumed by parent `instructionId` lookup when lines are embedded.
- **No redundant prefix compounds:** the settlement composite index covers all prefix lookups on `(instructionId)`, `(instructionId, settlementRail)`, and the full natural key; no shorter duplicate compounds on the same fields. The account+status compound covers its `accountId` prefix; a separate status-only index is required for `countByInstructionStatus` (status is not a usable left-prefix of that compound).

## 8. Rationale

Three relational tables collapse to two MongoDB collections. Embedding allocation lines matches the dominant access pattern (parent + all lines in one round trip) and aligns with intake guidance that allocation lines are always co-read with the payment instruction. Settlement batches remain in a separate collection to support composite natural-key lookups and an independent reconciliation lifecycle without inflating payment documents.

## 9. Assumptions

- Average 3 allocation lines per payment instruction at production scale (45M / 15M), per `intake.json` `productionRowCounts`.
- Settlement batches are a separate bounded collection; not embedded in payment instructions, per composite-key access pattern in `dataModelingNotes` and legacy `findSettlementBatch`.
- `instructionStatus` single-field index is added for `countByInstructionStatus` dashboard queries; relational DDL indexes `(accountId, instructionStatus)` which does not cover status-only predicates.
- `instructionId` is stored as a field with a unique index (not MongoDB `_id`), preserving natural-key parity with legacy JDBC.

## 10. Approval

- Status: **approved**
- Approved by: parthobardhan
- Via: GitHub PR comment
- Approved at: 2026-07-23T22:01:00Z
