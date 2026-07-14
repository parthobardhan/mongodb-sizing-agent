package com.example.claims.legacy;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Legacy JDBC data-access layer for claim document history.
 * Hot-path queries against relational tables; never migrated in this artifact.
 */
public class ClaimDocumentRepository {

    private final Connection connection;

    public ClaimDocumentRepository(Connection connection) {
        this.connection = connection;
    }

    /**
     * Load a claim document and all detail lines in one round trip (JOIN hot path).
     */
    public ClaimDocument findByKey(String cKey) throws SQLException {
        String sql =
                "SELECT h.cKey, h.cSuper_Key, h.cClaim_Number, h.cStatus, h.cCreated_Date, "
                        + "d.cLine_Number, d.cClaim_Number AS detail_claim, d.cAmount "
                        + "FROM CLIENT_DOCUMENT_HISTORY h "
                        + "LEFT JOIN CLIENT_DOCUMENT_DETAIL_HISTORY d ON h.cKey = d.cKey "
                        + "WHERE h.cKey = ? "
                        + "ORDER BY d.cLine_Number";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, cKey);
            try (ResultSet rs = ps.executeQuery()) {
                ClaimDocument doc = null;
                List<DetailLine> lines = new ArrayList<>();
                while (rs.next()) {
                    if (doc == null) {
                        doc = new ClaimDocument(
                                rs.getString("cKey"),
                                rs.getString("cSuper_Key"),
                                rs.getString("cClaim_Number"),
                                rs.getString("cStatus"),
                                rs.getTimestamp("cCreated_Date"));
                    }
                    int lineNumber = rs.getInt("cLine_Number");
                    if (!rs.wasNull()) {
                        lines.add(
                                new DetailLine(
                                        lineNumber,
                                        rs.getString("detail_claim"),
                                        rs.getBigDecimal("cAmount")));
                    }
                }
                if (doc == null) {
                    return null;
                }
                doc.setDetailLines(lines);
                return doc;
            }
        }
    }

    /**
     * Detail lines only, ordered by line number.
     */
    public List<DetailLine> findDetailLines(String cKey) throws SQLException {
        String sql =
                "SELECT cLine_Number, cClaim_Number, cAmount "
                        + "FROM CLIENT_DOCUMENT_DETAIL_HISTORY "
                        + "WHERE cKey = ? "
                        + "ORDER BY cLine_Number";

        List<DetailLine> lines = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, cKey);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    lines.add(
                            new DetailLine(
                                    rs.getInt("cLine_Number"),
                                    rs.getString("cClaim_Number"),
                                    rs.getBigDecimal("cAmount")));
                }
            }
        }
        return lines;
    }

    /**
     * Composite natural-key lookup on release rows.
     */
    public ReleaseRow findRelease(String cKey, String cKeyType, int cCopyNumber) throws SQLException {
        String sql =
                "SELECT cKey, cKey_Type, cCopy_Number, cRelease_Date "
                        + "FROM CLIENT_RELEASE_TABLE "
                        + "WHERE cKey = ? AND cKey_Type = ? AND cCopy_Number = ?";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, cKey);
            ps.setString(2, cKeyType);
            ps.setInt(3, cCopyNumber);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                return new ReleaseRow(
                        rs.getString("cKey"),
                        rs.getString("cKey_Type"),
                        rs.getInt("cCopy_Number"),
                        rs.getTimestamp("cRelease_Date"));
            }
        }
    }

    /**
     * Count claim documents by status (dashboard / batch aggregate).
     */
    public long countByStatus(String cStatus) throws SQLException {
        String sql = "SELECT COUNT(*) FROM CLIENT_DOCUMENT_HISTORY WHERE cStatus = ?";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, cStatus);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    /** Minimal row DTOs for legacy JDBC mapping. */
    public static class ClaimDocument {
        private final String cKey;
        private final String cSuperKey;
        private final String cClaimNumber;
        private final String cStatus;
        private final java.sql.Timestamp cCreatedDate;
        private List<DetailLine> detailLines = List.of();

        public ClaimDocument(
                String cKey,
                String cSuperKey,
                String cClaimNumber,
                String cStatus,
                java.sql.Timestamp cCreatedDate) {
            this.cKey = cKey;
            this.cSuperKey = cSuperKey;
            this.cClaimNumber = cClaimNumber;
            this.cStatus = cStatus;
            this.cCreatedDate = cCreatedDate;
        }

        public void setDetailLines(List<DetailLine> detailLines) {
            this.detailLines = detailLines;
        }
    }

    public static class DetailLine {
        public final int cLineNumber;
        public final String cClaimNumber;
        public final java.math.BigDecimal cAmount;

        public DetailLine(int cLineNumber, String cClaimNumber, java.math.BigDecimal cAmount) {
            this.cLineNumber = cLineNumber;
            this.cClaimNumber = cClaimNumber;
            this.cAmount = cAmount;
        }
    }

    public static class ReleaseRow {
        public final String cKey;
        public final String cKeyType;
        public final int cCopyNumber;
        public final java.sql.Timestamp cReleaseDate;

        public ReleaseRow(
                String cKey, String cKeyType, int cCopyNumber, java.sql.Timestamp cReleaseDate) {
            this.cKey = cKey;
            this.cKeyType = cKeyType;
            this.cCopyNumber = cCopyNumber;
            this.cReleaseDate = cReleaseDate;
        }
    }
}
