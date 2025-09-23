PRAGMA foreign_keys = ON;

-- Роли
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO roles (name) VALUES
('Администратор'),
('Модератор'),
('Участник');

-- Пользователи
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    telegram_id INTEGER,
    fio TEXT,
    email TEXT,
    role_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Сессии
CREATE TABLE tg_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Встречи
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    department TEXT,
    country TEXT,
    deadline_at DATETIME,
    status TEXT DEFAULT 'draft',  -- draft, open, closed, scheduled
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Вопросы для встреч
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    order_idx INTEGER NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 0,
    type TEXT NOT NULL DEFAULT 'text', -- text, choice, number и т.д.
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);

-- Варианты ответа (для choice-вопросов)
CREATE TABLE options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    label TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Ответы пользователей (респонсы)
CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meeting_id INTEGER NOT NULL,
    submitted_at DATETIME,
    status TEXT DEFAULT 'draft', -- draft, submitted
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);

-- Конкретные ответы на вопросы
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    value TEXT,
    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

------------------------------------------------------------------
-- Тестовые данные
------------------------------------------------------------------

-- Админ и пользователи (без хеша, пароли открытые)
INSERT INTO users (username, password_hash, role_id) VALUES
('admin', 'admin123', 1),
('moderator', 'mod123', 2),
('user1', 'user123', 3);

-- Тестовые встречи
INSERT INTO meetings (title, description, department, country, deadline_at, status, created_by) VALUES
('Планирование Q4', 'Обсуждение задач на квартал', 'Отдел продаж', 'Россия', '2025-12-31', 'scheduled', 1),
('Ретроспектива Q3', 'Анализ результатов', 'Разработка', 'Россия', '2025-10-15', 'open', 2);

-- Вопросы для встреч
INSERT INTO questions (meeting_id, text, order_idx, is_required, type) VALUES
(1, 'Какие приоритетные задачи на следующий квартал?', 1, 1, 'text'),
(1, 'Нужно ли увеличить бюджет?', 2, 0, 'choice'),
(2, 'Что удалось достичь в Q3?', 1, 1, 'text');

-- Варианты ответа для вопроса (id=2)
INSERT INTO options (question_id, value, label) VALUES
(2, 'yes', 'Да'),
(2, 'no', 'Нет'),
(2, 'maybe', 'Нужно обсудить');
