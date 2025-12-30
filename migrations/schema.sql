-- Mini Golf Leaderboard SQLite Schema
-- Version 1.0

-- Players table with Meta Quest username support
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    email TEXT,
    profile_picture TEXT,
    favorite_color TEXT DEFAULT '#2e7d32',
    google_id TEXT UNIQUE,
    role TEXT DEFAULT 'player' CHECK(role IN ('player', 'admin')),
    last_login TEXT,
    created_at TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    meta_quest_username TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_players_google_id ON players(google_id);
CREATE INDEX IF NOT EXISTS idx_players_meta_quest ON players(meta_quest_username);
CREATE INDEX IF NOT EXISTS idx_players_active ON players(active);

-- Courses table
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    location TEXT,
    holes INTEGER,
    par INTEGER,
    image_url TEXT,
    created_at TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_courses_active ON courses(active);
CREATE INDEX IF NOT EXISTS idx_courses_name ON courses(name);

-- Rounds table with round_start_time and picture support
CREATE TABLE IF NOT EXISTS rounds (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    course_name TEXT NOT NULL,
    date_played TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    round_start_time TEXT,
    notes TEXT,
    picture_filename TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE INDEX IF NOT EXISTS idx_rounds_course_id ON rounds(course_id);
CREATE INDEX IF NOT EXISTS idx_rounds_date_played ON rounds(date_played);
CREATE INDEX IF NOT EXISTS idx_rounds_timestamp ON rounds(timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rounds_duplicate_check
    ON rounds(course_id, round_start_time)
    WHERE round_start_time IS NOT NULL;

-- Round scores table with hole-by-hole scores
CREATE TABLE IF NOT EXISTS round_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    hole_scores TEXT,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(round_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_round_scores_round_id ON round_scores(round_id);
CREATE INDEX IF NOT EXISTS idx_round_scores_player_id ON round_scores(player_id);

-- Course ratings table
CREATE TABLE IF NOT EXISTS course_ratings (
    player_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    date_rated TEXT NOT NULL,
    PRIMARY KEY (player_id, course_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE INDEX IF NOT EXISTS idx_ratings_course_id ON course_ratings(course_id);

-- Tournaments table
CREATE TABLE IF NOT EXISTS tournaments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    created_at TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_tournaments_active ON tournaments(active);

-- Tournament rounds junction table
CREATE TABLE IF NOT EXISTS tournament_rounds (
    tournament_id TEXT NOT NULL,
    round_id TEXT NOT NULL,
    PRIMARY KEY (tournament_id, round_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tournament_rounds_tournament ON tournament_rounds(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_rounds_round ON tournament_rounds(round_id);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));
