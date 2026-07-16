package com.example.payments.legacy;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Legacy JDBC data-access layer for payment settlement (authorization + reconciliation).
 * Hot-path queries against relational tables; never executed in this migration artifact.
 */
public class PaymentSettlementRepository {

    private final Connection connection;

    public PaymentSettlementRepository(Connection connection) {
        this.connection = connection;
    }

    /**
     * Load a payment instruction and all allocation lines in one round trip (authorization hot path).
     */
    public PaymentInstruction findByInstructionId(String instructionId) throws SQLException {
        String sql =
                "SELECT p.instructionId, p.accountId, p.paymentReference, p.currencyCode, "
                        + "p.totalAmount, p.instructionStatus, p.valueDate, p.createdAt, "
                        + "a.lineNumber, a.beneficiaryAccount, a.allocationAmount, a.costCenter "
                        + "FROM PAYMENT_INSTRUCTION p "
                        + "LEFT JOIN PAYMENT_ALLOCATION_LINE a ON p.instructionId = a.instructionId "
                        + "WHERE p.instructionId = ? "
                        + "ORDER BY a.lineNumber";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, instructionId);
            try (ResultSet rs = ps.executeQuery()) {
                PaymentInstruction payment = null;
                List<AllocationLine> lines = new ArrayList<>();
                while (rs.next()) {
                    if (payment == null) {
                        payment = new PaymentInstruction(
                                rs.getString("instructionId"),
                                rs.getString("accountId"),
                                rs.getString("paymentReference"),
                                rs.getString("currencyCode"),
                                rs.getBigDecimal("totalAmount"),
                                rs.getString("instructionStatus"),
                                rs.getDate("valueDate"),
                                rs.getTimestamp("createdAt"));
                    }
                    int lineNumber = rs.getInt("lineNumber");
                    if (!rs.wasNull()) {
                        lines.add(
                                new AllocationLine(
                                        lineNumber,
                                        rs.getString("beneficiaryAccount"),
                                        rs.getBigDecimal("allocationAmount"),
                                        rs.getString("costCenter")));
                    }
                }
                if (payment == null) {
                    return null;
                }
                payment.setAllocationLines(lines);
                return payment;
            }
        }
    }

    /**
     * Allocation lines only, ordered by line number (audit drill-down).
     */
    public List<AllocationLine> findAllocationLines(String instructionId) throws SQLException {
        String sql =
                "SELECT lineNumber, beneficiaryAccount, allocationAmount, costCenter "
                        + "FROM PAYMENT_ALLOCATION_LINE "
                        + "WHERE instructionId = ? "
                        + "ORDER BY lineNumber";

        List<AllocationLine> lines = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, instructionId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    lines.add(
                            new AllocationLine(
                                    rs.getInt("lineNumber"),
                                    rs.getString("beneficiaryAccount"),
                                    rs.getBigDecimal("allocationAmount"),
                                    rs.getString("costCenter")));
                }
            }
        }
        return lines;
    }

    /**
     * Composite natural-key lookup on settlement batch (reconciliation hot path).
     */
    public SettlementBatch findSettlementBatch(
            String instructionId, String settlementRail, int batchSequence) throws SQLException {
        String sql =
                "SELECT instructionId, settlementRail, batchSequence, settlementStatus, settledAt "
                        + "FROM SETTLEMENT_BATCH "
                        + "WHERE instructionId = ? AND settlementRail = ? AND batchSequence = ?";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, instructionId);
            ps.setString(2, settlementRail);
            ps.setInt(3, batchSequence);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                return new SettlementBatch(
                        rs.getString("instructionId"),
                        rs.getString("settlementRail"),
                        rs.getInt("batchSequence"),
                        rs.getString("settlementStatus"),
                        rs.getTimestamp("settledAt"));
            }
        }
    }

    /**
     * Count payment instructions by status (operations dashboard / batch monitoring).
     */
    public long countByInstructionStatus(String instructionStatus) throws SQLException {
        String sql = "SELECT COUNT(*) FROM PAYMENT_INSTRUCTION WHERE instructionStatus = ?";

        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, instructionStatus);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    public static class PaymentInstruction {
        private final String instructionId;
        private final String accountId;
        private final String paymentReference;
        private final String currencyCode;
        private final java.math.BigDecimal totalAmount;
        private final String instructionStatus;
        private final java.sql.Date valueDate;
        private final java.sql.Timestamp createdAt;
        private List<AllocationLine> allocationLines = List.of();

        public PaymentInstruction(
                String instructionId,
                String accountId,
                String paymentReference,
                String currencyCode,
                java.math.BigDecimal totalAmount,
                String instructionStatus,
                java.sql.Date valueDate,
                java.sql.Timestamp createdAt) {
            this.instructionId = instructionId;
            this.accountId = accountId;
            this.paymentReference = paymentReference;
            this.currencyCode = currencyCode;
            this.totalAmount = totalAmount;
            this.instructionStatus = instructionStatus;
            this.valueDate = valueDate;
            this.createdAt = createdAt;
        }

        public void setAllocationLines(List<AllocationLine> allocationLines) {
            this.allocationLines = allocationLines;
        }
    }

    public static class AllocationLine {
        public final int lineNumber;
        public final String beneficiaryAccount;
        public final java.math.BigDecimal allocationAmount;
        public final String costCenter;

        public AllocationLine(
                int lineNumber,
                String beneficiaryAccount,
                java.math.BigDecimal allocationAmount,
                String costCenter) {
            this.lineNumber = lineNumber;
            this.beneficiaryAccount = beneficiaryAccount;
            this.allocationAmount = allocationAmount;
            this.costCenter = costCenter;
        }
    }

    public static class SettlementBatch {
        public final String instructionId;
        public final String settlementRail;
        public final int batchSequence;
        public final String settlementStatus;
        public final java.sql.Timestamp settledAt;

        public SettlementBatch(
                String instructionId,
                String settlementRail,
                int batchSequence,
                String settlementStatus,
                java.sql.Timestamp settledAt) {
            this.instructionId = instructionId;
            this.settlementRail = settlementRail;
            this.batchSequence = batchSequence;
            this.settlementStatus = settlementStatus;
            this.settledAt = settledAt;
        }
    }
}
