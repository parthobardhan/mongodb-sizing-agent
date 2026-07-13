-- Multi-tenant B2B order fulfillment (complex relational intake)

CREATE TABLE ORGANIZATION (
  org_id            CHAR(36)      NOT NULL PRIMARY KEY,
  org_code          VARCHAR(16)   NOT NULL UNIQUE,
  org_name          VARCHAR(200)  NOT NULL,
  tier              VARCHAR(20)   NOT NULL,
  created_at        TIMESTAMP     NOT NULL
);

CREATE TABLE CUSTOMER (
  org_id            CHAR(36)      NOT NULL,
  customer_id       CHAR(36)      NOT NULL,
  customer_number   VARCHAR(24)   NOT NULL,
  legal_name        VARCHAR(300)  NOT NULL,
  credit_status     CHAR(1)       NOT NULL,
  primary_contact   VARCHAR(200),
  created_at        TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, customer_id),
  UNIQUE (org_id, customer_number)
);

CREATE TABLE CUSTOMER_ADDRESS (
  org_id            CHAR(36)      NOT NULL,
  customer_id       CHAR(36)      NOT NULL,
  address_id        CHAR(36)      NOT NULL,
  address_type      VARCHAR(20)   NOT NULL,
  line1             VARCHAR(200)  NOT NULL,
  line2             VARCHAR(200),
  city              VARCHAR(100)  NOT NULL,
  region            VARCHAR(50),
  postal_code       VARCHAR(20)   NOT NULL,
  country_code      CHAR(2)       NOT NULL,
  is_default        BOOLEAN       NOT NULL DEFAULT FALSE,
  PRIMARY KEY (org_id, customer_id, address_id)
);

CREATE TABLE PRODUCT (
  org_id            CHAR(36)      NOT NULL,
  product_id        CHAR(36)      NOT NULL,
  sku_root          VARCHAR(40)   NOT NULL,
  title             VARCHAR(500)  NOT NULL,
  brand             VARCHAR(100),
  is_active         BOOLEAN       NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, product_id),
  UNIQUE (org_id, sku_root)
);

CREATE TABLE PRODUCT_VARIANT (
  org_id            CHAR(36)      NOT NULL,
  product_id        CHAR(36)      NOT NULL,
  variant_id        CHAR(36)      NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  attributes_json   TEXT          NOT NULL,
  weight_grams      INT,
  PRIMARY KEY (org_id, product_id, variant_id),
  UNIQUE (org_id, sku)
);

CREATE TABLE PRODUCT_CATEGORY (
  org_id            CHAR(36)      NOT NULL,
  category_id       CHAR(36)      NOT NULL,
  parent_category_id CHAR(36),
  category_code     VARCHAR(40)   NOT NULL,
  category_name     VARCHAR(200)  NOT NULL,
  PRIMARY KEY (org_id, category_id),
  UNIQUE (org_id, category_code)
);

CREATE TABLE PRODUCT_CATEGORY_MAP (
  org_id            CHAR(36)      NOT NULL,
  product_id        CHAR(36)      NOT NULL,
  category_id       CHAR(36)      NOT NULL,
  is_primary        BOOLEAN       NOT NULL DEFAULT FALSE,
  PRIMARY KEY (org_id, product_id, category_id)
);

CREATE TABLE CUSTOMER_CONTRACT (
  org_id            CHAR(36)      NOT NULL,
  contract_id       CHAR(36)      NOT NULL,
  customer_id       CHAR(36)      NOT NULL,
  contract_number   VARCHAR(30)   NOT NULL,
  currency_code     CHAR(3)       NOT NULL,
  valid_from        DATE          NOT NULL,
  valid_to          DATE,
  status            VARCHAR(20)   NOT NULL,
  PRIMARY KEY (org_id, contract_id),
  UNIQUE (org_id, contract_number)
);

CREATE TABLE CONTRACT_PRICE_LINE (
  org_id            CHAR(36)      NOT NULL,
  contract_id       CHAR(36)      NOT NULL,
  price_line_id     CHAR(36)      NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  unit_price        DECIMAL(14,4) NOT NULL,
  min_qty           INT           NOT NULL DEFAULT 1,
  PRIMARY KEY (org_id, contract_id, price_line_id)
);

CREATE TABLE ORDER_HEADER (
  org_id            CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  order_number      VARCHAR(30)   NOT NULL,
  customer_id       CHAR(36)      NOT NULL,
  contract_id       CHAR(36),
  ship_to_address_id CHAR(36)     NOT NULL,
  bill_to_address_id CHAR(36)     NOT NULL,
  currency_code     CHAR(3)       NOT NULL,
  order_status      VARCHAR(30)   NOT NULL,
  placed_at         TIMESTAMP     NOT NULL,
  promised_ship_by  TIMESTAMP,
  order_total       DECIMAL(16,2) NOT NULL,
  PRIMARY KEY (org_id, order_id),
  UNIQUE (org_id, order_number)
);

CREATE TABLE ORDER_LINE (
  org_id            CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  line_number       INT           NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  product_id        CHAR(36)      NOT NULL,
  variant_id        CHAR(36)      NOT NULL,
  qty_ordered       INT           NOT NULL,
  unit_price        DECIMAL(14,4) NOT NULL,
  line_status       VARCHAR(20)   NOT NULL,
  PRIMARY KEY (org_id, order_id, line_number)
);

CREATE TABLE ORDER_STATUS_HISTORY (
  org_id            CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  seq               BIGINT        NOT NULL,
  from_status       VARCHAR(30),
  to_status         VARCHAR(30)   NOT NULL,
  changed_at        TIMESTAMP     NOT NULL,
  changed_by        VARCHAR(100)  NOT NULL,
  reason_code       VARCHAR(40),
  PRIMARY KEY (org_id, order_id, seq)
);

CREATE TABLE SHIPMENT (
  org_id            CHAR(36)      NOT NULL,
  shipment_id       CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  warehouse_id      CHAR(36)      NOT NULL,
  carrier_code      VARCHAR(20)   NOT NULL,
  tracking_number   VARCHAR(64),
  shipment_status   VARCHAR(30)   NOT NULL,
  shipped_at        TIMESTAMP,
  PRIMARY KEY (org_id, shipment_id)
);

CREATE TABLE SHIPMENT_PACKAGE (
  org_id            CHAR(36)      NOT NULL,
  shipment_id       CHAR(36)      NOT NULL,
  package_number    INT           NOT NULL,
  weight_grams      INT,
  label_barcode     VARCHAR(64),
  PRIMARY KEY (org_id, shipment_id, package_number)
);

CREATE TABLE SHIPMENT_EVENT (
  org_id            CHAR(36)      NOT NULL,
  shipment_id       CHAR(36)      NOT NULL,
  event_seq         BIGINT        NOT NULL,
  event_type        VARCHAR(40)   NOT NULL,
  event_at          TIMESTAMP     NOT NULL,
  location_code     VARCHAR(40),
  payload_json      TEXT,
  PRIMARY KEY (org_id, shipment_id, event_seq)
);

CREATE TABLE INVENTORY_POSITION (
  org_id            CHAR(36)      NOT NULL,
  warehouse_id      CHAR(36)      NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  on_hand_qty       INT           NOT NULL,
  reserved_qty      INT           NOT NULL,
  last_counted_at   TIMESTAMP,
  PRIMARY KEY (org_id, warehouse_id, sku)
);

CREATE TABLE INVENTORY_RESERVATION (
  org_id            CHAR(36)      NOT NULL,
  reservation_id    CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  order_line_number INT           NOT NULL,
  warehouse_id      CHAR(36)      NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  qty_reserved      INT           NOT NULL,
  reserved_at       TIMESTAMP     NOT NULL,
  released_at       TIMESTAMP,
  PRIMARY KEY (org_id, reservation_id)
);

CREATE TABLE PAYMENT (
  org_id            CHAR(36)      NOT NULL,
  payment_id        CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  payment_method    VARCHAR(30)   NOT NULL,
  amount            DECIMAL(16,2) NOT NULL,
  currency_code     CHAR(3)       NOT NULL,
  payment_status    VARCHAR(20)   NOT NULL,
  captured_at       TIMESTAMP,
  PRIMARY KEY (org_id, payment_id)
);

CREATE TABLE INVOICE (
  org_id            CHAR(36)      NOT NULL,
  invoice_id        CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  invoice_number    VARCHAR(30)   NOT NULL,
  invoice_total     DECIMAL(16,2) NOT NULL,
  issued_at         TIMESTAMP     NOT NULL,
  due_at            TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, invoice_id),
  UNIQUE (org_id, invoice_number)
);

CREATE TABLE PROMOTION (
  org_id            CHAR(36)      NOT NULL,
  promotion_id      CHAR(36)      NOT NULL,
  promo_code        VARCHAR(40)   NOT NULL,
  discount_type     VARCHAR(20)   NOT NULL,
  discount_value    DECIMAL(12,4) NOT NULL,
  starts_at         TIMESTAMP     NOT NULL,
  ends_at           TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, promotion_id),
  UNIQUE (org_id, promo_code)
);

CREATE TABLE PROMOTION_PRODUCT (
  org_id            CHAR(36)      NOT NULL,
  promotion_id      CHAR(36)      NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  PRIMARY KEY (org_id, promotion_id, sku)
);

CREATE TABLE ORDER_TAG (
  org_id            CHAR(36)      NOT NULL,
  tag_id            CHAR(36)      NOT NULL,
  tag_code          VARCHAR(40)   NOT NULL,
  tag_label         VARCHAR(100)  NOT NULL,
  PRIMARY KEY (org_id, tag_id),
  UNIQUE (org_id, tag_code)
);

CREATE TABLE ORDER_TAG_MAP (
  org_id            CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  tag_id            CHAR(36)      NOT NULL,
  tagged_at         TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, order_id, tag_id)
);

CREATE TABLE RETURN_REQUEST (
  org_id            CHAR(36)      NOT NULL,
  return_id         CHAR(36)      NOT NULL,
  order_id          CHAR(36)      NOT NULL,
  return_number     VARCHAR(30)   NOT NULL,
  return_status     VARCHAR(30)   NOT NULL,
  opened_at         TIMESTAMP     NOT NULL,
  PRIMARY KEY (org_id, return_id),
  UNIQUE (org_id, return_number)
);

CREATE TABLE RETURN_LINE (
  org_id            CHAR(36)      NOT NULL,
  return_id         CHAR(36)      NOT NULL,
  line_number       INT           NOT NULL,
  order_line_number INT           NOT NULL,
  sku               VARCHAR(48)   NOT NULL,
  qty_returned      INT           NOT NULL,
  reason_code       VARCHAR(40)   NOT NULL,
  PRIMARY KEY (org_id, return_id, line_number)
);
