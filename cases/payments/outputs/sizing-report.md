# MongoDB Sizing Report

## Sample database stats (dbStats)

- Objects (sample): **1000**
- Avg object size: **368.90 B**
- Data size: **360.26 KB**
- Storage size: **120.00 KB**
- Index size: **152.00 KB**

## Per-collection (collStats → production scale)

| Collection | Sample count | Prod docs | Data (prod) | Index (prod) |
|------------|--------------|-----------|-------------|--------------|
| payment_instruction | 500 | 15000000 | 8.19 GB | 2.52 GB |
| settlement_batch | 500 | 6000000 | 865.40 MB | 750.00 MB |

## Atlas sizing (from dbStats scaling)

- Production document count (database): **21000000**
- Compression ratio: **0.6669**
- Sizing basis: **measured-storage**
- Data size (production): **7.21 GB**
- Storage size (production): **2.40 GB**
- Index size (production): **3.04 GB**
- RAM usage estimate (index × 1.5): **4.57 GB**
- **Disk required** (storage / 0.75): **3.20 GB**
- **RAM required**: **4.57 GB**

_Per-collection rows are for detail; Disk/RAM above use database-level dbStats only._
