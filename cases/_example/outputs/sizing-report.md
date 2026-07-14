# MongoDB Sizing Report

## Sample database stats (dbStats)

- Objects (sample): **1000**
- Avg object size: **298.68 B**
- Data size: **291.68 KB**
- Storage size: **92.00 KB**
- Index size: **88.00 KB**

## Per-collection (collStats → production scale)

| Collection | Sample count | Prod docs | Data (prod) | Index (prod) |
|------------|--------------|-----------|-------------|--------------|
| client_release_table | 500 | 8000000 | 877.38 MB | 687.50 MB |
| client_document_history | 500 | 12000000 | 5.39 GB | 1.01 GB |

## Atlas sizing (from dbStats scaling)

- Production document count (database): **20000000**
- Compression ratio: **0.6846**
- Sizing basis: **measured-storage**
- Data size (production): **5.56 GB**
- Storage size (production): **1.75 GB**
- Index size (production): **1.68 GB**
- RAM usage estimate (index × 1.5): **2.52 GB**
- **Disk required** (storage / 0.75): **2.34 GB**
- **RAM required**: **2.52 GB**

_Per-collection rows are for detail; Disk/RAM above use database-level dbStats only._
