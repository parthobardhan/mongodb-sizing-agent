# Data model: {{useCaseName}}

**Approval status:** {{approvalStatus}}

## 1. Use case summary

{{summary}}

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
{{dispositionRows}}

## 3. Relational → MongoDB mapping

{{mappingTable}}

## 4. Collections (sample documents)

{{collectionSamples}}

## 5. Embedding vs referencing

{{embeddingDecisions}}

## 6. Sizing inputs summary

- Database production document count: **{{databaseProductionDocumentCount}}**
{{sizingInputsSummary}}

## 7. Index strategy

{{indexStrategy}}

## 8. Rationale

{{rationale}}

## 9. Assumptions

{{assumptions}}

## 10. Approval

- Status: **{{approvalStatus}}**
- Approved at: {{approvedAt}}
