"""PyMongo repository migrated from legacy ClaimDocumentRepository.java."""

from __future__ import annotations

from typing import Any

from pymongo.database import Database

COL_HISTORY = "client_document_history"
COL_RELEASE = "client_release_table"


class ClaimDocumentRepository:
    """MongoDB data-access layer equivalent to legacy JDBC ClaimDocumentRepository."""

    def __init__(self, db: Database) -> None:
        self._history = db[COL_HISTORY]
        self._release = db[COL_RELEASE]

    def find_by_key(self, c_key: str) -> dict[str, Any] | None:
        """Legacy SQL:
        SELECT h.cKey, h.cSuper_Key, h.cClaim_Number, h.cStatus, h.cCreated_Date,
               d.cLine_Number, d.cClaim_Number AS detail_claim, d.cAmount
        FROM CLIENT_DOCUMENT_HISTORY h
        LEFT JOIN CLIENT_DOCUMENT_DETAIL_HISTORY d ON h.cKey = d.cKey
        WHERE h.cKey = ?
        ORDER BY d.cLine_Number
        """
        return self._history.find_one({"cKey": c_key})

    def find_detail_lines(self, c_key: str) -> list[dict[str, Any]]:
        """Legacy SQL:
        SELECT cLine_Number, cClaim_Number, cAmount
        FROM CLIENT_DOCUMENT_DETAIL_HISTORY
        WHERE cKey = ?
        ORDER BY cLine_Number
        """
        doc = self._history.find_one({"cKey": c_key}, {"detailLines": 1, "_id": 0})
        if not doc:
            return []
        lines = doc.get("detailLines", [])
        return sorted(lines, key=lambda line: line["cLine_Number"])

    def find_release(
        self, c_key: str, c_key_type: str, c_copy_number: int
    ) -> dict[str, Any] | None:
        """Legacy SQL:
        SELECT cKey, cKey_Type, cCopy_Number, cRelease_Date
        FROM CLIENT_RELEASE_TABLE
        WHERE cKey = ? AND cKey_Type = ? AND cCopy_Number = ?
        """
        return self._release.find_one(
            {
                "cKey": c_key,
                "cKey_Type": c_key_type,
                "cCopy_Number": c_copy_number,
            }
        )

    def count_by_status(self, c_status: str) -> int:
        """Legacy SQL:
        SELECT COUNT(*) FROM CLIENT_DOCUMENT_HISTORY WHERE cStatus = ?
        """
        return self._history.count_documents({"cStatus": c_status})
