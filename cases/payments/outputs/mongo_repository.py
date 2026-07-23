"""PyMongo repository migrated from legacy PaymentSettlementRepository.java."""

from __future__ import annotations

from typing import Any

from pymongo.database import Database

COL_INSTRUCTION = "payment_instruction"
COL_SETTLEMENT = "settlement_batch"


class PaymentSettlementRepository:
    """MongoDB data-access layer equivalent to legacy JDBC PaymentSettlementRepository."""

    def __init__(self, db: Database) -> None:
        self._instruction = db[COL_INSTRUCTION]
        self._settlement = db[COL_SETTLEMENT]

    def find_by_instruction_id(self, instruction_id: str) -> dict[str, Any] | None:
        """Legacy SQL:
        SELECT p.instructionId, p.accountId, p.paymentReference, p.currencyCode,
               p.totalAmount, p.instructionStatus, p.valueDate, p.createdAt,
               a.lineNumber, a.beneficiaryAccount, a.allocationAmount, a.costCenter
        FROM PAYMENT_INSTRUCTION p
        LEFT JOIN PAYMENT_ALLOCATION_LINE a ON p.instructionId = a.instructionId
        WHERE p.instructionId = ?
        ORDER BY a.lineNumber
        """
        return self._instruction.find_one({"instructionId": instruction_id})

    def find_allocation_lines(self, instruction_id: str) -> list[dict[str, Any]]:
        """Legacy SQL:
        SELECT lineNumber, beneficiaryAccount, allocationAmount, costCenter
        FROM PAYMENT_ALLOCATION_LINE
        WHERE instructionId = ?
        ORDER BY lineNumber
        """
        doc = self._instruction.find_one(
            {"instructionId": instruction_id}, {"allocationLines": 1, "_id": 0}
        )
        if not doc:
            return []
        lines = doc.get("allocationLines", [])
        return sorted(lines, key=lambda line: line["lineNumber"])

    def find_settlement_batch(
        self, instruction_id: str, settlement_rail: str, batch_sequence: int
    ) -> dict[str, Any] | None:
        """Legacy SQL:
        SELECT instructionId, settlementRail, batchSequence, settlementStatus, settledAt
        FROM SETTLEMENT_BATCH
        WHERE instructionId = ? AND settlementRail = ? AND batchSequence = ?
        """
        return self._settlement.find_one(
            {
                "instructionId": instruction_id,
                "settlementRail": settlement_rail,
                "batchSequence": batch_sequence,
            }
        )

    def count_by_instruction_status(self, instruction_status: str) -> int:
        """Legacy SQL:
        SELECT COUNT(*) FROM PAYMENT_INSTRUCTION WHERE instructionStatus = ?
        """
        return self._instruction.count_documents({"instructionStatus": instruction_status})
