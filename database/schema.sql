PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'student'
        CHECK (role IN ('student', 'instructor', 'admin')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price NUMERIC NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled')),
    total_amount NUMERIC NOT NULL CHECK (total_amount >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
    UNIQUE (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    difficulty TEXT NOT NULL
        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    category TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    flag TEXT NOT NULL,
    hint_1 TEXT,
    hint_2 TEXT,
    hint_3 TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS challenge_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    points_awarded INTEGER NOT NULL DEFAULT 0 CHECK (points_awarded >= 0),
    hints_used INTEGER NOT NULL DEFAULT 0 CHECK (hints_used BETWEEN 0 AND 3),
    attempts INTEGER NOT NULL DEFAULT 1 CHECK (attempts > 0),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id) ON DELETE CASCADE,
    UNIQUE (user_id, challenge_id)
);

CREATE TABLE IF NOT EXISTS challenge_progress (
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    highest_hint INTEGER NOT NULL DEFAULT 0 CHECK (highest_hint BETWEEN 0 AND 3),
    last_attempt_at TEXT,
    PRIMARY KEY (user_id, challenge_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lab_cookie_tokens (
    user_id INTEGER PRIMARY KEY,
    token_digest TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lab_order_accounts (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lab_orders (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    total_amount NUMERIC NOT NULL CHECK (total_amount >= 0),
    private_note TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES lab_order_accounts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lab_chain_tokens (
    user_id INTEGER PRIMARY KEY,
    token_digest TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lab_final_records (
    id INTEGER PRIMARY KEY,
    fictional_owner TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
    public_note TEXT NOT NULL,
    private_note TEXT NOT NULL
);
