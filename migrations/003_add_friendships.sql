-- Migration 003: Add friendships table for friend relationships
-- Version 3

-- Friendships table for mutual friend relationships
CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id TEXT NOT NULL,
    addressee_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (requester_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (addressee_id) REFERENCES players(id) ON DELETE CASCADE,
    UNIQUE(requester_id, addressee_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester_id);
CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON friendships(status);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (3, datetime('now'));
