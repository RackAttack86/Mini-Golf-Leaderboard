#!/usr/bin/env python3
"""
Export real rounds data (excluding test courses) for migration to production
"""

import sqlite3
from pathlib import Path

def main():
    conn = sqlite3.connect('data/minigolf.db')
    conn.row_factory = sqlite3.Row

    # Get rounds NOT played on test courses
    cursor = conn.execute("""
        SELECT r.id, r.course_id, r.date_played
        FROM rounds r
        JOIN courses c ON r.course_id = c.id
        WHERE c.name NOT LIKE '%Test%' AND c.name NOT LIKE '%test%'
        ORDER BY r.date_played
    """)
    real_rounds = cursor.fetchall()
    real_round_ids = [r['id'] for r in real_rounds]

    print(f"Found {len(real_rounds)} real rounds to export")

    # Get round scores for these rounds
    placeholders = ','.join(['?'] * len(real_round_ids))
    cursor = conn.execute(f"""
        SELECT round_id, player_id, player_name, score, hole_scores
        FROM round_scores
        WHERE round_id IN ({placeholders})
        ORDER BY round_id, score
    """, real_round_ids)
    round_scores = cursor.fetchall()

    print(f"Found {len(round_scores)} round scores")

    # Generate SQL for rounds
    rounds_sql = ['-- Real rounds data export', '']
    for r in real_rounds:
        sql = f"INSERT OR IGNORE INTO rounds (id, course_id, date_played) VALUES ('{r['id']}', '{r['course_id']}', '{r['date_played']}');"
        rounds_sql.append(sql)

    # Generate SQL for round scores
    scores_sql = ['', '-- Round scores data']
    for rs in round_scores:
        player_name = (rs['player_name'] or '').replace("'", "''")
        hole_scores = (rs['hole_scores'] or '').replace("'", "''")
        sql = f"INSERT OR IGNORE INTO round_scores (round_id, player_id, player_name, score, hole_scores) VALUES ('{rs['round_id']}', '{rs['player_id']}', '{player_name}', {rs['score']}, '{hole_scores}');"
        scores_sql.append(sql)

    # Write to file
    output_file = Path('migrations/seed_rounds.sql')
    all_sql = rounds_sql + scores_sql
    output_file.write_text('\n'.join(all_sql), encoding='utf-8')

    print(f"\n[OK] Created {output_file}")
    print(f"     {len(real_rounds)} rounds")
    print(f"     {len(round_scores)} scores")

    # Generate cleanup SQL for local database
    cleanup_sql = [
        "-- Delete test course rounds from local database",
        "",
        "-- Delete round scores for test rounds",
        f"DELETE FROM round_scores WHERE round_id NOT IN ({placeholders});",
        "",
        "-- Delete test rounds",
        f"DELETE FROM rounds WHERE id NOT IN ({placeholders});",
        "",
        "VACUUM;"
    ]

    cleanup_file = Path('migrations/cleanup_local_test_rounds.sql')
    # Need to format with actual IDs
    round_ids_str = ', '.join(["'" + rid + "'" for rid in real_round_ids])
    cleanup_sql_formatted = [
        "-- Delete test course rounds from local database",
        "",
        "-- Delete round scores for test rounds",
        f"DELETE FROM round_scores WHERE round_id NOT IN ({round_ids_str});",
        "",
        "-- Delete test rounds",
        f"DELETE FROM rounds WHERE id NOT IN ({round_ids_str});",
        "",
        "VACUUM;"
    ]
    cleanup_file.write_text('\n'.join(cleanup_sql_formatted), encoding='utf-8')

    print(f"\n[OK] Created {cleanup_file}")
    print(f"     Will delete {80 - len(real_rounds)} test rounds")

if __name__ == '__main__':
    main()
