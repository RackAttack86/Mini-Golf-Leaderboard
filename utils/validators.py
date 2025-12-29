from datetime import datetime
from typing import Tuple, List, Optional
import re
import html

# Validation Constants
# Score limits: Allow reasonable range for mini golf scores
# Typical mini golf courses have 18 holes with par 2-4 per hole (total par ~36-72)
# Max score accounts for worst-case scenario of hitting max strokes per hole
# Min score allows for hole-in-ones and eagles (significantly under par)
MIN_SCORE = -50  # Allows for exceptional performance (multiple holes-in-one)
MAX_SCORE = 500  # Allows for very poor performance across all holes

# Par limits: Reasonable range for total course par
# Typical mini golf courses: 18 holes * 2-4 par = 36-72 total par
# Extended courses with more holes could have higher par
MAX_PAR = 500  # Allows for large courses with many holes

# Holes limit: Maximum number of holes per course
# Most mini golf courses have 9-18 holes, but some larger venues may have more
MAX_HOLES = 100  # Allows for very large multi-course facilities

# Name length limits
MAX_NAME_LENGTH = 100  # Reasonable limit for player/course names
MAX_EMAIL_LENGTH = 100  # Standard email length limit


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML from user input to prevent XSS attacks

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML entities escaped
    """
    if not text:
        return text

    # Escape HTML entities - this is sufficient to prevent XSS
    # Converts < > & " ' to their HTML entity equivalents
    sanitized = html.escape(text.strip())

    return sanitized


def validate_player_name(name: str, existing_players: List[dict], exclude_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate player name

    Args:
        name: Player name to validate
        existing_players: List of existing players
        exclude_id: Player ID to exclude from duplicate check (for updates)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name too long (max {MAX_NAME_LENGTH} characters)"

    # Check for duplicates
    for player in existing_players:
        if exclude_id and player['id'] == exclude_id:
            continue
        if player['name'].lower() == name.lower():
            return False, "Player name already exists"

    return True, ""


def validate_course_name(name: str, existing_courses: List[dict], exclude_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate course name

    Args:
        name: Course name to validate
        existing_courses: List of existing courses
        exclude_id: Course ID to exclude from duplicate check (for updates)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name too long (max {MAX_NAME_LENGTH} characters)"

    # Check for duplicates
    for course in existing_courses:
        if exclude_id and course['id'] == exclude_id:
            continue
        if course['name'].lower() == name.lower():
            return False, "Course name already exists"

    return True, ""


def validate_score(score: any) -> Tuple[bool, str]:
    """
    Validate golf score (can be negative for scores relative to par)

    Args:
        score: Score to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        score_int = int(score)
        if score_int < MIN_SCORE:
            return False, f"Score unreasonably low (min {MIN_SCORE})"
        if score_int > MAX_SCORE:
            return False, f"Score unreasonably high (max {MAX_SCORE})"
        return True, ""
    except (ValueError, TypeError):
        return False, "Score must be a number"


def validate_holes(holes: any) -> Tuple[bool, str]:
    """
    Validate number of holes

    Args:
        holes: Number of holes to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if holes is None or holes == '':
        return True, ""  # Optional field

    try:
        holes_int = int(holes)
        if holes_int <= 0:
            return False, "Number of holes must be positive"
        if holes_int > MAX_HOLES:
            return False, f"Number of holes unreasonably high (max {MAX_HOLES})"
        return True, ""
    except (ValueError, TypeError):
        return False, "Number of holes must be a number"


def validate_par(par: any) -> Tuple[bool, str]:
    """
    Validate par score

    Args:
        par: Par to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if par is None or par == '':
        return True, ""  # Optional field

    try:
        par_int = int(par)
        if par_int <= 0:
            return False, "Par must be positive"
        if par_int > MAX_PAR:
            return False, f"Par unreasonably high (max {MAX_PAR})"
        return True, ""
    except (ValueError, TypeError):
        return False, "Par must be a number"


def validate_date(date_str: str) -> Tuple[bool, str]:
    """
    Validate date string

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return False, "Date cannot be empty"

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Check if date is not in the future
        if date > datetime.now().date():
            return False, "Date cannot be in the future"

        return True, ""
    except ValueError:
        return False, "Invalid date format (use YYYY-MM-DD)"


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address using RFC 5322 simplified pattern

    Args:
        email: Email to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or email.strip() == '':
        return True, ""  # Optional field

    email = email.strip()

    if len(email) > MAX_EMAIL_LENGTH:
        return False, f"Email too long (max {MAX_EMAIL_LENGTH} characters)"

    # RFC 5322 simplified email validation pattern
    # Matches: user@domain.com, user.name@sub.domain.com, user+tag@domain.co.uk
    # Rejects: @., user@., user@domain., @domain.com, user@@domain.com
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    # Additional checks for edge cases
    if email.count('@') != 1:
        return False, "Invalid email format"

    local, domain = email.split('@')

    # Validate local part (before @)
    if not local or local.startswith('.') or local.endswith('.') or '..' in local:
        return False, "Invalid email format"

    # Validate domain part (after @)
    if not domain or domain.startswith('.') or domain.endswith('.') or '..' in domain:
        return False, "Invalid email format"

    return True, ""
