PRAGMA foreign_keys = ON;

-- =========================
-- Users (Telegram users)
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- Searches (user subscriptions)
-- =========================
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    vinted_url TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =========================
-- Items (Vinted listings)
-- =========================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vinted_id INTEGER NOT NULL,
    title TEXT,
    price TEXT,
    url TEXT,
    image_url TEXT,                -- 🔹 ссылка на картинку
    brand TEXT,
    created_at DATETIME,

    UNIQUE (vinted_id)
);

-- =========================
-- Search ↔ Item relation
-- =========================
CREATE TABLE IF NOT EXISTS search_items (
    search_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    sent BOOLEAN DEFAULT 0,
    sent_at DATETIME,

    PRIMARY KEY (search_id, item_id),

    FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

-- =========================
-- Indexes (performance)
-- =========================
CREATE INDEX IF NOT EXISTS idx_users_tg_id
    ON users(tg_id);

CREATE INDEX IF NOT EXISTS idx_searches_user_id
    ON searches(user_id);

CREATE INDEX IF NOT EXISTS idx_items_vinted_id
    ON items(vinted_id);

CREATE INDEX IF NOT EXISTS idx_search_items_sent
    ON search_items(sent);
