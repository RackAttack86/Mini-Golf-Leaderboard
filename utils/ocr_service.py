"""OCR service for extracting scorecard data from Walkabout Mini Golf screenshots"""
import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from fuzzywuzzy import fuzz
from config import Config

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = Config.OCR_TESSERACT_PATH


class WalkaboutOCRService:
    """Extract scorecard data from Walkabout Mini Golf screenshots"""

    @staticmethod
    def extract_scorecard_data(image_path: str) -> Dict[str, Any]:
        """
        Extract all data from scorecard image

        Args:
            image_path: Path to the scorecard image

        Returns:
            Dictionary with:
            - success: bool
            - confidence: float (0.0-1.0)
            - data: dict with course_name, player_username, start_time, hole_scores, total_score
            - errors: list of error messages
            - raw_text: str (for debugging)
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            preprocessed = WalkaboutOCRService._preprocess_image(image)

            # Extract raw text with better Tesseract configuration
            # PSM 6 = Assume a single uniform block of text
            # PSM 11 = Sparse text. Find as much text as possible in no particular order
            custom_config = r'--oem 3 --psm 6'
            raw_text = pytesseract.image_to_string(preprocessed, config=custom_config)

            # Extract individual fields
            course_name, course_confidence = WalkaboutOCRService._extract_course_name(raw_text, image)
            player_username, player_confidence = WalkaboutOCRService._extract_player_username(raw_text)
            start_time, time_confidence = WalkaboutOCRService._extract_start_time(raw_text)
            hole_scores, scores_confidence = WalkaboutOCRService._extract_hole_scores(raw_text, image)
            total_score = sum(hole_scores) if hole_scores and len(hole_scores) == 18 else None

            # Calculate overall confidence
            confidences = [c for c in [course_confidence, player_confidence, time_confidence, scores_confidence] if c > 0]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Validate data
            errors = WalkaboutOCRService._validate_scorecard_data(
                course_name, player_username, start_time, hole_scores, total_score
            )

            return {
                'success': len(errors) == 0,
                'confidence': overall_confidence,
                'data': {
                    'course_name': course_name,
                    'player_username': player_username,
                    'start_time': start_time,
                    'hole_scores': hole_scores,
                    'total_score': total_score
                },
                'errors': errors,
                'raw_text': raw_text
            }

        except Exception as e:
            return {
                'success': False,
                'confidence': 0.0,
                'data': {},
                'errors': [f"OCR extraction failed: {str(e)}"],
                'raw_text': ''
            }

    @staticmethod
    def _preprocess_image(image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR accuracy

        Args:
            image: PIL Image object

        Returns:
            Preprocessed PIL Image
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Increase brightness slightly (helps with dark screenshots)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)

        # Increase contrast more aggressively
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)

        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        # Convert to grayscale
        image = image.convert('L')

        # Apply threshold to make text more distinct (binarization)
        # Convert to black and white based on threshold
        threshold = 150
        image = image.point(lambda x: 0 if x < threshold else 255, '1')
        image = image.convert('L')

        return image

    @staticmethod
    def _extract_course_name(raw_text: str, image: Image.Image) -> Tuple[Optional[str], float]:
        """
        Extract course name from scorecard

        The course name appears at the top center of the scorecard in large text.
        Common patterns: "MARS GARDENS", "Shangri La", etc.

        Returns:
            Tuple of (course_name, confidence)
        """
        # Look for course name patterns in the first few lines
        lines = raw_text.split('\n')

        # Known course name patterns
        known_courses = ['MARS', 'GARDEN', 'SHANGRI', 'LA', 'NEON', 'OLYMPUS', 'CASTLE',
                        'FORE', 'FORE', 'LABYRINTH', 'TEMPLE', 'ATLANTIS', 'SACRED']

        # Course names are typically all caps or title case and appear early
        for i, line in enumerate(lines[:15]):
            line = line.strip()

            # Skip empty lines and common UI elements
            if not line or line.lower() in ['settings', 'friends', 'tutorial', 'resume game', 'main menu', 'mode', 'full', 'record']:
                continue

            # Remove common prefixes that OCR might add
            line = re.sub(r'^(Mode:|Record:|Full\s*\d+)', '', line, flags=re.IGNORECASE).strip()

            # Look for capitalized multi-word patterns (likely course names)
            if len(line) > 5 and line.isupper():
                # Check if it contains known course words
                if any(word in line.upper() for word in known_courses):
                    # Clean up the line
                    cleaned = re.sub(r'[^A-Z\s]', '', line).strip()
                    if len(cleaned) > 5:
                        return cleaned, 0.9

                # If it's mostly letters and spaces, likely course name
                if re.match(r'^[A-Z\s]{6,30}$', line):
                    return line, 0.8

        # Fallback: Look for "MARS GARDENS" or similar patterns anywhere
        course_pattern = r'\b(MARS\s*GARDENS?|SHANGRI\s*LA|NEON\s*HEIGHTS?|MOUNT\s*OLYMPUS|ATLANTIS)\b'
        match = re.search(course_pattern, raw_text, re.IGNORECASE)
        if match:
            return match.group(1).upper(), 0.85

        return None, 0.0

    @staticmethod
    def _extract_player_username(raw_text: str) -> Tuple[Optional[str], float]:
        """
        Extract Meta Quest player username

        The username appears in the "PlayerName" field at the bottom of the scorecard.
        Format: "PlayerName" followed by the username (e.g., "Sir_Chops")

        Returns:
            Tuple of (username, confidence)
        """
        # Look for PlayerName label followed by the username
        # More flexible pattern to catch variations
        player_pattern = r'(?:PlayerName|PLAYERNAME|Player[\s_]*Name|Name)[:\s]*([A-Za-z][A-Za-z0-9_\-]{2,20})'
        match = re.search(player_pattern, raw_text, re.IGNORECASE | re.MULTILINE)
        if match:
            username = match.group(1).strip()
            # Filter out common false positives
            if username.lower() not in ['start', 'current', 'version', 'active', 'modifiers', 'mode', 'full', 'record']:
                return username, 0.9

        # Look specifically for patterns like "Sir_Chops" (common username format)
        # Username with underscore pattern
        underscore_pattern = r'\b([A-Z][a-z]+_[A-Za-z]+)\b'
        match = re.search(underscore_pattern, raw_text)
        if match:
            return match.group(1), 0.85

        # Fallback: look for username-like patterns near bottom of text
        lines = raw_text.split('\n')
        # Search bottom half of document
        for line in lines[len(lines)//2:]:
            # Look for alphanumeric with underscores
            username_pattern = r'\b([A-Za-z][A-Za-z0-9_]{3,20})\b'
            matches = re.findall(username_pattern, line)

            for match in matches:
                if '_' in match:
                    # Likely a username
                    if match.lower() not in ['settings', 'tutorial', 'playername']:
                        return match, 0.7

        return None, 0.0

    @staticmethod
    def _extract_start_time(raw_text: str) -> Tuple[Optional[str], float]:
        """
        Extract round start time

        Format: "12/30/2025 3:15:28 AM" or similar
        Located in the "Start" field at the bottom

        Returns:
            Tuple of (ISO-8601 timestamp string, confidence)
        """
        # Look for date/time patterns
        # Format: MM/DD/YYYY HH:MM:SS AM/PM
        # Try multiple patterns to catch OCR errors
        datetime_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))',  # 12/30/2025 3:15:28 AM
            r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})',  # Without AM/PM
            r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2})',  # ISO format
        ]

        for pattern in datetime_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                datetime_str = match.group(1).strip()
                try:
                    # Parse the datetime - try multiple formats
                    formats = [
                        '%m/%d/%Y %I:%M:%S %p',  # 12/30/2025 3:15:28 AM
                        '%m/%d/%Y %H:%M:%S',     # 12/30/2025 15:15:28
                        '%d/%m/%Y %I:%M:%S %p',  # 30/12/2025 3:15:28 AM
                        '%d/%m/%Y %H:%M:%S',     # 30/12/2025 15:15:28
                        '%Y-%m-%d %H:%M:%S',     # 2025-12-30 15:15:28
                    ]

                    for fmt in formats:
                        try:
                            dt = datetime.strptime(datetime_str, fmt)
                            # Convert to ISO-8601 format
                            iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                            return iso_timestamp, 0.9
                        except ValueError:
                            continue

                except Exception:
                    pass

        return None, 0.0

    @staticmethod
    def _extract_hole_scores(raw_text: str, image: Image.Image) -> Tuple[Optional[List[int]], float]:
        """
        Extract 18 hole scores from the score table

        The scores appear in a row labeled "SCORE" with 18 individual hole scores.

        Returns:
            Tuple of (list of 18 scores, confidence)
        """
        # Look for the SCORE row followed by numbers
        lines = raw_text.split('\n')

        scores = []
        confidence = 0.0

        # Find lines containing "SCORE" or "Score"
        for i, line in enumerate(lines):
            if re.search(r'\b(SCORE|Score)\b', line):
                # Extract numbers from this line and next 3 lines
                # Sometimes the scores are on the next line
                search_lines = lines[i:min(i+4, len(lines))]
                search_text = ' '.join(search_lines)

                # Extract all single-digit and double-digit numbers
                # Use word boundaries to avoid splitting multi-digit numbers
                numbers = re.findall(r'\b(\d{1,2})\b', search_text)

                # Filter to reasonable golf scores (1-10, allowing up to 15 for very bad holes)
                valid_scores = []
                for n in numbers:
                    score = int(n)
                    if 1 <= score <= 15:
                        valid_scores.append(score)

                # If we found exactly 18 scores, high confidence
                if len(valid_scores) == 18:
                    scores = valid_scores
                    confidence = 0.95
                    break
                # If we found 17 or 19, try to adjust
                elif 16 <= len(valid_scores) <= 20:
                    # Take the first 18
                    if len(valid_scores) >= 18:
                        scores = valid_scores[:18]
                        confidence = 0.75
                        break

        # Fallback: Look for hole numbers (1-18) followed by scores
        if not scores:
            # Try to find pattern like "1 2 3 4 5 ... 18" followed by scores
            hole_pattern = r'(?:Hole|HOLE).*?(?:\d+\s+){17}\d+'
            match = re.search(hole_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                # Get text after the hole numbers
                remaining_text = raw_text[match.end():]
                numbers = re.findall(r'\b(\d{1,2})\b', remaining_text[:200])
                valid_scores = [int(n) for n in numbers if 1 <= int(n) <= 15]
                if len(valid_scores) >= 18:
                    scores = valid_scores[:18]
                    confidence = 0.7

        # Last fallback: try to find any sequence of 18 valid scores
        if not scores:
            all_numbers = re.findall(r'\b(\d{1,2})\b', raw_text)
            valid_numbers = [int(n) for n in all_numbers if 1 <= int(n) <= 10]

            # Look for sequence of 18 valid scores
            for i in range(len(valid_numbers) - 17):
                potential_scores = valid_numbers[i:i+18]
                # Check if total is reasonable (typically 40-90 for mini golf)
                total = sum(potential_scores)
                if 35 <= total <= 120:
                    scores = potential_scores
                    confidence = 0.5
                    break

        if len(scores) == 18:
            return scores, confidence
        elif len(scores) > 0:
            # Partial scores found
            return scores, confidence * 0.5

        return None, 0.0

    @staticmethod
    def _validate_scorecard_data(course_name: Optional[str], player_username: Optional[str],
                                  start_time: Optional[str], hole_scores: Optional[List[int]],
                                  total_score: Optional[int]) -> List[str]:
        """
        Validate extracted scorecard data

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not course_name:
            errors.append("Could not extract course name")

        if not player_username:
            errors.append("Could not extract player username")

        if not start_time:
            errors.append("Could not extract start time")

        if not hole_scores:
            errors.append("Could not extract hole scores")
        elif len(hole_scores) != 18:
            errors.append(f"Expected 18 hole scores, found {len(hole_scores)}")

        if total_score is not None and (total_score < 18 or total_score > 180):
            errors.append(f"Total score {total_score} is out of reasonable range (18-180)")

        return errors

    @staticmethod
    def find_matching_course(ocr_course_name: str, available_courses: List[Dict[str, Any]]) -> Tuple[Optional[str], int, List[Tuple[Dict[str, Any], int]]]:
        """
        Find best matching course using fuzzy string matching

        Args:
            ocr_course_name: Course name extracted from OCR
            available_courses: List of course dictionaries from database

        Returns:
            Tuple of (course_id or None, match_score, top_5_suggestions)
            Each suggestion is (course_dict, match_score)
        """
        if not ocr_course_name or not available_courses:
            return None, 0, []

        # Calculate fuzzy match scores for all courses
        matches = []
        for course in available_courses:
            course_name = course['name']
            # Calculate ratio (0-100)
            ratio = fuzz.ratio(ocr_course_name.lower(), course_name.lower())
            # Also try partial ratio for substring matches
            partial = fuzz.partial_ratio(ocr_course_name.lower(), course_name.lower())
            # Use the higher score
            score = max(ratio, partial)
            matches.append((course, score))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Get top 5 suggestions
        top_5 = matches[:5]

        # If best match is above threshold, return it
        if matches and matches[0][1] >= Config.FUZZY_MATCH_THRESHOLD:
            return matches[0][0]['id'], matches[0][1], top_5

        # Otherwise return None but provide suggestions
        return None, matches[0][1] if matches else 0, top_5
