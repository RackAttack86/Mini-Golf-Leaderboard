-- Migration 004: Seed friendships between all existing players
-- Makes all existing active players friends with each other
-- Version 4

-- Insert accepted friendships between all pairs of active players
-- Using a self-join to create pairs where player1.id < player2.id to avoid duplicates
INSERT OR IGNORE INTO friendships (requester_id, addressee_id, status, created_at, updated_at)
SELECT
    p1.id as requester_id,
    p2.id as addressee_id,
    'accepted' as status,
    datetime('now') as created_at,
    datetime('now') as updated_at
FROM players p1
CROSS JOIN players p2
WHERE p1.id < p2.id
AND p1.active = 1
AND p2.active = 1;

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (4, datetime('now'));
