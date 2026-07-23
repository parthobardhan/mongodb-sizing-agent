# MongoDB Sizing Report

## Sample database stats (dbStats)

- Objects (sample): **1000**
- Avg object size: **355.54 B**
- Data size: **347.20 KB**
- Storage size: **116.00 KB**
- Index size: **152.00 KB**

## Per-collection (collStats → production scale)

| Collection | Sample count | Prod docs | Data (prod) | Index (prod) |
|------------|--------------|-----------|-------------|--------------|
| payment_instruction | 500 | 15000000 | 7.81 GB | 2.52 GB |
| settlement_batch | 500 | 6000000 | 869.75 MB | 750.00 MB |

## Atlas sizing (from dbStats scaling)

- Production document count (database): **21000000**
- Compression ratio: **0.6659**
- Sizing basis: **measured-storage**
- Data size (production): **6.95 GB**
- Storage size (production): **2.32 GB**
- Index size (production): **3.04 GB**
- RAM usage estimate (index × 1.5): **4.57 GB**
- **Disk required** (storage / 0.75): **3.10 GB**
- **RAM required**: **4.57 GB**

_Per-collection rows are for detail; Disk/RAM above use database-level dbStats only._
