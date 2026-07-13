-- Tenant-scoped access paths

CREATE INDEX idx_customer_org_number ON CUSTOMER (org_id, customer_number);
CREATE INDEX idx_customer_org_created ON CUSTOMER (org_id, created_at);

CREATE INDEX idx_address_customer ON CUSTOMER_ADDRESS (org_id, customer_id, is_default);

CREATE INDEX idx_product_org_sku_root ON PRODUCT (org_id, sku_root);
CREATE INDEX idx_product_org_active ON PRODUCT (org_id, is_active, created_at);

CREATE UNIQUE INDEX idx_variant_org_sku ON PRODUCT_VARIANT (org_id, sku);
CREATE INDEX idx_variant_product ON PRODUCT_VARIANT (org_id, product_id);

CREATE INDEX idx_category_parent ON PRODUCT_CATEGORY (org_id, parent_category_id);
CREATE INDEX idx_category_map_category ON PRODUCT_CATEGORY_MAP (org_id, category_id, product_id);
CREATE INDEX idx_category_map_product ON PRODUCT_CATEGORY_MAP (org_id, product_id, category_id);

CREATE INDEX idx_contract_customer ON CUSTOMER_CONTRACT (org_id, customer_id, status);
CREATE INDEX idx_price_contract_sku ON CONTRACT_PRICE_LINE (org_id, contract_id, sku);

-- Order hot paths
CREATE UNIQUE INDEX idx_order_org_number ON ORDER_HEADER (org_id, order_number);
CREATE INDEX idx_order_customer_placed ON ORDER_HEADER (org_id, customer_id, placed_at DESC);
CREATE INDEX idx_order_status_placed ON ORDER_HEADER (org_id, order_status, placed_at DESC);

CREATE INDEX idx_order_line_order ON ORDER_LINE (org_id, order_id, line_number);
CREATE INDEX idx_order_line_sku ON ORDER_LINE (org_id, sku);

CREATE INDEX idx_order_history_order_seq ON ORDER_STATUS_HISTORY (org_id, order_id, seq DESC);

CREATE INDEX idx_shipment_order ON SHIPMENT (org_id, order_id, shipment_status);
CREATE INDEX idx_shipment_tracking ON SHIPMENT (org_id, tracking_number);

CREATE INDEX idx_package_shipment ON SHIPMENT_PACKAGE (org_id, shipment_id, package_number);
CREATE INDEX idx_shipment_event_seq ON SHIPMENT_EVENT (org_id, shipment_id, event_seq DESC);

-- Inventory (high churn, warehouse-local)
CREATE UNIQUE INDEX idx_inventory_wh_sku ON INVENTORY_POSITION (org_id, warehouse_id, sku);
CREATE INDEX idx_reservation_order_line ON INVENTORY_RESERVATION (org_id, order_id, order_line_number);
CREATE INDEX idx_reservation_wh_sku_open ON INVENTORY_RESERVATION (org_id, warehouse_id, sku, released_at);

CREATE INDEX idx_payment_order ON PAYMENT (org_id, order_id, payment_status);
CREATE INDEX idx_invoice_order ON INVOICE (org_id, order_id);
CREATE UNIQUE INDEX idx_invoice_number ON INVOICE (org_id, invoice_number);

CREATE INDEX idx_promo_product_sku ON PROMOTION_PRODUCT (org_id, sku, promotion_id);
CREATE INDEX idx_order_tag_map_order ON ORDER_TAG_MAP (org_id, order_id, tag_id);
CREATE INDEX idx_order_tag_map_tag ON ORDER_TAG_MAP (org_id, tag_id, order_id);

CREATE INDEX idx_return_order ON RETURN_REQUEST (org_id, order_id, return_status);
CREATE INDEX idx_return_line_return ON RETURN_LINE (org_id, return_id, line_number);
