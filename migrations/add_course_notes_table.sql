-- Migration: Add course_notes table
-- Date: 2025-12-31

BEGIN TRANSACTION;

-- Create course notes table
CREATE TABLE IF NOT EXISTS course_notes (
    player_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    notes TEXT,
    date_created TEXT NOT NULL,
    date_updated TEXT NOT NULL,
    PRIMARY KEY (player_id, course_id),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_course_notes_player_id ON course_notes(player_id);
CREATE INDEX IF NOT EXISTS idx_course_notes_course_id ON course_notes(course_id);

COMMIT;
