"""Achievement system for players"""
from typing import Any, Dict, List

from models.course import Course
from models.round import Round


class AchievementService:
    """Service for managing player achievements"""

    # Define all achievements
    ACHIEVEMENTS = {
        # Rounds Played Achievements
        'first_round': {
            'name': 'First Round',
            'description': 'Play your first round',
            'icon': 'bi-play-circle',
            'category': 'Participation',
            'requirement': 1,
            'color': '#17a2b8',
            'points': 10
        },
        'getting_started': {
            'name': 'Getting Started',
            'description': 'Play 5 rounds',
            'icon': 'bi-flag',
            'category': 'Participation',
            'requirement': 5,
            'color': '#28a745',
            'points': 20
        },
        'regular': {
            'name': 'Regular',
            'description': 'Play 10 rounds',
            'icon': 'bi-star',
            'category': 'Participation',
            'requirement': 10,
            'color': '#ffc107',
            'points': 30
        },
        'veteran': {
            'name': 'Veteran',
            'description': 'Play 25 rounds',
            'icon': 'bi-award',
            'category': 'Participation',
            'requirement': 25,
            'color': '#fd7e14',
            'points': 50
        },
        'century_club': {
            'name': 'Century Club',
            'description': 'Play 100 rounds',
            'icon': 'bi-trophy',
            'category': 'Participation',
            'requirement': 100,
            'color': '#6f42c1',
            'points': 100
        },

        # Winning Achievements
        'first_victory': {
            'name': 'First Victory',
            'description': 'Win your first round',
            'icon': 'bi-trophy-fill',
            'category': 'Victory',
            'requirement': 1,
            'color': '#ffd700',
            'points': 10
        },
        'hat_trick': {
            'name': 'Hat Trick',
            'description': 'Win 3 rounds',
            'icon': 'bi-gem',
            'category': 'Victory',
            'requirement': 3,
            'color': '#28a745',
            'points': 30
        },
        'champion': {
            'name': 'Champion',
            'description': 'Win 10 rounds',
            'icon': 'bi-award-fill',
            'category': 'Victory',
            'requirement': 10,
            'color': '#dc3545',
            'points': 60
        },
        'dominator': {
            'name': 'Dominator',
            'description': 'Win 25 rounds',
            'icon': 'bi-star-fill',
            'category': 'Victory',
            'requirement': 25,
            'color': '#6f42c1',
            'points': 100
        },
        'legend': {
            'name': 'Legend',
            'description': 'Win 50 rounds',
            'icon': 'bi-lightning-fill',
            'category': 'Victory',
            'requirement': 50,
            'color': '#ff0000',
            'points': 150
        },

        # Course Exploration Achievements
        'explorer': {
            'name': 'Explorer',
            'description': 'Play on 3 different courses',
            'icon': 'bi-compass',
            'category': 'Exploration',
            'requirement': 3,
            'color': '#17a2b8',
            'points': 20
        },
        'world_traveler': {
            'name': 'World Traveler',
            'description': 'Play on 5 different courses',
            'icon': 'bi-globe',
            'category': 'Exploration',
            'requirement': 5,
            'color': '#20c997',
            'points': 40
        },
        'course_master': {
            'name': 'Course Master',
            'description': 'Play on 10 different courses',
            'icon': 'bi-map',
            'category': 'Exploration',
            'requirement': 10,
            'color': '#6610f2',
            'points': 80
        },
        'globe_trotter': {
            'name': 'Globe Trotter',
            'description': 'Play on every course',
            'icon': 'bi-globe2',
            'category': 'Exploration',
            'requirement': 'all',
            'color': '#8b5cf6',
            'points': 80
        },
        'standard_explorer': {
            'name': 'Standard Explorer',
            'description': 'Play on all non-hard courses',
            'icon': 'bi-compass-fill',
            'category': 'Exploration',
            'requirement': 'all_standard',
            'color': '#3b82f6',
            'points': 150
        },
        'hardcore_champion': {
            'name': 'Hardcore Champion',
            'description': 'Play on all hard courses',
            'icon': 'bi-fire',
            'category': 'Exploration',
            'requirement': 'all_hard',
            'color': '#dc2626',
            'points': 200
        },
        'course_conqueror': {
            'name': 'Course Conqueror',
            'description': 'Win on every course',
            'icon': 'bi-shield-fill-check',
            'category': 'Mastery',
            'requirement': 'all',
            'color': '#7c2d12',
            'points': 500
        },

        # Social Achievements
        'social_butterfly': {
            'name': 'Social Butterfly',
            'description': 'Play with 5 different players',
            'icon': 'bi-people-fill',
            'category': 'Social',
            'requirement': 5,
            'color': '#e83e8c',
            'points': 40
        },
        'party_animal': {
            'name': 'Party Animal',
            'description': 'Play in a round with 4 or more players',
            'icon': 'bi-emoji-smile-fill',
            'category': 'Social',
            'requirement': 1,
            'color': '#ff6b6b',
            'points': 10
        },

        # Winning Streak Achievements
        'hot_streak': {
            'name': 'Hot Streak',
            'description': 'Win 3 rounds in a row',
            'icon': 'bi-fire',
            'category': 'Streak',
            'requirement': 3,
            'color': '#ff6b35',
            'points': 70
        },
        'unstoppable': {
            'name': 'Unstoppable',
            'description': 'Win 5 rounds in a row',
            'icon': 'bi-rocket-takeoff-fill',
            'category': 'Streak',
            'requirement': 5,
            'color': '#d90429',
            'points': 150
        }
    }

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
            achievement = AchievementService.ACHIEVEMENTS[achievement_id]
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
            achievement = AchievementService.ACHIEVEMENTS[achievement_id]
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
            achievement = AchievementService.ACHIEVEMENTS[achievement_id]
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
        achievement = AchievementService.ACHIEVEMENTS['globe_trotter']
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

        achievement = AchievementService.ACHIEVEMENTS['standard_explorer']
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
        achievement = AchievementService.ACHIEVEMENTS['hardcore_champion']
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
        achievement = AchievementService.ACHIEVEMENTS['course_conqueror']
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
        achievement = AchievementService.ACHIEVEMENTS['social_butterfly']
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

        achievement = AchievementService.ACHIEVEMENTS['party_animal']
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
            achievement = AchievementService.ACHIEVEMENTS[achievement_id]
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
