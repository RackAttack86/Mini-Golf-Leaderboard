from models.round import Round
from typing import Optional, Dict, Any, List


class TrendsService:
    """Service for calculating historical trends"""

    @staticmethod
    def get_player_trends(player_id: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get historical trends for a player

        Args:
            player_id: Player ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary of trend data
        """
        # Build filters
        filters = {'player_id': player_id}
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        rounds = Round.get_all(filters)

        # Sort by date (oldest first for trends)
        rounds.sort(key=lambda r: r['date_played'])

        trends = {
            'total_rounds': 0,
            'average_score': 0,
            'improvement': 0,
            'rounds': [],
            'dates': [],
            'scores': []
        }

        if not rounds:
            return trends

        scores = []
        for round_data in rounds:
            player_score = Round.get_player_score_in_round(round_data, player_id)
            if player_score is not None:
                scores.append(player_score)

                # Check if won
                min_score = min(s['score'] for s in round_data['scores'])
                won = (player_score == min_score)

                trends['rounds'].append({
                    'date': round_data['date_played'],
                    'course_name': round_data['course_name'],
                    'score': player_score,
                    'won': won
                })

                trends['dates'].append(round_data['date_played'])
                trends['scores'].append(player_score)

        if scores:
            trends['total_rounds'] = len(scores)
            trends['average_score'] = sum(scores) / len(scores)

            # Calculate improvement (compare first 3 rounds to last 3 rounds)
            if len(scores) >= 6:
                first_avg = sum(scores[:3]) / 3
                last_avg = sum(scores[-3:]) / 3
                trends['improvement'] = first_avg - last_avg  # Positive means improvement

        return trends

    @staticmethod
    def get_overall_trends(start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get overall trends across all players

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary of overall trend data
        """
        # Build filters
        filters = {}
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        rounds = Round.get_all(filters if filters else None)

        trends = {
            'total_rounds': len(rounds),
            'total_players': 0,
            'average_score': 0
        }

        if not rounds:
            return trends

        # Count unique players and calculate average
        player_ids = set()
        all_scores = []

        for round_data in rounds:
            for score_data in round_data['scores']:
                player_ids.add(score_data['player_id'])
                all_scores.append(score_data['score'])

        trends['total_players'] = len(player_ids)
        if all_scores:
            trends['average_score'] = sum(all_scores) / len(all_scores)

        return trends
