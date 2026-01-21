from models.round import Round
from models.course import Course
from models.player import Player
from typing import List, Dict, Any


class CoursesPlayedService:
    """Service for calculating courses played statistics by player(s)"""

    @staticmethod
    def get_courses_played_by_players(player_ids: List[str], sort_order: str = 'desc') -> List[Dict[str, Any]]:
        """
        Get statistics on how many times selected players have played each course together

        Args:
            player_ids: List of player IDs to include
            sort_order: 'asc' for ascending, 'desc' for descending, 'name' for alphabetical

        Returns:
            List of course statistics with play counts (including courses with 0 plays)
        """
        if not player_ids:
            return []

        # Get all courses
        courses = Course.get_all()

        # Get all rounds
        all_rounds = Round.get_all()

        # Count plays per course for selected players
        course_play_counts = {}

        for course in courses:
            course_id = course['id']
            course_play_counts[course_id] = {
                'course': course,
                'play_count': 0,
                'player_wins': {}  # Track wins per player
            }

        # Count rounds where ALL of the selected players participated
        for round_data in all_rounds:
            course_id = round_data['course_id']

            # Get player IDs in this round
            players_in_round = set(score['player_id'] for score in round_data['scores'])

            # Check if ALL selected players played in this round
            all_selected_players_participated = all(
                player_id in players_in_round
                for player_id in player_ids
            )

            if all_selected_players_participated and course_id in course_play_counts:
                course_play_counts[course_id]['play_count'] += 1

                # Find the winner among selected players
                selected_players_scores = [
                    score for score in round_data['scores']
                    if score['player_id'] in player_ids
                ]

                if selected_players_scores:
                    # Winner is player with lowest score among selected players
                    winner = min(selected_players_scores, key=lambda x: x['score'])
                    winner_id = winner['player_id']
                    winner_name = winner['player_name']

                    # Initialize player wins dict if needed
                    if winner_id not in course_play_counts[course_id]['player_wins']:
                        course_play_counts[course_id]['player_wins'][winner_id] = {
                            'id': winner_id,
                            'name': winner_name,
                            'wins': 0
                        }

                    course_play_counts[course_id]['player_wins'][winner_id]['wins'] += 1

        # Convert to list
        results = list(course_play_counts.values())

        # Calculate max for percentage bars
        max_plays = max([r['play_count'] for r in results]) if results else 1
        if max_plays == 0:
            max_plays = 1

        # Add percentage for display and find top winner for each course
        for result in results:
            result['percentage'] = (result['play_count'] / max_plays) * 100 if max_plays > 0 else 0

            # Find player with most wins on this course
            if result['player_wins']:
                top_winner = max(result['player_wins'].values(), key=lambda x: x['wins'])
                result['top_winner_name'] = top_winner['name']
                result['top_winner_wins'] = top_winner['wins']

                # Get the winner's favorite color
                winner_player = Player.get_by_id(top_winner['id'])
                result['top_winner_color'] = winner_player['favorite_color'] if winner_player else '#2e7d32'

                # Abbreviate name if longer than 15 characters
                if len(result['top_winner_name']) > 15:
                    # Take first name and last initial
                    name_parts = result['top_winner_name'].split()
                    if len(name_parts) > 1:
                        result['top_winner_name'] = f"{name_parts[0]} {name_parts[-1][0]}."
                    else:
                        # Just truncate and add ellipsis
                        result['top_winner_name'] = result['top_winner_name'][:12] + "..."
            else:
                result['top_winner_name'] = None
                result['top_winner_wins'] = 0
                result['top_winner_color'] = '#2e7d32'

        # Sort based on sort_order (after calculating top_winner_wins)
        if sort_order == 'asc':
            results.sort(key=lambda x: x['play_count'])
        elif sort_order == 'name':
            results.sort(key=lambda x: x['course']['name'])
        elif sort_order == 'wins':
            results.sort(key=lambda x: x['top_winner_wins'], reverse=True)
        else:  # desc
            results.sort(key=lambda x: x['play_count'], reverse=True)

        # Return all courses including those with 0 plays
        return results
