CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    deadline TIMESTAMP,
    notify_minutes INTEGER DEFAULT 0
);
