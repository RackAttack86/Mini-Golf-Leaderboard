"""
Course Trophy model - manages trophy ownership and transfers

Each course can have one trophy that can only be owned by one player at a time.
Trophy transfers occur when:
1. Initial assignment (first 4+ player round on a course)
2. Trophy contested in a round (owner playing, 4+ players, trophy_up_for_grabs=True)
"""

from typing import List, Optional, Dict, Any, Tuple
from models.database import get_db


class CourseTrophy:
    """
    Course Trophy model - manages trophy ownership and transfers
    """

    @staticmethod
    def generate_trophy_filename(course_name: str) -> Tuple[str, str]:
        """
        Generate trophy filename and difficulty directory from course name.

        Trophy files are stored as:
        - Remove " (HARD)" suffix
        - Remove apostrophes and commas
        - Replace spaces with underscores
        - Add .png extension

        Args:
            course_name: Full course name (e.g., "Alice's Adventures in Wonderland (HARD)")

        Returns:
            Tuple of (difficulty, filename) where difficulty is 'hard' or 'normal'
            e.g., ('hard', 'Alices_Adventures_in_Wonderland.png')
        """
        # Determine difficulty
        difficulty = 'hard' if '(HARD)' in course_name else 'normal'

        # Remove (HARD) suffix
        clean_name = course_name.replace(' (HARD)', '')

        # Remove special characters that aren't in filenames
        clean_name = clean_name.replace("'", "")  # Remove apostrophes
        clean_name = clean_name.replace(",", "")  # Remove commas

        # Replace spaces with underscores
        filename = clean_name.replace(' ', '_') + '.png'

        return difficulty, filename

    @staticmethod
    def get_trophy_owner(course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current trophy owner for a course.

        Args:
            course_id: Course ID

        Returns:
            Dict with owner info or None if no owner
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT
                ct.course_id,
                ct.player_id,
                ct.date_acquired,
                ct.acquired_round_id,
                p.name as player_name
            FROM course_trophies ct
            JOIN players p ON ct.player_id = p.id
            WHERE ct.course_id = ?
        """, (course_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'course_id': row['course_id'],
            'player_id': row['player_id'],
            'player_name': row['player_name'],
            'date_acquired': row['date_acquired'],
            'acquired_round_id': row['acquired_round_id']
        }

    @staticmethod
    def get_owners_map() -> Dict[str, Dict[str, str]]:
        """
        Get all trophy owners as dict for easy JavaScript access.

        Returns:
            {course_id: {'owner_id': player_id, 'owner_name': player_name}}
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT
                ct.course_id,
                ct.player_id,
                p.name as player_name
            FROM course_trophies ct
            JOIN players p ON ct.player_id = p.id
        """)

        result = {}
        for row in cursor.fetchall():
            result[row['course_id']] = {
                'owner_id': row['player_id'],
                'owner_name': row['player_name']
            }

        return result

    @staticmethod
    def get_trophies_owned_by_player(player_id: str) -> List[Dict[str, Any]]:
        """
        Get all course trophies owned by a player.

        Args:
            player_id: Player ID

        Returns:
            List of trophy dicts with course info and trophy image path
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT
                ct.course_id,
                ct.date_acquired,
                ct.acquired_round_id,
                c.name as course_name,
                c.image_url
            FROM course_trophies ct
            JOIN courses c ON ct.course_id = c.id
            WHERE ct.player_id = ?
            ORDER BY c.name ASC
        """, (player_id,))

        trophies = []
        for row in cursor.fetchall():
            # Generate trophy filename using helper method
            course_name = row['course_name']
            difficulty, trophy_filename = CourseTrophy.generate_trophy_filename(course_name)

            trophies.append({
                'course_id': row['course_id'],
                'course_name': course_name,
                'date_acquired': row['date_acquired'],
                'acquired_round_id': row['acquired_round_id'],
                'trophy_image': trophy_filename,
                'difficulty': difficulty
            })

        return trophies

    @staticmethod
    def determine_round_winner(scores: List[Dict[str, Any]]) -> Optional[str]:
        """
        Determine winner from round scores.

        Args:
            scores: List of dicts with 'player_id' and 'score'

        Returns:
            player_id of winner, or None if tie for first place
        """
        if not scores:
            return None

        min_score = min(s['score'] for s in scores)
        winners = [s for s in scores if s['score'] == min_score]

        # If tie, return None (trophy stays with current owner)
        if len(winners) > 1:
            return None

        return winners[0]['player_id']

    @staticmethod
    def transfer_trophy(course_id: str, new_owner_id: str, round_id: str,
                       date: str) -> Tuple[bool, str]:
        """
        Transfer trophy to new owner.

        Args:
            course_id: Course ID
            new_owner_id: New owner player ID
            round_id: Round ID where trophy was won
            date: Date acquired (YYYY-MM-DD)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        try:
            # Validate that new owner exists
            cursor = conn.execute(
                "SELECT id FROM players WHERE id = ?",
                (new_owner_id,)
            )
            if not cursor.fetchone():
                return False, f"Player {new_owner_id} does not exist"

            # Check if trophy already exists for this course
            cursor = conn.execute(
                "SELECT player_id FROM course_trophies WHERE course_id = ?",
                (course_id,)
            )
            current = cursor.fetchone()

            if current:
                # Update existing trophy
                conn.execute("""
                    UPDATE course_trophies
                    SET player_id = ?, date_acquired = ?, acquired_round_id = ?
                    WHERE course_id = ?
                """, (new_owner_id, date, round_id, course_id))
                return True, "Trophy transferred"
            else:
                # Insert new trophy (first time awarded for this course)
                conn.execute("""
                    INSERT INTO course_trophies
                    (course_id, player_id, date_acquired, acquired_round_id)
                    VALUES (?, ?, ?, ?)
                """, (course_id, new_owner_id, date, round_id))
                return True, "Trophy awarded"

        except Exception as e:
            return False, f"Error transferring trophy: {str(e)}"

    @staticmethod
    def initialize_trophies_from_history() -> Tuple[int, List[str]]:
        """
        Retroactively assign trophies based on historical round data.
        Finds first 4+ player round for each course and awards trophy to winner.

        Returns:
            Tuple of (trophies_assigned_count, warnings_list)
        """
        db = get_db()
        conn = db.get_connection()

        warnings = []
        assigned_count = 0

        try:
            # Find first qualifying round for each course
            cursor = conn.execute("""
                WITH RoundPlayerCounts AS (
                    SELECT
                        r.id as round_id,
                        r.course_id,
                        r.course_name,
                        r.date_played,
                        r.timestamp,
                        COUNT(DISTINCT rs.player_id) as player_count,
                        MIN(rs.score) as winning_score
                    FROM rounds r
                    JOIN round_scores rs ON r.id = rs.round_id
                    GROUP BY r.id
                    HAVING player_count >= 4
                ),
                FirstRoundPerCourse AS (
                    SELECT
                        course_id,
                        MIN(timestamp) as first_timestamp
                    FROM RoundPlayerCounts
                    GROUP BY course_id
                ),
                QualifyingRounds AS (
                    SELECT
                        rpc.course_id,
                        rpc.round_id,
                        rpc.course_name,
                        rpc.date_played,
                        rpc.winning_score
                    FROM RoundPlayerCounts rpc
                    JOIN FirstRoundPerCourse frc ON
                        rpc.course_id = frc.course_id AND
                        rpc.timestamp = frc.first_timestamp
                )
                SELECT
                    qr.course_id,
                    qr.round_id,
                    qr.course_name,
                    qr.date_played,
                    rs.player_id,
                    rs.player_name,
                    rs.score
                FROM QualifyingRounds qr
                JOIN round_scores rs ON
                    qr.round_id = rs.round_id AND
                    rs.score = qr.winning_score
                ORDER BY qr.course_id, rs.player_id
            """)

            rounds_data = cursor.fetchall()

            # Group by course to handle ties
            courses_processed = {}
            for row in rounds_data:
                course_id = row['course_id']

                if course_id not in courses_processed:
                    courses_processed[course_id] = []

                courses_processed[course_id].append({
                    'round_id': row['round_id'],
                    'player_id': row['player_id'],
                    'player_name': row['player_name'],
                    'date_played': row['date_played'],
                    'course_name': row['course_name']
                })

            # Assign trophies
            for course_id, winners in courses_processed.items():
                if len(winners) > 1:
                    # Tie in first qualifying round - assign to first player alphabetically
                    winners_sorted = sorted(winners, key=lambda x: x['player_name'])
                    winner = winners_sorted[0]
                    warnings.append(
                        f"Tie in first round for {winner['course_name']} - "
                        f"awarded to {winner['player_name']}"
                    )
                else:
                    winner = winners[0]

                # Insert trophy
                conn.execute("""
                    INSERT INTO course_trophies
                    (course_id, player_id, date_acquired, acquired_round_id)
                    VALUES (?, ?, ?, ?)
                """, (
                    course_id,
                    winner['player_id'],
                    winner['date_played'],
                    winner['round_id']
                ))

                assigned_count += 1

            return assigned_count, warnings

        except Exception as e:
            warnings.append(f"Error initializing trophies: {str(e)}")
            return assigned_count, warnings
