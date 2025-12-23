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

                # Calculate position
                sorted_scores = sorted([s['score'] for s in round_data['scores']])
                position = sorted_scores.index(player_score) + 1
                total_players = len(round_data['scores'])

                trends['rounds'].append({
                    'date': round_data['date_played'],
                    'course_name': round_data['course_name'],
                    'score': player_score,
                    'won': won,
                    'position': position,
                    'total_players': total_players
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

    @staticmethod
    def get_all_players_trends(start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trend data for all players for comparison

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with player trends for comparison charts
        """
        from models.player import Player

        # Build filters
        filters = {}
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        rounds = Round.get_all(filters if filters else None)
        players = Player.get_all()

        # Organize data by player
        player_data = {}
        course_data = {}
        win_counts = {}

        for player in players:
            player_data[player['id']] = {
                'name': player['name'],
                'color': player.get('favorite_color', '#2e7d32'),
                'rounds': []
            }
            win_counts[player['id']] = 0

        # Process rounds
        for round_info in rounds:
            # Track course difficulty
            course_name = round_info['course_name']
            if course_name not in course_data:
                course_data[course_name] = []

            # Find winner
            if round_info['scores']:
                min_score = min(s['score'] for s in round_info['scores'])

                for score in round_info['scores']:
                    player_id = score['player_id']
                    if player_id in player_data:
                        player_data[player_id]['rounds'].append({
                            'date': round_info['date_played'],
                            'score': score['score'],
                            'course': course_name,
                            'won': score['score'] == min_score
                        })

                        if score['score'] == min_score:
                            win_counts[player_id] += 1

                        course_data[course_name].append(score['score'])

        # Calculate course averages
        course_averages = {
            course: sum(scores) / len(scores)
            for course, scores in course_data.items()
            if scores
        }

        return {
            'players': player_data,
            'courses': course_averages,
            'win_counts': win_counts
        }
