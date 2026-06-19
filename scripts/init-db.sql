-- ============================================================
-- PossKassa — PostgreSQL boshlang'ich migratsiyasi
-- docker-compose da avtomatik ishga tushadi
-- ============================================================

-- Kengaytmalar
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Fuzzy qidirish uchun

-- ============================================================
-- TENANT
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    slug          VARCHAR(100) UNIQUE NOT NULL,
    legal_name    VARCHAR(255),
    inn           VARCHAR(20),
    ofd_token     TEXT,
    didox_token   TEXT,
    eimzo_cert    TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- USER
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id),
    keycloak_id   VARCHAR(255) UNIQUE NOT NULL,
    full_name     VARCHAR(255) NOT NULL,
    phone         VARCHAR(20),
    role          VARCHAR(20) NOT NULL DEFAULT 'cashier'
                  CHECK (role IN ('cashier','manager','admin','owner')),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

-- ============================================================
-- CATEGORY
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    parent_id   UUID REFERENCES categories(id),
    name        VARCHAR(255) NOT NULL,
    name_uz     VARCHAR(255),
    name_ru     VARCHAR(255),
    icon        VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PRODUCT
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id),
    category_id  UUID REFERENCES categories(id),
    name         VARCHAR(255) NOT NULL,
    name_uz      VARCHAR(255),
    name_ru      VARCHAR(255),
    sku          VARCHAR(100),
    barcode      VARCHAR(100),
    unit         VARCHAR(10) DEFAULT 'pcs',
    price        NUMERIC(15,2) NOT NULL DEFAULT 0,
    cost_price   NUMERIC(15,2) DEFAULT 0,
    vat_rate     NUMERIC(5,2)  DEFAULT 12,
    is_active    BOOLEAN DEFAULT TRUE,
    track_stock  BOOLEAN DEFAULT TRUE,
    image_url    TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode_tenant
    ON products(tenant_id, barcode) WHERE barcode IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_name_trgm
    ON products USING GIN (name gin_trgm_ops);

-- ============================================================
-- WAREHOUSE
-- ============================================================
CREATE TABLE IF NOT EXISTS warehouses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    name        VARCHAR(255) NOT NULL,
    address     TEXT,
    is_default  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- STOCK
-- ============================================================
CREATE TABLE IF NOT EXISTS stock (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID NOT NULL REFERENCES tenants(id),
    product_id           UUID NOT NULL REFERENCES products(id),
    warehouse_id         UUID NOT NULL REFERENCES warehouses(id),
    quantity             NUMERIC(15,3) DEFAULT 0,
    reserved_quantity    NUMERIC(15,3) DEFAULT 0,
    low_stock_threshold  NUMERIC(15,3) DEFAULT 5,
    updated_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, warehouse_id)
);

-- ============================================================
-- SHIFT (Smena)
-- ============================================================
CREATE TABLE IF NOT EXISTS shifts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id),
    cashier_id    UUID NOT NULL REFERENCES users(id),
    warehouse_id  UUID NOT NULL REFERENCES warehouses(id),
    opening_cash  NUMERIC(15,2) DEFAULT 0,
    closing_cash  NUMERIC(15,2),
    expected_cash NUMERIC(15,2),
    status        VARCHAR(10)  DEFAULT 'open',
    opened_at     TIMESTAMPTZ  DEFAULT NOW(),
    closed_at     TIMESTAMPTZ,
    notes         TEXT,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- ============================================================
-- CUSTOMER (Mijoz)
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    full_name       VARCHAR(255),
    phone           VARCHAR(20),
    loyalty_balance NUMERIC(15,2) DEFAULT 0,
    total_visits    INTEGER DEFAULT 0,
    total_spent     NUMERIC(15,2) DEFAULT 0,
    last_visit      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SALE (Sotuv)
-- ============================================================
CREATE TABLE IF NOT EXISTS sales (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    shift_id        UUID REFERENCES shifts(id),
    cashier_id      UUID NOT NULL REFERENCES users(id),
    customer_id     UUID REFERENCES customers(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    receipt_number  VARCHAR(50) NOT NULL,
    subtotal        NUMERIC(15,2) DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    vat_amount      NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL,
    status          VARCHAR(20) DEFAULT 'completed',
    sync_status     VARCHAR(10) DEFAULT 'pending',
    local_id        VARCHAR(100) UNIQUE,
    fiscal_sign     VARCHAR(255),
    fiscal_url      TEXT,
    sale_time       TIMESTAMPTZ DEFAULT NOW(),
    synced_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sales_tenant_time   ON sales(tenant_id, sale_time DESC);
CREATE INDEX IF NOT EXISTS idx_sales_sync_status   ON sales(tenant_id, sync_status);
CREATE INDEX IF NOT EXISTS idx_sales_cashier       ON sales(tenant_id, cashier_id);

-- ============================================================
-- SALE_ITEM
-- ============================================================
CREATE TABLE IF NOT EXISTS sale_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    sale_id         UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id),
    quantity        NUMERIC(15,3) NOT NULL,
    unit_price      NUMERIC(15,2) NOT NULL,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    vat_amount      NUMERIC(15,2) DEFAULT 0,
    total_price     NUMERIC(15,2) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale    ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);

-- ============================================================
-- PAYMENT (To'lov)
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id),
    sale_id           UUID NOT NULL REFERENCES sales(id),
    method            VARCHAR(20) NOT NULL,
    amount            NUMERIC(15,2) NOT NULL,
    transaction_id    VARCHAR(255),
    status            VARCHAR(20) DEFAULT 'completed',
    provider_response JSONB,
    paid_at           TIMESTAMPTZ DEFAULT NOW(),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- FISCAL_RECEIPT
-- ============================================================
CREATE TABLE IF NOT EXISTS fiscal_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    sale_id         UUID NOT NULL REFERENCES sales(id),
    fiscal_number   VARCHAR(100),
    fiscal_sign     VARCHAR(255),
    ofd_receipt_id  VARCHAR(100),
    receipt_url     TEXT,
    qr_url          TEXT,
    status          VARCHAR(20) DEFAULT 'pending',
    ofd_response    JSONB,
    sent_at         TIMESTAMPTZ,
    confirmed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sale_id)
);

-- ============================================================
-- RETURN (Qaytarish)
-- ============================================================
CREATE TABLE IF NOT EXISTS returns (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id),
    original_sale_id UUID NOT NULL REFERENCES sales(id),
    cashier_id       UUID NOT NULL REFERENCES users(id),
    reason           TEXT,
    refund_amount    NUMERIC(15,2) NOT NULL,
    refund_method    VARCHAR(20) DEFAULT 'cash',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SUPPLIER (Yetkazuvchi)
-- ============================================================
CREATE TABLE IF NOT EXISTS suppliers (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL REFERENCES tenants(id),
    name           VARCHAR(255) NOT NULL,
    inn            VARCHAR(20),
    phone          VARCHAR(20),
    email          VARCHAR(255),
    address        TEXT,
    column_mapping JSONB,
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INTAKE_DRAFT
-- ============================================================
CREATE TABLE IF NOT EXISTS intake_drafts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id),
    created_by        UUID NOT NULL REFERENCES users(id),
    source            VARCHAR(20) NOT NULL,
    original_file_url TEXT,
    raw_extracted     JSONB,
    normalized_rows   JSONB,
    review_result     JSONB,
    status            VARCHAR(30) DEFAULT 'extracting',
    supplier_id       UUID REFERENCES suppliers(id),
    warehouse_id      UUID,
    error_message     TEXT,
    reviewed_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- STOCK_RECEIPT (Kirim hujjati)
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_receipts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL REFERENCES tenants(id),
    supplier_id    UUID REFERENCES suppliers(id),
    warehouse_id   UUID NOT NULL,
    created_by     UUID NOT NULL REFERENCES users(id),
    receipt_number VARCHAR(50) NOT NULL,
    invoice_number VARCHAR(100),
    total_amount   NUMERIC(15,2) DEFAULT 0,
    total_cost     NUMERIC(15,2) DEFAULT 0,
    status         VARCHAR(20) DEFAULT 'confirmed',
    source         VARCHAR(20) DEFAULT 'manual',
    esf_number     VARCHAR(100),
    draft_id       UUID,
    receipt_date   TIMESTAMPTZ DEFAULT NOW(),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- STOCK_RECEIPT_ITEM
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_receipt_items (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id),
    receipt_id   UUID NOT NULL REFERENCES stock_receipts(id) ON DELETE CASCADE,
    product_id   UUID REFERENCES products(id),
    quantity     NUMERIC(15,3) NOT NULL,
    unit_cost    NUMERIC(15,2) NOT NULL,
    total_cost   NUMERIC(15,2) NOT NULL,
    vat_rate     NUMERIC(5,2) DEFAULT 12,
    batch_number VARCHAR(100),
    expiry_date  VARCHAR(20),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUDIT_LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL,
    user_id      UUID,
    entity_type  VARCHAR(100) NOT NULL,
    entity_id    UUID,
    action       VARCHAR(50)  NOT NULL,
    before_state JSONB,
    after_state  JSONB,
    ip_address   VARCHAR(45),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(tenant_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_time   ON audit_logs(tenant_id, created_at DESC);

-- ============================================================
-- RLS (Row Level Security) — har bir jadval uchun
-- ============================================================
DO $$
DECLARE tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'users','categories','products','warehouses','stock',
    'shifts','customers','sales','sale_items','payments',
    'fiscal_receipts','returns','suppliers','intake_drafts',
    'stock_receipts','stock_receipt_items'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format(
      'CREATE POLICY IF NOT EXISTS tenant_isolation_%I ON %I
       USING (tenant_id = current_setting(''app.tenant_id'', TRUE)::uuid)',
      tbl, tbl
    );
  END LOOP;
END $$;

-- ============================================================
-- Demo tenant va ma'lumotlar (dev muhiti)
-- ============================================================
INSERT INTO tenants (id, name, slug, legal_name, inn) VALUES
  ('00000000-0000-0000-0000-000000000001',
   'Demo Do''kon', 'demo', 'Demo Do''kon MCHJ', '123456789')
ON CONFLICT DO NOTHING;

INSERT INTO warehouses (id, tenant_id, name, is_default) VALUES
  ('00000000-0000-0000-0000-000000000010',
   '00000000-0000-0000-0000-000000000001', 'Asosiy ombor', TRUE)
ON CONFLICT DO NOTHING;
