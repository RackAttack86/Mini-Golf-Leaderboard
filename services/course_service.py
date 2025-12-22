from models.course import Course
from models.round import Round
from typing import List, Dict, Any


class CourseService:
    """Service for calculating course statistics"""

    @staticmethod
    def get_course_stats() -> List[Dict[str, Any]]:
        """
        Get statistics for all courses

        Returns:
            List of course statistics dictionaries
        """
        courses = Course.get_all()
        course_stats = []

        for course in courses:
            stats = CourseService._calculate_course_stats(course['id'])
            if stats['times_played'] > 0:  # Only include courses that have been played
                course_stats.append({
                    'course': course,
                    'stats': stats
                })

        # Sort by average score (harder courses first)
        course_stats.sort(key=lambda x: x['stats']['average_score'], reverse=True)

        # Add difficulty ranking
        for i, stat in enumerate(course_stats):
            stat['stats']['difficulty_rank'] = i + 1

        return course_stats

    @staticmethod
    def _calculate_course_stats(course_id: str) -> Dict[str, Any]:
        """
        Calculate statistics for a specific course

        Args:
            course_id: Course ID

        Returns:
            Dictionary of course statistics
        """
        rounds = Round.get_by_course(course_id)

        stats = {
            'times_played': len(rounds),
            'average_score': 0,
            'best_score': None,
            'best_score_player': None,
            'worst_score': None,
            'worst_score_player': None
        }

        if not rounds:
            return stats

        all_scores = []
        score_to_player = {}  # Map score to player name

        for round_data in rounds:
            for score_data in round_data['scores']:
                score = score_data['score']
                player_name = score_data['player_name']
                all_scores.append(score)

                # Track player for this score
                if score not in score_to_player:
                    score_to_player[score] = player_name

        if all_scores:
            stats['average_score'] = sum(all_scores) / len(all_scores)
            stats['best_score'] = min(all_scores)
            stats['worst_score'] = max(all_scores)
            stats['best_score_player'] = score_to_player[stats['best_score']]
            stats['worst_score_player'] = score_to_player[stats['worst_score']]

        return stats
