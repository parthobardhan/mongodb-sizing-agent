# Data model: payment-settlement-platform

**Approval status:** pending

## 1. Use case summary

Payment settlement platform workload: anchor payment instructions with embedded allocation lines for the dominant authorization hot path (parent + all lines in one round trip, 40 ms SLA). Settlement batches live in a separate collection, keyed by composite natural key `(instructionId, settlementRail, batchSequence)` and reconciled independently from the payment header.

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| PAYMENT_INSTRUCTION | anchor | `payment_instructions` |
| PAYMENT_ALLOCATION_LINE | embedded | `allocationLines[]` in `payment_instructions` |
| SETTLEMENT_BATCH | separate_collection | `settlement_batches` |

## 3. Relational → MongoDB mapping

| Table / column | Collection / field |
|----------------|-------------------|
| PAYMENT_INSTRUCTION.instructionId | payment_instructions.instructionId |
| PAYMENT_INSTRUCTION.accountId | payment_instructions.accountId |
| PAYMENT_INSTRUCTION.paymentReference | payment_instructions.paymentReference |
| PAYMENT_INSTRUCTION.currencyCode | payment_instructions.currencyCode |
| PAYMENT_INSTRUCTION.totalAmount | payment_instructions.totalAmount |
| PAYMENT_INSTRUCTION.instructionStatus | payment_instructions.instructionStatus |
| PAYMENT_INSTRUCTION.valueDate | payment_instructions.valueDate |
| PAYMENT_INSTRUCTION.createdAt | payment_instructions.createdAt |
| PAYMENT_ALLOCATION_LINE.instructionId | *(parent key; not duplicated in array elements)* |
| PAYMENT_ALLOCATION_LINE.lineNumber | payment_instructions.allocationLines[].lineNumber |
| PAYMENT_ALLOCATION_LINE.beneficiaryAccount | payment_instructions.allocationLines[].beneficiaryAccount |
| PAYMENT_ALLOCATION_LINE.allocationAmount | payment_instructions.allocationLines[].allocationAmount |
| PAYMENT_ALLOCATION_LINE.costCenter | payment_instructions.allocationLines[].costCenter |
| SETTLEMENT_BATCH.instructionId | settlement_batches.instructionId |
| SETTLEMENT_BATCH.settlementRail | settlement_batches.settlementRail |
| SETTLEMENT_BATCH.batchSequence | settlement_batches.batchSequence |
| SETTLEMENT_BATCH.settlementStatus | settlement_batches.settlementStatus |
| SETTLEMENT_BATCH.settledAt | settlement_batches.settledAt |

## 4. Collections (sample documents)

Database: `sizing_payment_settlement_platform`

**payment_instructions** — ~3 `allocationLines` per doc (avgCardinality 3).

```json
{
  "instructionId": "550e8400-e29b-41d4-a716-446655440000",
  "accountId": "ACC-0000123456",
  "paymentReference": "PAY-2026-000001",
  "currencyCode": "USD",
  "totalAmount": 15000.0000,
  "instructionStatus": "AU",
  "valueDate": "2026-07-23",
  "createdAt": "2026-07-23T08:00:00Z",
  "allocationLines": [
    {
      "lineNumber": 1,
      "beneficiaryAccount": "GB82WEST12345698765432",
      "allocationAmount": 10000.0000,
      "costCenter": "CC-OPS-01"
    },
    {
      "lineNumber": 2,
      "beneficiaryAccount": "DE89370400440532013000",
      "allocationAmount": 5000.0000,
      "costCenter": "CC-OPS-02"
    }
  ]
}
```

**settlement_batches** — one doc per batch row; unique compound on `(instructionId, settlementRail, batchSequence)`.

```json
{
  "instructionId": "550e8400-e29b-41d4-a716-446655440000",
  "settlementRail": "ACH",
  "batchSequence": 1,
  "settlementStatus": "ST",
  "settledAt": "2026-07-23T10:30:00Z"
}
```

## 5. Embedding vs referencing

- **Embed allocation lines:** `dataModelingNotes` and legacy `findByInstructionId` confirm allocation lines are read with the parent payment instruction on every authorization and settlement hot path (LEFT JOIN, single round trip). `findAllocationLines` projects from the same parent document for audit drill-down; lines are not queried at volume without their parent. Embedding eliminates the JOIN and satisfies the 40 ms SLA with a single `find_one`.
- **Separate settlement batches:** Settlement batches are keyed by a distinct composite natural key `(instructionId, settlementRail, batchSequence)` and queried independently via `findSettlementBatch`. Storing them in `settlement_batches` avoids bloating payment instruction documents (6M batch rows vs 15M instruction docs) and supports direct composite lookups and rail-level reconciliation without loading parent aggregates.

## 6. Sizing inputs summary

- Database production document count: **21,000,000**
- `payment_instructions`: 15,000,000 (anchor)
- `settlement_batches`: 6,000,000 (separate)
- Embedded PAYMENT_ALLOCATION_LINE: **15000000:45000000** → avg **3** (derived from `intake.json` `productionRowCounts`)

## 7. Index strategy

| Collection | Index | Legacy source | Query path |
|------------|-------|---------------|------------|
| `payment_instructions` | `{ instructionId: 1 }` unique | `idx_payment_instruction_id` / PK | `findByInstructionId`, `findAllocationLines` |
| `payment_instructions` | `{ accountId: 1, instructionStatus: 1 }` | `idx_payment_account_status` | Account-scoped status filtering |
| `payment_instructions` | `{ instructionStatus: 1 }` | *(added for DAO)* | `countByInstructionStatus` — status-only count not indexed in relational DDL |
| `settlement_batches` | `{ instructionId: 1, settlementRail: 1, batchSequence: 1 }` unique | `idx_settlement_composite` | `findSettlementBatch` |
| `settlement_batches` | `{ settlementRail: 1, settlementStatus: 1 }` | `idx_settlement_rail` | Rail-level reconciliation / monitoring |

- **No index on embedded `allocationLines`:** relational `idx_allocation_instruction_line` is subsumed by parent `instructionId` lookup when lines are embedded.
- **No redundant prefix compounds:** the settlement composite index covers prefix lookups on `(instructionId)`, `(instructionId, settlementRail)`, and the full natural key; no shorter duplicate compounds on the same fields. The `(settlementRail, settlementStatus)` index uses a different field order and serves a distinct query pattern.

## 8. Rationale

Three relational tables collapse to two MongoDB collections. Embedding allocation lines matches the dominant access pattern (parent + all lines in one round trip) and aligns with intake guidance that allocation lines are always co-read with the parent on authorization and settlement hot paths. Settlement batches remain in a separate collection to support composite natural-key lookups, rail-level reconciliation, and an independent row lifecycle without inflating payment instruction documents.

## 9. Assumptions

- Average 3 allocation lines per payment instruction at production scale (45M / 15M), per `intake.json` `productionRowCounts`.
- Settlement batches are a separate bounded collection; not embedded in payment instructions, per composite-key access pattern in `dataModelingNotes` and legacy `findSettlementBatch`.
- `instructionStatus` single-field index is added for `countByInstructionStatus` dashboard queries; relational DDL defines `(accountId, instructionStatus)` but does not index status alone.
- `instructionId` is stored as a field with a unique index (not MongoDB `_id`), preserving natural-key parity with legacy JDBC.

## 10. Approval

- Status: **pending**
- Approved at: —
