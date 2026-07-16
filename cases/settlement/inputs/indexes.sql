CREATE INDEX idx_payment_instruction_id ON PAYMENT_INSTRUCTION (instructionId);
CREATE INDEX idx_payment_account_status ON PAYMENT_INSTRUCTION (accountId, instructionStatus);
CREATE INDEX idx_allocation_instruction_line ON PAYMENT_ALLOCATION_LINE (instructionId, lineNumber);
CREATE UNIQUE INDEX idx_settlement_composite ON SETTLEMENT_BATCH (instructionId, settlementRail, batchSequence);
CREATE INDEX idx_settlement_rail ON SETTLEMENT_BATCH (settlementRail, settlementStatus);
