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

            # Extract raw text
            raw_text = pytesseract.image_to_string(preprocessed)

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

        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)

        # Convert to grayscale
        image = image.convert('L')

        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=3))

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

        # Course names are typically all caps or title case and appear early
        for i, line in enumerate(lines[:10]):
            line = line.strip()

            # Skip empty lines and common UI elements
            if not line or line.lower() in ['settings', 'friends', 'tutorial', 'resume game', 'main menu']:
                continue

            # Look for capitalized multi-word patterns (likely course names)
            if len(line) > 5 and (line.isupper() or line.istitle()):
                # Check if it contains course-like words or is standalone capitalized text
                if any(word in line.upper() for word in ['GARDEN', 'COURSE', 'GOLF', 'MINI', 'SHANGRI', 'MARS', 'NEON']):
                    return line, 0.9

                # If it's the largest text in first 5 lines, likely the course name
                if i < 5 and len(line) > 8:
                    return line, 0.7

        # Fallback: try pattern matching
        course_pattern = r'([A-Z][a-zA-Z\s]{5,30})'
        match = re.search(course_pattern, raw_text)
        if match:
            return match.group(1).strip(), 0.5

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
        player_pattern = r'(?:PlayerName|PLAYERNAME|Player\s*Name)[:\s]*([A-Za-z0-9_\-]+)'
        match = re.search(player_pattern, raw_text, re.IGNORECASE)
        if match:
            username = match.group(1).strip()
            # Filter out common false positives
            if username.lower() not in ['start', 'current', 'version', 'active', 'modifiers']:
                return username, 0.9

        # Fallback: look for username-like patterns (alphanumeric with underscores)
        username_pattern = r'\b([A-Za-z][A-Za-z0-9_]{3,20})\b'
        matches = re.findall(username_pattern, raw_text)

        # Filter matches that look like usernames
        for match in matches:
            if '_' in match or match[0].isupper():
                # Avoid common UI words
                if match.lower() not in ['settings', 'tutorial', 'playername', 'current', 'version', 'active']:
                    return match, 0.6

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
        datetime_pattern = r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?)'
        match = re.search(datetime_pattern, raw_text, re.IGNORECASE)

        if match:
            datetime_str = match.group(1).strip()
            try:
                # Parse the datetime
                # Try with AM/PM first
                for fmt in ['%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %H:%M:%S', '%d/%m/%Y %I:%M:%S %p', '%d/%m/%Y %H:%M:%S']:
                    try:
                        dt = datetime.strptime(datetime_str, fmt)
                        # Convert to ISO-8601 format
                        iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                        return iso_timestamp, 0.9
                    except ValueError:
                        continue

                return None, 0.0

            except Exception:
                return None, 0.0

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

        # Find lines containing "SCORE"
        for i, line in enumerate(lines):
            if 'SCORE' in line.upper() or 'Score' in line:
                # Extract numbers from this line and nearby lines
                # Look in current line and next 2 lines
                search_text = ' '.join(lines[i:i+3])

                # Extract all single-digit and double-digit numbers
                numbers = re.findall(r'\b(\d{1,2})\b', search_text)

                # Filter to reasonable golf scores (1-10)
                valid_scores = [int(n) for n in numbers if 1 <= int(n) <= 10]

                # If we found exactly 18 scores, high confidence
                if len(valid_scores) == 18:
                    scores = valid_scores
                    confidence = 0.95
                    break
                # If we found close to 18, lower confidence
                elif 15 <= len(valid_scores) <= 20:
                    scores = valid_scores[:18] if len(valid_scores) >= 18 else valid_scores
                    confidence = 0.6
                    break

        # Fallback: try to find 18 consecutive numbers in reasonable range
        if not scores:
            all_numbers = re.findall(r'\b(\d{1,2})\b', raw_text)
            valid_numbers = [int(n) for n in all_numbers if 1 <= int(n) <= 10]

            # Look for sequence of 18 valid scores
            for i in range(len(valid_numbers) - 17):
                potential_scores = valid_numbers[i:i+18]
                # Check if total is reasonable (typically 45-90 for mini golf)
                total = sum(potential_scores)
                if 30 <= total <= 100:
                    scores = potential_scores
                    confidence = 0.4
                    break

        if len(scores) == 18:
            return scores, confidence
        elif scores:
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
