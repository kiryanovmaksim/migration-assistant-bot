PRAGMA foreign_keys = ON;

-- ---------- Roles ----------
CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(32) UNIQUE NOT NULL
);

-- ---------- Users ----------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      VARCHAR(64) UNIQUE,
    password_hash VARCHAR(255),
    telegram_id   INTEGER,
    fio           VARCHAR(255),
    email         VARCHAR(255),
    role_id       INTEGER REFERENCES roles(id),
    is_active     BOOLEAN DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------- TgSessions ----------
CREATE TABLE IF NOT EXISTS tg_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    user_id     INTEGER REFERENCES users(id),
    is_active   BOOLEAN DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------- Meetings ----------
CREATE TABLE IF NOT EXISTS meetings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    department  VARCHAR(128),
    country     VARCHAR(64),
    deadline_at DATETIME,
    status      VARCHAR(16) DEFAULT 'draft',
    created_by  INTEGER REFERENCES users(id),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------- Questions ----------
CREATE TABLE IF NOT EXISTS questions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    order_idx  INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT 1,
    type       VARCHAR(16) DEFAULT 'text'
);

-- ---------- Options ----------
CREATE TABLE IF NOT EXISTS options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    value       VARCHAR(128) NOT NULL,
    label       VARCHAR(128)
);

-- ---------- Responses ----------
CREATE TABLE IF NOT EXISTS responses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    meeting_id  INTEGER REFERENCES meetings(id),
    submitted_at DATETIME,
    status      VARCHAR(16) DEFAULT 'draft'
);

-- ---------- Answers ----------
CREATE TABLE IF NOT EXISTS answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER REFERENCES responses(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    value       TEXT
);

-- ---------- Первичное наполнение ----------
INSERT OR IGNORE INTO roles (id, name) VALUES
    (1, 'Администратор'),
    (2, 'Модератор'),
    (3, 'Участник');

