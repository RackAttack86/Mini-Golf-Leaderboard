"""Achievement system for players"""
from typing import Any, Dict, List

from models.course import Course
from models.round import Round
from services.achievements_data import ACHIEVEMENTS


class AchievementService:
    """Service for managing player achievements"""

    @staticmethod
    def get_achievement_score(player_id: str) -> int:
        """
        Get total achievement points for a player

        Args:
            player_id: Player ID

        Returns:
            Total achievement points
        """
        achievements = AchievementService.get_player_achievements(player_id)
        return achievements['total_points']

    @staticmethod
    def get_player_achievements(player_id: str) -> Dict[str, Any]:
        """
        Calculate and return all achievements for a player

        Args:
            player_id: Player ID

        Returns:
            Dict with earned and available achievements
        """
        all_rounds = Round.get_by_player(player_id)

        # Filter out solo rounds (only count rounds with 2+ players)
        rounds = [r for r in all_rounds if len(r['scores']) >= 2]

        earned_achievements = []
        progress = {}
        total_points = 0

        # Calculate stats
        total_rounds = len(rounds)
        wins = AchievementService._count_wins(rounds, player_id)
        courses_played = AchievementService._count_unique_courses(rounds)
        courses_won = AchievementService._count_courses_won(rounds, player_id)
        total_active_courses = len(Course.get_all(active_only=True))
        players_played_with = AchievementService._count_unique_players(rounds, player_id)
        max_party_size = AchievementService._get_max_party_size(rounds)
        current_win_streak = AchievementService._get_current_win_streak(rounds, player_id)
        max_win_streak = AchievementService._get_max_win_streak(rounds, player_id)

        # Check Participation Achievements
        for achievement_id in ['first_round', 'getting_started', 'regular', 'veteran', 'century_club']:
            achievement = ACHIEVEMENTS[achievement_id]
            if total_rounds >= achievement['requirement']:
                earned_achievements.append({
                    'id': achievement_id,
                    **achievement,
                    'earned': True
                })
                total_points += achievement['points']
            else:
                progress[achievement_id] = {
                    'current': total_rounds,
                    'required': achievement['requirement']
                }

        # Check Victory Achievements
        for achievement_id in ['first_victory', 'hat_trick', 'champion', 'dominator', 'legend']:
            achievement = ACHIEVEMENTS[achievement_id]
            if wins >= achievement['requirement']:
                earned_achievements.append({
                    'id': achievement_id,
                    **achievement,
                    'earned': True
                })
                total_points += achievement['points']
            else:
                progress[achievement_id] = {
                    'current': wins,
                    'required': achievement['requirement']
                }

        # Check Exploration Achievements
        for achievement_id in ['explorer', 'world_traveler', 'course_master']:
            achievement = ACHIEVEMENTS[achievement_id]
            if courses_played >= achievement['requirement']:
                earned_achievements.append({
                    'id': achievement_id,
                    **achievement,
                    'earned': True
                })
                total_points += achievement['points']
            else:
                progress[achievement_id] = {
                    'current': courses_played,
                    'required': achievement['requirement']
                }

        # Check Globe Trotter (play every course)
        achievement = ACHIEVEMENTS['globe_trotter']
        if total_active_courses > 0 and courses_played >= total_active_courses:
            earned_achievements.append({
                'id': 'globe_trotter',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['globe_trotter'] = {
                'current': courses_played,
                'required': total_active_courses
            }

        # Check Standard Explorer (play all non-hard courses)
        hard_courses_played = AchievementService._count_hard_courses_played(rounds)
        nonhard_courses_played = AchievementService._count_nonhard_courses_played(rounds)
        total_hard_courses = AchievementService._count_total_hard_courses()
        total_nonhard_courses = AchievementService._count_total_nonhard_courses()

        achievement = ACHIEVEMENTS['standard_explorer']
        if total_nonhard_courses > 0 and nonhard_courses_played >= total_nonhard_courses:
            earned_achievements.append({
                'id': 'standard_explorer',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['standard_explorer'] = {
                'current': nonhard_courses_played,
                'required': total_nonhard_courses
            }

        # Check Hardcore Champion (play all hard courses)
        achievement = ACHIEVEMENTS['hardcore_champion']
        if total_hard_courses > 0 and hard_courses_played >= total_hard_courses:
            earned_achievements.append({
                'id': 'hardcore_champion',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['hardcore_champion'] = {
                'current': hard_courses_played,
                'required': total_hard_courses
            }

        # Check Course Conqueror (win on every course)
        achievement = ACHIEVEMENTS['course_conqueror']
        if total_active_courses > 0 and courses_won >= total_active_courses:
            earned_achievements.append({
                'id': 'course_conqueror',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['course_conqueror'] = {
                'current': courses_won,
                'required': total_active_courses
            }

        # Check Social Achievements
        achievement = ACHIEVEMENTS['social_butterfly']
        if players_played_with >= achievement['requirement']:
            earned_achievements.append({
                'id': 'social_butterfly',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['social_butterfly'] = {
                'current': players_played_with,
                'required': achievement['requirement']
            }

        achievement = ACHIEVEMENTS['party_animal']
        if max_party_size >= 4:
            earned_achievements.append({
                'id': 'party_animal',
                **achievement,
                'earned': True
            })
            total_points += achievement['points']
        else:
            progress['party_animal'] = {
                'current': max_party_size,
                'required': 4
            }

        # Check Streak Achievements
        for achievement_id in ['hot_streak', 'unstoppable']:
            achievement = ACHIEVEMENTS[achievement_id]
            if max_win_streak >= achievement['requirement']:
                earned_achievements.append({
                    'id': achievement_id,
                    **achievement,
                    'earned': True
                })
                total_points += achievement['points']
            else:
                progress[achievement_id] = {
                    'current': max_win_streak,
                    'required': achievement['requirement']
                }

        return {
            'earned': earned_achievements,
            'progress': progress,
            'total_points': total_points,
            'stats': {
                'total_rounds': total_rounds,
                'wins': wins,
                'courses_played': courses_played,
                'courses_won': courses_won,
                'players_played_with': players_played_with,
                'current_win_streak': current_win_streak,
                'max_win_streak': max_win_streak
            }
        }

    @staticmethod
    def _count_wins(rounds: List[Dict[str, Any]], player_id: str) -> int:
        """Count number of wins for a player"""
        wins = 0
        for round_data in rounds:
            if round_data['scores']:
                winner = min(round_data['scores'], key=lambda x: x['score'])
                if winner['player_id'] == player_id:
                    wins += 1
        return wins

    @staticmethod
    def _count_unique_courses(rounds: List[Dict[str, Any]]) -> int:
        """Count unique courses played"""
        courses = set()
        for round_data in rounds:
            courses.add(round_data['course_id'])
        return len(courses)

    @staticmethod
    def _count_courses_won(rounds: List[Dict[str, Any]], player_id: str) -> int:
        """Count unique courses where player has won at least once"""
        won_courses = set()
        for round_data in rounds:
            if round_data['scores']:
                winner = min(round_data['scores'], key=lambda x: x['score'])
                if winner['player_id'] == player_id:
                    won_courses.add(round_data['course_id'])
        return len(won_courses)

    @staticmethod
    def _count_unique_players(rounds: List[Dict[str, Any]], player_id: str) -> int:
        """Count unique players played with (excluding self)"""
        players = set()
        for round_data in rounds:
            for score in round_data['scores']:
                if score['player_id'] != player_id:
                    players.add(score['player_id'])
        return len(players)

    @staticmethod
    def _get_max_party_size(rounds: List[Dict[str, Any]]) -> int:
        """Get maximum number of players in a single round"""
        if not rounds:
            return 0
        return max(len(round_data['scores']) for round_data in rounds)

    @staticmethod
    def _get_current_win_streak(rounds: List[Dict[str, Any]], player_id: str) -> int:
        """Get current winning streak"""
        if not rounds:
            return 0

        # Sort by date (most recent first)
        sorted_rounds = sorted(rounds, key=lambda x: x['date_played'], reverse=True)

        streak = 0
        for round_data in sorted_rounds:
            if round_data['scores']:
                winner = min(round_data['scores'], key=lambda x: x['score'])
                if winner['player_id'] == player_id:
                    streak += 1
                else:
                    break

        return streak

    @staticmethod
    def _get_max_win_streak(rounds: List[Dict[str, Any]], player_id: str) -> int:
        """Get maximum winning streak"""
        if not rounds:
            return 0

        # Sort by date (oldest first)
        sorted_rounds = sorted(rounds, key=lambda x: x['date_played'])

        max_streak = 0
        current_streak = 0

        for round_data in sorted_rounds:
            if round_data['scores']:
                winner = min(round_data['scores'], key=lambda x: x['score'])
                if winner['player_id'] == player_id:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0

        return max_streak

    @staticmethod
    def _count_hard_courses_played(rounds: List[Dict[str, Any]]) -> int:
        """Count unique hard courses played"""
        hard_courses = set()
        for round_data in rounds:
            course = Course.get_by_id(round_data['course_id'])
            if course and '(HARD)' in course['name']:
                hard_courses.add(round_data['course_id'])
        return len(hard_courses)

    @staticmethod
    def _count_nonhard_courses_played(rounds: List[Dict[str, Any]]) -> int:
        """Count unique non-hard courses played"""
        nonhard_courses = set()
        for round_data in rounds:
            course = Course.get_by_id(round_data['course_id'])
            if course and '(HARD)' not in course['name']:
                nonhard_courses.add(round_data['course_id'])
        return len(nonhard_courses)

    @staticmethod
    def _count_total_hard_courses() -> int:
        """Count total active hard courses"""
        courses = Course.get_all(active_only=True)
        return len([c for c in courses if '(HARD)' in c['name']])

    @staticmethod
    def _count_total_nonhard_courses() -> int:
        """Count total active non-hard courses"""
        courses = Course.get_all(active_only=True)
        return len([c for c in courses if '(HARD)' not in c['name']])
