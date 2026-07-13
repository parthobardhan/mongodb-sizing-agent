-- Minimal DocumentHistory-style tables for sizing example

CREATE TABLE CLIENT_DOCUMENT_HISTORY (
  cKey VARCHAR(23) PRIMARY KEY,
  cSuper_Key VARCHAR(23),
  cClaim_Number VARCHAR(30),
  cStatus CHAR(1),
  cCreated_Date TIMESTAMP
);

CREATE TABLE CLIENT_DOCUMENT_DETAIL_HISTORY (
  cKey VARCHAR(23),
  cClaim_Number VARCHAR(30),
  cLine_Number INT,
  cAmount DECIMAL(12,2),
  PRIMARY KEY (cKey, cLine_Number)
);

CREATE TABLE CLIENT_RELEASE_TABLE (
  cKey VARCHAR(23),
  cKey_Type CHAR(2),
  cCopy_Number INT,
  cRelease_Date TIMESTAMP,
  PRIMARY KEY (cKey, cKey_Type, cCopy_Number)
);
