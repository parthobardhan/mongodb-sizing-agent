# Data model: global-order-fulfillment

**Approval status:** pending

## 1. Use case summary

Multi-tenant B2B order fulfillment with a **75 ms** query SLA. Three dominant access patterns drive the design:

1. **Order detail (hot path #1):** Fetch a single order by `(org_id, order_number)` with all lines, current status, status history, tags, and open shipment summaries in **one round-trip**.
2. **Warehouse inventory (hot path #2):** Scan `(warehouse_id, sku)` for on-hand and reserved quantities **without loading order aggregates**.
3. **Customer portal (hot path #3):** List orders by `customer_id` sorted by `placed_at` descending, paginated at 25 per page.

Contract unit prices are frozen on order lines at placement time. Status history and shipment events are append-only audit streams; the UI shows the most recent events inline while compliance exports query the full stream. Returns reference original order lines but maintain an independent workflow state.

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| ORGANIZATION | separate_collection | `organizations` |
| CUSTOMER | anchor | `customers` |
| CUSTOMER_ADDRESS | embedded | `addresses[]` in `customers` |
| PRODUCT | anchor | `products` |
| PRODUCT_VARIANT | embedded | `variants[]` in `products` |
| PRODUCT_CATEGORY | separate_collection | `product_categories` |
| PRODUCT_CATEGORY_MAP | separate_collection | `product_category_map` |
| CUSTOMER_CONTRACT | anchor | `customer_contracts` |
| CONTRACT_PRICE_LINE | embedded | `priceLines[]` in `customer_contracts` |
| ORDER_HEADER | anchor | `orders` |
| ORDER_LINE | embedded | `lines[]` in `orders` |
| ORDER_STATUS_HISTORY | embedded | `statusHistory[]` in `orders` |
| ORDER_TAG_MAP | embedded | `tags[]` in `orders` |
| SHIPMENT | separate_collection | `shipments` |
| SHIPMENT (open subset) | embedded | `openShipments[]` in `orders` |
| SHIPMENT_PACKAGE | embedded | `packages[]` in `shipments` |
| SHIPMENT_EVENT | separate_collection | `shipment_events` |
| SHIPMENT_EVENT (recent subset) | embedded | `recentEvents[]` in `shipments` |
| INVENTORY_POSITION | separate_collection | `inventory_positions` |
| INVENTORY_RESERVATION | separate_collection | `inventory_reservations` |
| PAYMENT | separate_collection | `payments` |
| INVOICE | separate_collection | `invoices` |
| PROMOTION | anchor | `promotions` |
| PROMOTION_PRODUCT | embedded | `products[]` in `promotions` |
| ORDER_TAG | separate_collection | `order_tags` |
| RETURN_REQUEST | anchor | `return_requests` |
| RETURN_LINE | embedded | `lines[]` in `return_requests` |

## 3. Relational → MongoDB mapping

| Table / column | Collection / field |
|----------------|-------------------|
| ORGANIZATION.org_id | organizations.orgId |
| ORGANIZATION.org_code | organizations.orgCode |
| ORGANIZATION.org_name | organizations.orgName |
| ORGANIZATION.tier | organizations.tier |
| ORGANIZATION.created_at | organizations.createdAt |
| CUSTOMER.org_id | customers.orgId |
| CUSTOMER.customer_id | customers.customerId |
| CUSTOMER.customer_number | customers.customerNumber |
| CUSTOMER.legal_name | customers.legalName |
| CUSTOMER.credit_status | customers.creditStatus |
| CUSTOMER.primary_contact | customers.primaryContact |
| CUSTOMER.created_at | customers.createdAt |
| CUSTOMER_ADDRESS.address_id | customers.addresses[].addressId |
| CUSTOMER_ADDRESS.address_type | customers.addresses[].addressType |
| CUSTOMER_ADDRESS.line1 | customers.addresses[].line1 |
| CUSTOMER_ADDRESS.is_default | customers.addresses[].isDefault |
| PRODUCT.product_id | products.productId |
| PRODUCT.sku_root | products.skuRoot |
| PRODUCT.title | products.title |
| PRODUCT_VARIANT.variant_id | products.variants[].variantId |
| PRODUCT_VARIANT.sku | products.variants[].sku |
| PRODUCT_VARIANT.attributes_json | products.variants[].attributes |
| PRODUCT_CATEGORY.category_id | product_categories.categoryId |
| PRODUCT_CATEGORY.parent_category_id | product_categories.parentCategoryId |
| PRODUCT_CATEGORY_MAP.product_id | product_category_map.productId |
| PRODUCT_CATEGORY_MAP.category_id | product_category_map.categoryId |
| PRODUCT_CATEGORY_MAP.is_primary | product_category_map.isPrimary |
| CUSTOMER_CONTRACT.contract_id | customer_contracts.contractId |
| CUSTOMER_CONTRACT.customer_id | customer_contracts.customerId |
| CONTRACT_PRICE_LINE.price_line_id | customer_contracts.priceLines[].priceLineId |
| CONTRACT_PRICE_LINE.sku | customer_contracts.priceLines[].sku |
| CONTRACT_PRICE_LINE.unit_price | customer_contracts.priceLines[].unitPrice |
| ORDER_HEADER.order_id | orders.orderId |
| ORDER_HEADER.order_number | orders.orderNumber |
| ORDER_HEADER.customer_id | orders.customerId |
| ORDER_HEADER.order_status | orders.orderStatus |
| ORDER_HEADER.placed_at | orders.placedAt |
| ORDER_LINE.line_number | orders.lines[].lineNumber |
| ORDER_LINE.sku | orders.lines[].sku |
| ORDER_LINE.unit_price | orders.lines[].unitPrice |
| ORDER_STATUS_HISTORY.seq | orders.statusHistory[].seq |
| ORDER_STATUS_HISTORY.to_status | orders.statusHistory[].toStatus |
| ORDER_STATUS_HISTORY.changed_at | orders.statusHistory[].changedAt |
| ORDER_TAG_MAP.tag_id | orders.tags[].tagId |
| ORDER_TAG_MAP.tagged_at | orders.tags[].taggedAt |
| SHIPMENT.shipment_id | shipments.shipmentId |
| SHIPMENT.order_id | shipments.orderId |
| SHIPMENT.shipment_status | shipments.shipmentStatus |
| SHIPMENT (open summary) | orders.openShipments[].shipmentId |
| SHIPMENT_PACKAGE.package_number | shipments.packages[].packageNumber |
| SHIPMENT_EVENT.event_seq | shipment_events.eventSeq |
| SHIPMENT_EVENT.event_type | shipment_events.eventType |
| SHIPMENT_EVENT (recent) | shipments.recentEvents[].eventSeq |
| INVENTORY_POSITION.warehouse_id | inventory_positions.warehouseId |
| INVENTORY_POSITION.sku | inventory_positions.sku |
| INVENTORY_POSITION.on_hand_qty | inventory_positions.onHandQty |
| INVENTORY_POSITION.reserved_qty | inventory_positions.reservedQty |
| INVENTORY_RESERVATION.reservation_id | inventory_reservations.reservationId |
| INVENTORY_RESERVATION.order_id | inventory_reservations.orderId |
| PAYMENT.payment_id | payments.paymentId |
| PAYMENT.order_id | payments.orderId |
| INVOICE.invoice_id | invoices.invoiceId |
| INVOICE.invoice_number | invoices.invoiceNumber |
| PROMOTION.promotion_id | promotions.promotionId |
| PROMOTION.promo_code | promotions.promoCode |
| PROMOTION_PRODUCT.sku | promotions.products[].sku |
| ORDER_TAG.tag_id | order_tags.tagId |
| ORDER_TAG.tag_code | order_tags.tagCode |
| RETURN_REQUEST.return_id | return_requests.returnId |
| RETURN_REQUEST.order_id | return_requests.orderId |
| RETURN_LINE.line_number | return_requests.lines[].lineNumber |

## 4. Collections (sample documents)

Database: `sizing_global_order_fulfillment`

**orders** — embeds lines (~4.4), statusHistory (~4), tags (~2), openShipments (~1).

```json
{
  "orgId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "orderId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "orderNumber": "ORD-2026-0048217",
  "customerId": "c0ffee00-0000-4000-8000-000000000001",
  "contractId": "b3d4e5f6-7890-1234-abcd-ef1234567891",
  "shipToAddressId": "addr-ship-001",
  "billToAddressId": "addr-bill-001",
  "currencyCode": "USD",
  "orderStatus": "PARTIALLY_SHIPPED",
  "placedAt": "2026-07-15T14:22:00Z",
  "promisedShipBy": "2026-07-18T23:59:59Z",
  "orderTotal": 4825.60,
  "lines": [
    {
      "lineNumber": 1,
      "sku": "SKU-WIDGET-42-RED",
      "productId": "p001",
      "variantId": "v001",
      "qtyOrdered": 10,
      "unitPrice": 125.5000,
      "lineStatus": "SHIPPED"
  }
  ],
  "statusHistory": [
    {
      "seq": 3,
      "fromStatus": "PICKING",
      "toStatus": "PARTIALLY_SHIPPED",
      "changedAt": "2026-07-16T09:15:00Z",
      "changedBy": "warehouse-bot",
      "reasonCode": null
    }
  ],
  "tags": [
    { "tagId": "tag-rush", "taggedAt": "2026-07-15T14:22:05Z" }
  ],
  "openShipments": [
    {
      "shipmentId": "shp-00042",
      "warehouseId": "wh-west-01",
      "carrierCode": "FEDX",
      "trackingNumber": "794612345678",
      "shipmentStatus": "IN_TRANSIT"
    }
  ]
}
```

**inventory_positions** — isolated from order aggregates (hot path #2).

```json
{
  "orgId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "warehouseId": "wh-west-01",
  "sku": "SKU-WIDGET-42-RED",
  "onHandQty": 240,
  "reservedQty": 18,
  "lastCountedAt": "2026-07-14T06:00:00Z"
}
```

**shipments** — packages embedded (~2.7); last 5 events in `recentEvents[]`; full stream in `shipment_events`.

```json
{
  "orgId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "shipmentId": "shp-00042",
  "orderId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "warehouseId": "wh-west-01",
  "carrierCode": "FEDX",
  "trackingNumber": "794612345678",
  "shipmentStatus": "IN_TRANSIT",
  "shippedAt": "2026-07-16T08:30:00Z",
  "packages": [
    { "packageNumber": 1, "weightGrams": 1250, "labelBarcode": "PKG-00042-01" }
  ],
  "recentEvents": [
    {
      "eventSeq": 12,
      "eventType": "IN_TRANSIT",
      "eventAt": "2026-07-17T11:00:00Z",
      "locationCode": "DEN-HUB"
    }
  ]
}
```

**customer_contracts** — price lines embedded (~40) for placement-time SKU lookup.

```json
{
  "orgId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "contractId": "b3d4e5f6-7890-1234-abcd-ef1234567891",
  "customerId": "c0ffee00-0000-4000-8000-000000000001",
  "contractNumber": "CTR-2026-0088",
  "currencyCode": "USD",
  "validFrom": "2026-01-01",
  "validTo": "2026-12-31",
  "status": "ACTIVE",
  "priceLines": [
    { "priceLineId": "pl-001", "sku": "SKU-WIDGET-42-RED", "unitPrice": 125.5000, "minQty": 1 }
  ]
}
```

## 5. Embedding vs referencing

- **Embed order lines, status history, and tags in `orders`:** Hot path #1 requires a single `findOne` on `(orgId, orderNumber)` returning the full order aggregate. Lines (~4.4 avg), status history (~4 avg), and tags (~2 avg) are always co-read with the parent and are bounded per order.
- **Embed `openShipments[]` summaries in `orders`:** Satisfies hot path #1 without a second query. Full shipment documents (with packages) remain in `shipments` for warehouse and tracking workflows.
- **Separate `inventory_positions`:** Hot path #2 explicitly must not load order aggregates. Inventory is high-churn and warehouse-scoped; it lives in its own collection with a unique compound on `(orgId, warehouseId, sku)`.
- **Separate `shipment_events` with `recentEvents[]` on `shipments`:** Average ~12 events per shipment exceeds the UI's inline display of 5, but compliance exports need the full append-only stream. Recent events are denormalized into the shipment document; the full history is queryable from `shipment_events` by `(orgId, shipmentId)`.
- **Embed addresses in `customers`, variants in `products`, price lines in `customer_contracts`:** Cardinalities are bounded (3.25, 3.35, and 40 respectively) and these children are co-accessed with their parent on typical read paths.
- **Separate `payments`, `invoices`, `inventory_reservations`:** Referenced by `orderId` but have independent lifecycles, statuses, and query paths; embedding would bloat order documents without serving hot path #1.
- **Separate `product_category_map`:** M:N join table (74M rows) supports category-tree catalog browse via `(orgId, categoryId)` and product-centric lookups via `(orgId, productId)`.

## 6. Sizing inputs summary

- Database production document count: **13,328,764,200**
- Top-level collections: 16 (see `sizing_inputs.json`)
- Key embedded cardinalities (derived from `intake.json` `productionRowCounts`):
  - CUSTOMER_ADDRESS → customers.addresses[]: **3.25** (9,100,000 / 2,800,000)
  - PRODUCT_VARIANT → products.variants[]: **3.35** (62,000,000 / 18,500,000)
  - CONTRACT_PRICE_LINE → customer_contracts.priceLines[]: **40** (48,000,000 / 1,200,000)
  - ORDER_LINE → orders.lines[]: **4.42** (4,200,000,000 / 950,000,000)
  - ORDER_STATUS_HISTORY → orders.statusHistory[]: **4** (3,800,000,000 / 950,000,000)
  - ORDER_TAG_MAP → orders.tags[]: **2** (1,900,000,000 / 950,000,000)
  - SHIPMENT (open summaries) → orders.openShipments[]: **1** (780,000,000 / 950,000,000, rounded; non-terminal subset at read time)
  - SHIPMENT_PACKAGE → shipments.packages[]: **2.69** (2,100,000,000 / 780,000,000)
  - SHIPMENT_EVENT (recent) → shipments.recentEvents[]: **5** (UI cap; full stream in `shipment_events`)
  - PROMOTION_PRODUCT → promotions.products[]: **13.33** (2,400,000 / 180,000)
  - RETURN_LINE → return_requests.lines[]: **2.33** (98,000,000 / 42,000,000)

## 7. Index strategy

| Collection | Index | Legacy source | Query path |
|------------|-------|---------------|------------|
| `customers` | `{ orgId: 1, customerNumber: 1 }` | `idx_customer_org_number` | Customer lookup by number |
| `customers` | `{ orgId: 1, createdAt: -1 }` | `idx_customer_org_created` | Org customer listing |
| `products` | `{ orgId: 1, skuRoot: 1 }` | `idx_product_org_sku_root` | Product by root SKU |
| `products` | `{ orgId: 1, isActive: 1, createdAt: -1 }` | `idx_product_org_active` | Active catalog browse |
| `products` | `{ orgId: 1, "variants.sku": 1 }` unique | `idx_variant_org_sku` | Variant SKU resolution |
| `product_categories` | `{ orgId: 1, parentCategoryId: 1 }` | `idx_category_parent` | Category tree traversal |
| `product_category_map` | `{ orgId: 1, categoryId: 1, productId: 1 }` | `idx_category_map_category` | Products in category |
| `product_category_map` | `{ orgId: 1, productId: 1, categoryId: 1 }` | `idx_category_map_product` | Categories for product |
| `customer_contracts` | `{ orgId: 1, customerId: 1, status: 1 }` | `idx_contract_customer` | Active contracts per customer |
| `customer_contracts` | `{ orgId: 1, contractId: 1, "priceLines.sku": 1 }` | `idx_price_contract_sku` | Contract price at placement |
| `orders` | `{ orgId: 1, orderNumber: 1 }` unique | `idx_order_org_number` | Hot path #1 order detail |
| `orders` | `{ orgId: 1, customerId: 1, placedAt: -1 }` | `idx_order_customer_placed` | Hot path #3 portal listing |
| `orders` | `{ orgId: 1, orderStatus: 1, placedAt: -1 }` | `idx_order_status_placed` | Ops queue by status |
| `orders` | `{ orgId: 1, "lines.sku": 1 }` | `idx_order_line_sku` | SKU-in-order analytics |
| `shipments` | `{ orgId: 1, orderId: 1, shipmentStatus: 1 }` | `idx_shipment_order` | Shipments for order (non-hot-path) |
| `shipments` | `{ orgId: 1, trackingNumber: 1 }` | `idx_shipment_tracking` | Carrier tracking lookup |
| `shipment_events` | `{ orgId: 1, shipmentId: 1, eventSeq: -1 }` | `idx_shipment_event_seq` | Compliance export / full audit |
| `inventory_positions` | `{ orgId: 1, warehouseId: 1, sku: 1 }` unique | `idx_inventory_wh_sku` | Hot path #2 warehouse scan |
| `inventory_reservations` | `{ orgId: 1, orderId: 1, orderLineNumber: 1 }` | `idx_reservation_order_line` | Reservation by order line |
| `inventory_reservations` | `{ orgId: 1, warehouseId: 1, sku: 1, releasedAt: 1 }` | `idx_reservation_wh_sku_open` | Open reservations by SKU |
| `payments` | `{ orgId: 1, orderId: 1, paymentStatus: 1 }` | `idx_payment_order` | Payments for order |
| `invoices` | `{ orgId: 1, orderId: 1 }` | `idx_invoice_order` | Invoices for order |
| `invoices` | `{ orgId: 1, invoiceNumber: 1 }` unique | `idx_invoice_number` | Invoice number lookup |
| `promotions` | `{ orgId: 1, promoCode: 1 }` unique | PK `PROMOTION` | Promo code redemption |
| `promotions` | `{ orgId: 1, "products.sku": 1, promotionId: 1 }` | `idx_promo_product_sku` | Promotions for SKU |
| `order_tags` | `{ orgId: 1, tagCode: 1 }` unique | PK `ORDER_TAG` | Tag definition lookup |
| `return_requests` | `{ orgId: 1, orderId: 1, returnStatus: 1 }` | `idx_return_order` | Returns for order |

**Prefix coverage notes:**

- No index on embedded `customers.addresses[]`; parent `(orgId, customerId)` PK lookup covers `idx_address_customer`.
- No index on embedded `orders.lines[]` for `(orgId, orderId, lineNumber)`; lines are retrieved with the parent order document.
- No index on embedded `shipments.packages[]`; package access is via parent shipment lookup (`idx_package_shipment` subsumed).
- `idx_order_tag_map_order` and `idx_order_tag_map_tag` are subsumed by embedded tags in orders (order-centric) and `order_tags` collection (tag-centric definition lookup).
- `idx_return_line_return` subsumed by embedded lines in `return_requests`.
- Compound indexes on `product_category_map` use different field order for distinct access paths; neither is a prefix of the other.
- `organizations` has no relational secondary indexes; collection size is 4,200 documents.

## 8. Rationale

The model optimizes for three competing constraints: sub-75 ms order detail reads, isolated warehouse inventory scans, and paginated customer order history. Order aggregates (lines, status, tags, open shipment summaries) are embedded to satisfy hot path #1 in a single query. Inventory and reservations remain separate to honor hot path #2's isolation requirement and to support high-churn warehouse updates without touching order documents.

Shipment events split into a denormalized `recentEvents[]` slice (5 events for UI) and a full `shipment_events` collection (9.6B rows) for compliance exports — avoiding 12+ embedded events per shipment in the hot shipment document while keeping the UI path efficient.

Catalog and contract data use bounded embedding (variants, price lines, addresses) where parent-child co-read is typical, while M:N category mapping and financial documents (payments, invoices) stay in separate collections with tenant-scoped compound indexes mirroring the relational access paths.

## 9. Assumptions

- `orgId` is included as a leading field on all compound indexes for tenant isolation, matching the relational `(org_id, …)` pattern.
- `openShipments[]` embeds only non-terminal shipment summaries; avg cardinality **1** is derived from total shipment-to-order ratio (780M / 950M ≈ 0.82, rounded up for sizing headroom).
- `recentEvents[]` caps at **5** events per shipment per UI requirement; full history cardinality (~12.3 per shipment) is modeled in `shipment_events`.
- Contract price lines are embedded (avg 40 per contract); contracts with exceptionally large price schedules may require a future bucketed or referenced layout — not indicated in intake.
- Payments (~0.65 per order) and invoices (~0.61 per order) are referenced collections, not embedded, because they are not required for hot path #1 and have independent status lifecycles.
- Natural keys (`orderNumber`, `customerNumber`, `sku`, etc.) are stored as fields with unique/compound indexes rather than as MongoDB `_id`, preserving parity with relational access patterns.
- `attributes_json` and `payload_json` TEXT columns map to BSON subdocuments/objects in sample documents.

## 10. Approval

- Status: **pending**
- Approved at: —
