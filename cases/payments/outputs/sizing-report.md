# MongoDB Sizing Report

## Sample database stats (dbStats)

- Objects (sample): **1000**
- Avg object size: **364.62 B**
- Data size: **356.07 KB**
- Storage size: **140.00 KB**
- Index size: **188.00 KB**

## Per-collection (collStats → production scale)

| Collection | Sample count | Prod docs | Data (prod) | Index (prod) |
|------------|--------------|-----------|-------------|--------------|
| payment_instructions | 500 | 15000000 | 7.90 GB | 2.98 GB |
| settlement_batches | 500 | 6000000 | 936.96 MB | 984.38 MB |

## Atlas sizing (from dbStats scaling)

- Production document count (database): **21000000**
- Compression ratio: **0.6068**
- Sizing basis: **measured-storage**
- Data size (production): **7.13 GB**
- Storage size (production): **2.80 GB**
- Index size (production): **3.77 GB**
- RAM usage estimate (index × 1.5): **5.65 GB**
- **Disk required** (storage / 0.75): **3.74 GB**
- **RAM required**: **5.65 GB**

_Per-collection rows are for detail; Disk/RAM above use database-level dbStats only._
