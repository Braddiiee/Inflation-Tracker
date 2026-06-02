-- Local Grocery Inflation Tracker — reference schema (3NF)
-- Applied automatically via SQLAlchemy models in src/models.py (init_db).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS stores (
    store_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE,
    category_id  INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS price_logs (
    log_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL,
    store_id       INTEGER NOT NULL,
    price_total    REAL NOT NULL CHECK (price_total > 0),
    quantity       REAL NOT NULL CHECK (quantity > 0),
    unit_type      TEXT NOT NULL CHECK (unit_type IN ('kg', 'g', 'l', 'ml', 'unit')),
    date_recorded  TEXT NOT NULL,
    notes          TEXT,
    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE RESTRICT,
    FOREIGN KEY (store_id) REFERENCES stores (store_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_price_date ON price_logs (date_recorded);
CREATE INDEX IF NOT EXISTS idx_product_store ON price_logs (product_id, store_id);
