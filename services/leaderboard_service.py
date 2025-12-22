from models.player import Player
from models.round import Round
from typing import List, Dict, Any


class LeaderboardService:
    """Service for calculating player rankings and leaderboard statistics"""

    @staticmethod
    def get_player_rankings(sort_by: str = 'average') -> List[Dict[str, Any]]:
        """
        Get player rankings sorted by specified criteria

        Args:
            sort_by: Sort criteria ('average', 'wins', 'rounds')

        Returns:
            List of player ranking dictionaries
        """
        players = Player.get_all()
        rankings = []

        for player in players:
            stats = LeaderboardService._calculate_player_stats(player['id'])
            if stats['total_rounds'] > 0:  # Only include players with rounds
                rankings.append({
                    'player': player,
                    'stats': stats
                })

        # Sort based on criteria
        if sort_by == 'wins':
            rankings.sort(key=lambda x: x['stats']['wins'], reverse=True)
        elif sort_by == 'rounds':
            rankings.sort(key=lambda x: x['stats']['total_rounds'], reverse=True)
        else:  # average (default)
            rankings.sort(key=lambda x: x['stats']['average_score'])  # Lower is better

        return rankings

    @staticmethod
    def _calculate_player_stats(player_id: str) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for a player

        Args:
            player_id: Player ID

        Returns:
            Dictionary of player statistics
        """
        rounds = Round.get_by_player(player_id)

        stats = {
            'total_rounds': 0,
            'average_score': 0,
            'best_score': None,
            'worst_score': None,
            'wins': 0,
            'win_rate': 0
        }

        if not rounds:
            return stats

        scores = []
        wins = 0

        for round_data in rounds:
            # Get player's score in this round
            player_score = Round.get_player_score_in_round(round_data, player_id)
            if player_score is not None:
                scores.append(player_score)

                # Check if this was a win (lowest score in the round)
                min_score = min(s['score'] for s in round_data['scores'])
                if player_score == min_score:
                    wins += 1

        if scores:
            stats['total_rounds'] = len(scores)
            stats['average_score'] = sum(scores) / len(scores)
            stats['best_score'] = min(scores)
            stats['worst_score'] = max(scores)
            stats['wins'] = wins
            stats['win_rate'] = wins / len(scores) if len(scores) > 0 else 0

        return stats
