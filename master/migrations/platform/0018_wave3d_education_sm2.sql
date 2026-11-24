-- Wave 3D (EPK-19): Persistent SM-2 spaced-repetition education flashcards.
CREATE TABLE IF NOT EXISTS edu_flashcards (
    card_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    repetitions INTEGER NOT NULL DEFAULT 0,
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    next_review_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edu_flashcards_user ON edu_flashcards(user_id, next_review_at);
