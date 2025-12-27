"""Achievement definitions and configurations"""

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
