-- Payment settlement platform (legacy relational model)
-- Financial services: payment instructions, allocation lines, settlement batches

CREATE TABLE PAYMENT_INSTRUCTION (
  instructionId VARCHAR(36) PRIMARY KEY,
  accountId VARCHAR(20) NOT NULL,
  paymentReference VARCHAR(35) NOT NULL,
  currencyCode CHAR(3) NOT NULL,
  totalAmount DECIMAL(18,4) NOT NULL,
  instructionStatus CHAR(2) NOT NULL,
  valueDate DATE NOT NULL,
  createdAt TIMESTAMP NOT NULL
);

CREATE TABLE PAYMENT_ALLOCATION_LINE (
  instructionId VARCHAR(36) NOT NULL,
  lineNumber INT NOT NULL,
  beneficiaryAccount VARCHAR(34) NOT NULL,
  allocationAmount DECIMAL(18,4) NOT NULL,
  costCenter VARCHAR(10),
  PRIMARY KEY (instructionId, lineNumber),
  FOREIGN KEY (instructionId) REFERENCES PAYMENT_INSTRUCTION(instructionId)
);

CREATE TABLE SETTLEMENT_BATCH (
  instructionId VARCHAR(36) NOT NULL,
  settlementRail CHAR(3) NOT NULL,
  batchSequence INT NOT NULL,
  settlementStatus CHAR(2) NOT NULL,
  settledAt TIMESTAMP,
  PRIMARY KEY (instructionId, settlementRail, batchSequence),
  FOREIGN KEY (instructionId) REFERENCES PAYMENT_INSTRUCTION(instructionId)
);
