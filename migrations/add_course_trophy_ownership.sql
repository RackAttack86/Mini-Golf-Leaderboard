-- Add course trophy ownership feature
-- This migration adds support for course-specific trophies that can only be owned by one player at a time

-- Add trophy_up_for_grabs field to rounds table
ALTER TABLE rounds ADD COLUMN trophy_up_for_grabs INTEGER DEFAULT 0;

-- Create course_trophies table
-- PRIMARY KEY on course_id ensures one trophy per course
CREATE TABLE IF NOT EXISTS course_trophies (
    course_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    date_acquired TEXT NOT NULL,
    acquired_round_id TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (acquired_round_id) REFERENCES rounds(id)
);

CREATE INDEX IF NOT EXISTS idx_course_trophies_player ON course_trophies(player_id);
CREATE INDEX IF NOT EXISTS idx_course_trophies_date ON course_trophies(date_acquired);
