#!/usr/bin/env python3
"""
Generate clean seed data files with only real data (no test data)
This script creates SQL files for players, courses, and a cleanup migration
"""

import sqlite3
from pathlib import Path

def main():
    conn = sqlite3.connect('data/minigolf.db')
    conn.row_factory = sqlite3.Row

    # ===== IDENTIFY REAL DATA =====

    # Real players (created before 2026-01-06)
    cursor = conn.execute("""
        SELECT id, name, email, profile_picture, favorite_color, google_id, role,
               last_login, created_at, active, meta_quest_username
        FROM players
        WHERE created_at < '2026-01-06' OR (name = 'Max' AND created_at = '2025-12-27T02:14:32Z')
        ORDER BY created_at
    """)
    real_players = cursor.fetchall()
    real_player_ids = [p['id'] for p in real_players]

    # Real courses (Walkabout Mini Golf only, no test data)
    cursor = conn.execute("""
        SELECT id, name, location, holes, par, image_url, active, created_at
        FROM courses
        WHERE location = 'Walkabout Mini Golf'
          AND name NOT LIKE '%Test%'
        ORDER BY name
    """)
    real_courses = cursor.fetchall()
    real_course_ids = [c['id'] for c in real_courses]

    # Real rounds (with at least one real player)
    placeholders = ','.join(['?'] * len(real_player_ids))
    cursor = conn.execute(f"""
        SELECT DISTINCT r.id
        FROM rounds r
        JOIN round_scores rs ON r.id = rs.round_id
        WHERE rs.player_id IN ({placeholders})
    """, real_player_ids)
    real_rounds = cursor.fetchall()
    real_round_ids = [r['id'] for r in real_rounds]

    print(f"Found {len(real_players)} real players")
    print(f"Found {len(real_courses)} real courses")
    print(f"Found {len(real_rounds)} real rounds")

    # ===== GENERATE CLEANUP SQL =====

    cleanup_lines = [
        "-- Cleanup test data from database",
        "-- This script deletes all test players, courses, and rounds",
        "-- Keeping only real Walkabout Mini Golf data",
        "",
        "-- Disable foreign keys temporarily",
        "PRAGMA foreign_keys = OFF;",
        "",
    ]

    # Delete test rounds (and their scores, notes, pictures)
    if real_round_ids:
        round_ids_str = "', '".join(real_round_ids)
        cleanup_lines.extend([
            "-- Delete test round data",
            f"DELETE FROM round_pictures WHERE round_id NOT IN ('{round_ids_str}');",
            f"DELETE FROM round_notes WHERE round_id NOT IN ('{round_ids_str}');",
            f"DELETE FROM round_scores WHERE round_id NOT IN ('{round_ids_str}');",
            f"DELETE FROM rounds WHERE id NOT IN ('{round_ids_str}');",
            "",
        ])

    # Delete test courses (and their trophies, notes)
    if real_course_ids:
        course_ids_str = "', '".join(real_course_ids)
        cleanup_lines.extend([
            "-- Delete test course data",
            f"DELETE FROM course_trophies WHERE course_id NOT IN ('{course_ids_str}');",
            f"DELETE FROM course_notes WHERE course_id NOT IN ('{course_ids_str}');",
            f"DELETE FROM courses WHERE id NOT IN ('{course_ids_str}');",
            "",
        ])

    # Delete test players (and their achievements, personal bests)
    if real_player_ids:
        player_ids_str = "', '".join(real_player_ids)
        cleanup_lines.extend([
            "-- Delete test player data",
            f"DELETE FROM personal_bests WHERE player_id NOT IN ('{player_ids_str}');",
            f"DELETE FROM achievements WHERE player_id NOT IN ('{player_ids_str}');",
            f"DELETE FROM players WHERE id NOT IN ('{player_ids_str}');",
            "",
        ])

    cleanup_lines.extend([
        "-- Re-enable foreign keys",
        "PRAGMA foreign_keys = ON;",
        "",
        "-- Vacuum to reclaim space",
        "VACUUM;",
    ])

    # Write cleanup SQL
    cleanup_file = Path('migrations/cleanup_test_data.sql')
    cleanup_file.write_text('\n'.join(cleanup_lines), encoding='utf-8')
    print(f"[OK] Created {cleanup_file}")

    # ===== GENERATE CLEAN PLAYER SEED DATA =====

    player_lines = ['-- Real player seed data', '']
    for player in real_players:
        name = (player['name'] or '').replace("'", "''")
        email = (player['email'] or '').replace("'", "''")
        profile_pic = (player['profile_picture'] or '').replace("'", "''")
        fav_color = (player['favorite_color'] or '').replace("'", "''")
        google_id = (player['google_id'] or '').replace("'", "''")
        role = (player['role'] or 'player').replace("'", "''")
        last_login = (player['last_login'] or '').replace("'", "''")
        created_at = player['created_at'] or 'CURRENT_TIMESTAMP'
        active = player['active'] if player['active'] is not None else 1
        meta_quest = (player['meta_quest_username'] or '').replace("'", "''")

        sql = f"""INSERT OR IGNORE INTO players (id, name, email, profile_picture, favorite_color, google_id, role, last_login, created_at, active, meta_quest_username)
VALUES ('{player['id']}', '{name}', '{email}', '{profile_pic}', '{fav_color}', '{google_id}', '{role}', '{last_login}', '{created_at}', {active}, '{meta_quest}');"""
        player_lines.append(sql)

    player_file = Path('migrations/seed_players.sql')
    player_file.write_text('\n'.join(player_lines), encoding='utf-8')
    print(f"[OK] Created {player_file}")

    # ===== REGENERATE CLEAN COURSE SEED DATA =====

    course_lines = ['-- Real course seed data (Walkabout Mini Golf only)', '']
    for course in real_courses:
        name = (course['name'] or '').replace("'", "''")
        location = (course['location'] or '').replace("'", "''")
        image_url = (course['image_url'] or '').replace("'", "''")
        holes = course['holes'] if course['holes'] is not None else 18
        par = course['par'] if course['par'] is not None else 54
        active = course['active'] if course['active'] is not None else 1
        created_at = course['created_at'] or 'CURRENT_TIMESTAMP'

        sql = f"""INSERT OR IGNORE INTO courses (id, name, location, holes, par, image_url, active, created_at)
VALUES ('{course['id']}', '{name}', '{location}', {holes}, {par}, '{image_url}', {active}, '{created_at}');"""
        course_lines.append(sql)

    course_file = Path('migrations/seed_courses.sql')
    course_file.write_text('\n'.join(course_lines), encoding='utf-8')
    print(f"[OK] Recreated {course_file} (clean version)")

    print("\n[SUCCESS] Seed data generation complete!")
    print(f"\nTo clean up the database:")
    print(f"  python -c \"import sqlite3; conn = sqlite3.connect('data/minigolf.db'); conn.executescript(open('migrations/cleanup_test_data.sql').read()); conn.close()\"")

if __name__ == '__main__':
    main()
