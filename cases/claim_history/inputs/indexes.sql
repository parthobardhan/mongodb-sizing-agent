CREATE UNIQUE INDEX idx_release_composite ON CLIENT_RELEASE_TABLE (cKey, cKey_Type, cCopy_Number);
CREATE INDEX idx_history_ckey ON CLIENT_DOCUMENT_HISTORY (cKey);
CREATE INDEX idx_detail_ckey ON CLIENT_DOCUMENT_DETAIL_HISTORY (cKey, cLine_Number);
