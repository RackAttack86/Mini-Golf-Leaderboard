from models.player import Player
from models.round import Round
from typing import Dict, Any, List


class ComparisonService:
    """Service for head-to-head player comparisons"""

    @staticmethod
    def compare_players(player1_id: str, player2_id: str) -> Dict[str, Any]:
        """
        Compare two players head-to-head

        Args:
            player1_id: First player ID
            player2_id: Second player ID

        Returns:
            Dictionary of comparison data
        """
        # Get all rounds
        all_rounds = Round.get_all()

        # Calculate overall stats for each player
        player1_stats = ComparisonService._get_player_stats(player1_id, all_rounds)
        player2_stats = ComparisonService._get_player_stats(player2_id, all_rounds)

        # Find rounds where both players competed
        head_to_head = ComparisonService._get_head_to_head(player1_id, player2_id, all_rounds)

        # Determine overall winner (better average score)
        overall_winner = None
        if player1_stats['total_rounds'] > 0 and player2_stats['total_rounds'] > 0:
            if player1_stats['average_score'] < player2_stats['average_score']:
                overall_winner = player1_id
            elif player2_stats['average_score'] < player1_stats['average_score']:
                overall_winner = player2_id

        # Get detailed round history for charts
        player1_rounds = ComparisonService._get_player_rounds(player1_id, all_rounds)
        player2_rounds = ComparisonService._get_player_rounds(player2_id, all_rounds)

        # Get course breakdown
        player1_courses = ComparisonService._get_course_breakdown(player1_id, all_rounds)
        player2_courses = ComparisonService._get_course_breakdown(player2_id, all_rounds)

        return {
            'player1_stats': player1_stats,
            'player2_stats': player2_stats,
            'head_to_head': head_to_head,
            'overall_winner': overall_winner,
            'player1_rounds': player1_rounds,
            'player2_rounds': player2_rounds,
            'player1_courses': player1_courses,
            'player2_courses': player2_courses
        }

    @staticmethod
    def _get_player_stats(player_id: str, all_rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate stats for a player"""
        player_rounds = [r for r in all_rounds if any(s['player_id'] == player_id for s in r['scores'])]

        stats = {
            'total_rounds': 0,
            'average_score': 0,
            'best_score': None,
            'win_rate': 0
        }

        if not player_rounds:
            return stats

        scores = []
        wins = 0

        for round_data in player_rounds:
            player_score = Round.get_player_score_in_round(round_data, player_id)
            if player_score is not None:
                scores.append(player_score)

                # Check if won
                min_score = min(s['score'] for s in round_data['scores'])
                if player_score == min_score:
                    wins += 1

        if scores:
            stats['total_rounds'] = len(scores)
            stats['average_score'] = sum(scores) / len(scores)
            stats['best_score'] = min(scores)
            stats['win_rate'] = wins / len(scores)

        return stats

    @staticmethod
    def _get_head_to_head(player1_id: str, player2_id: str,
                          all_rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get head-to-head matchup data"""
        # Find rounds where both players competed
        matchup_rounds = []
        for round_data in all_rounds:
            player_ids = [s['player_id'] for s in round_data['scores']]
            if player1_id in player_ids and player2_id in player_ids:
                matchup_rounds.append(round_data)

        head_to_head = {
            'total_matchups': len(matchup_rounds),
            'player1_wins': 0,
            'player2_wins': 0,
            'ties': 0,
            'matchups': []
        }

        for round_data in matchup_rounds:
            player1_score = Round.get_player_score_in_round(round_data, player1_id)
            player2_score = Round.get_player_score_in_round(round_data, player2_id)

            winner = None
            if player1_score < player2_score:
                head_to_head['player1_wins'] += 1
                winner = player1_id
            elif player2_score < player1_score:
                head_to_head['player2_wins'] += 1
                winner = player2_id
            else:
                head_to_head['ties'] += 1

            head_to_head['matchups'].append({
                'date': round_data['date_played'],
                'course_name': round_data['course_name'],
                'player1_score': player1_score,
                'player2_score': player2_score,
                'winner': winner
            })

        # Sort by date (newest first)
        head_to_head['matchups'].sort(key=lambda m: m['date'], reverse=True)

        return head_to_head

    @staticmethod
    def _get_player_rounds(player_id: str, all_rounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all rounds for a player with dates and scores"""
        player_rounds = []

        for round_data in all_rounds:
            player_score = Round.get_player_score_in_round(round_data, player_id)
            if player_score is not None:
                player_rounds.append({
                    'date': round_data['date_played'],
                    'score': player_score,
                    'course': round_data['course_name']
                })

        # Sort by date
        player_rounds.sort(key=lambda r: r['date'])
        return player_rounds

    @staticmethod
    def _get_course_breakdown(player_id: str, all_rounds: List[Dict[str, Any]]) -> Dict[str, float]:
        """Get average score by course for a player"""
        course_scores = {}

        for round_data in all_rounds:
            player_score = Round.get_player_score_in_round(round_data, player_id)
            if player_score is not None:
                course_name = round_data['course_name']
                if course_name not in course_scores:
                    course_scores[course_name] = []
                course_scores[course_name].append(player_score)

        # Calculate averages
        course_averages = {
            course: sum(scores) / len(scores)
            for course, scores in course_scores.items()
        }

        return course_averages
