#!/usr/bin/env python3
"""
Load rounds data into production with course ID mapping
This script maps course names from local DB to production course IDs
"""

import sqlite3
from pathlib import Path

def main():
    # This script is meant to be run ON THE SERVER via the admin endpoint
    # It reads the local rounds data and maps to production courses

    local_db = 'data/minigolf.db'

    conn = sqlite3.connect(local_db)
    conn.row_factory = sqlite3.Row

    # Get real rounds with course names
    cursor = conn.execute("""
        SELECT r.id, r.date_played, c.name as course_name
        FROM rounds r
        JOIN courses c ON r.course_id = c.id
        WHERE c.name NOT LIKE '%Test%'
        ORDER BY r.date_played
    """)
    rounds_with_names = cursor.fetchall()

    # Get round scores
    round_ids = [r['id'] for r in rounds_with_names]
    placeholders = ','.join(['?'] * len(round_ids))
    cursor = conn.execute(f"""
        SELECT round_id, player_id, player_name, score, hole_scores
        FROM round_scores
        WHERE round_id IN ({placeholders})
    """, round_ids)
    scores = cursor.fetchall()

    # Group by round - convert Row objects to dicts
    rounds_data = []
    for r in rounds_with_names:
        round_scores = [s for s in scores if s['round_id'] == r['id']]
        rounds_data.append({
            'id': r['id'],
            'date_played': r['date_played'],
            'course_name': r['course_name'],
            'scores': [dict(s) for s in round_scores]  # Convert Row to dict
        })

    # Generate Python code for the endpoint
    import json
    output = {
        'rounds': rounds_data
    }

    output_file = Path('migrations/rounds_data.json')
    output_file.write_text(json.dumps(output, indent=2), encoding='utf-8')

    print(f"[OK] Created {output_file}")
    print(f"     {len(rounds_data)} rounds")
    print(f"     {len(scores)} scores")

if __name__ == '__main__':
    main()
