#!/usr/bin/env python3
"""Clean up test rounds from local database"""

import sqlite3

def main():
    conn = sqlite3.connect('data/minigolf.db')

    # Execute cleanup SQL
    with open('migrations/cleanup_local_test_rounds.sql', 'r') as f:
        sql = f.read()

    conn.executescript(sql)
    conn.commit()

    # Verify cleanup
    cursor = conn.execute('SELECT COUNT(*) FROM rounds')
    rounds_count = cursor.fetchone()[0]

    cursor = conn.execute('SELECT COUNT(*) FROM round_scores')
    scores_count = cursor.fetchone()[0]

    print(f'[OK] Cleanup completed')
    print(f'     Rounds remaining: {rounds_count}')
    print(f'     Scores remaining: {scores_count}')

    conn.close()

if __name__ == '__main__':
    main()
