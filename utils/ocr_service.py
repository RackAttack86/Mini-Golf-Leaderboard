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
            # PSM 3 = Fully automatic page segmentation, but no OSD (best for mixed layouts)
            # PSM 6 = Assume a single uniform block of text
            # PSM 11 = Sparse text. Find as much text as possible in no particular order
            custom_config = r'--oem 3 --psm 3'
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

        # Moderate brightness increase
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)

        # Moderate contrast increase (less aggressive than before)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.8)

        # Moderate sharpness increase
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)

        # Convert to grayscale
        image = image.convert('L')

        # Skip binarization - use grayscale directly
        # The aggressive binarization was causing character distortion

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
                        'FORE', 'LABYRINTH', 'TEMPLE', 'ATLANTIS', 'SACRED', 'TOURIST', 'TRAP',
                        'PIRATES', 'COVE', 'WILD', 'WEST', 'JUNGLE', 'SAFARI']

        # Course names are typically all caps or title case and appear early
        for i, line in enumerate(lines[:15]):
            line = line.strip()

            # Skip empty lines and common UI elements
            if not line or line.lower() in ['settings', 'friends', 'tutorial', 'resume game', 'main menu', 'mode', 'full', 'record']:
                continue

            # Remove common prefixes that OCR might add
            line = re.sub(r'^(Mode:|Record:|Full\s*\d+)', '', line, flags=re.IGNORECASE).strip()

            # Check if it contains known course words (case insensitive)
            if any(word in line.upper() for word in known_courses):
                # Look for the actual course name words in the line
                # Extract words that match known course keywords
                words = line.upper().split()
                course_words = [w for w in words if any(kw in w for kw in known_courses)]

                if course_words:
                    # Clean up and join course words
                    cleaned = ' '.join(course_words)
                    cleaned = re.sub(r'[^A-Z\s]', '', cleaned).strip()
                    if len(cleaned) > 5:
                        return cleaned, 0.85

            # Look for capitalized multi-word patterns (likely course names)
            if len(line) > 5 and line.isupper():
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
    def _correct_ocr_errors(text: str) -> str:
        """
        Correct common OCR character recognition errors

        Args:
            text: Raw OCR text

        Returns:
            Corrected text
        """
        # Common OCR mistakes in usernames and text
        corrections = {
            'S18': 'Sir',  # "Sir" often read as "S18"
            'S1r': 'Sir',
            'Slr': 'Sir',
            '0': 'O',      # Zero to letter O (context-dependent, be careful)
            'l': 'I',      # Lowercase L to uppercase I in all-caps context
        }

        corrected = text
        for wrong, right in corrections.items():
            corrected = corrected.replace(wrong, right)

        return corrected

    @staticmethod
    def _extract_player_username(raw_text: str) -> Tuple[Optional[str], float]:
        """
        Extract Meta Quest player username

        The username appears in the "PlayerName" field at the bottom of the scorecard.
        Format: "PlayerName" followed by the username (e.g., "Sir_Chops")

        Returns:
            Tuple of (username, confidence)
        """
        # Apply OCR error corrections first
        corrected_text = WalkaboutOCRService._correct_ocr_errors(raw_text)

        # Look for PlayerName label followed by the username
        # More flexible pattern to catch variations
        player_pattern = r'(?:PlayerName|PLAYERNAME|Player[\s_]*Name|Name)[:\s]*([A-Za-z][A-Za-z0-9_\-]{2,20})'
        match = re.search(player_pattern, corrected_text, re.IGNORECASE | re.MULTILINE)
        if match:
            username = match.group(1).strip()
            # Filter out common false positives
            if username.lower() not in ['start', 'current', 'version', 'active', 'modifiers', 'mode', 'full', 'record']:
                return username, 0.9

        # Also try on original text in case corrections broke something
        match = re.search(player_pattern, raw_text, re.IGNORECASE | re.MULTILINE)
        if match:
            username = match.group(1).strip()
            if username.lower() not in ['start', 'current', 'version', 'active', 'modifiers', 'mode', 'full', 'record']:
                return username, 0.85

        # Look specifically for patterns like "Sir_Chops" (common username format)
        # Username with underscore pattern - try corrected text first
        underscore_pattern = r'\b([A-Z][a-z]+_[A-Za-z]+)\b'
        match = re.search(underscore_pattern, corrected_text)
        if match:
            return match.group(1), 0.85

        match = re.search(underscore_pattern, raw_text)
        if match:
            return match.group(1), 0.8

        # Look for "S18_CHOPS" or similar patterns and correct them
        s18_pattern = r'\bS18_([A-Za-z]+)\b'
        match = re.search(s18_pattern, raw_text, re.IGNORECASE)
        if match:
            username = f"Sir_{match.group(1)}"
            return username, 0.75

        # Fallback: look for username-like patterns near bottom of text
        lines = corrected_text.split('\n')
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
        # Replace newlines with spaces to handle multi-line datetime patterns
        # Sometimes OCR splits date and time across lines
        normalized_text = raw_text.replace('\n', ' ').replace('\r', ' ')

        # Look for "Start:" or "Start" label followed by datetime
        start_label_pattern = r'Start[:\s]+(.{0,150})'
        start_match = re.search(start_label_pattern, normalized_text, re.IGNORECASE)
        search_text = start_match.group(1) if start_match else normalized_text

        # Look for date/time patterns
        # Format: MM/DD/YYYY HH:MM:SS AM/PM
        # Try multiple patterns to catch OCR errors
        datetime_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))',  # 12/30/2025 3:15:28 AM
            r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})',  # Without AM/PM
            r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2})',  # ISO format
            # More tolerant patterns for OCR errors
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)',  # Allow - instead of /
        ]

        for pattern in datetime_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                datetime_str = match.group(1).strip()
                # Clean up OCR errors in datetime string
                datetime_str = datetime_str.replace('-', '/')  # Normalize separators

                try:
                    # Parse the datetime - try multiple formats
                    formats = [
                        '%m/%d/%Y %I:%M:%S %p',  # 12/30/2025 3:15:28 AM
                        '%m/%d/%Y %H:%M:%S',     # 12/30/2025 15:15:28
                        '%d/%m/%Y %I:%M:%S %p',  # 30/12/2025 3:15:28 AM
                        '%d/%m/%Y %H:%M:%S',     # 30/12/2025 15:15:28
                        '%Y/%m/%d %H:%M:%S',     # 2025/12/30 15:15:28
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

        # Fallback: Extract date and time separately (they may be far apart in OCR text)
        # Find date pattern
        date_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
        time_pattern = r'(\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))'

        date_match = re.search(date_pattern, search_text)
        time_match = re.search(time_pattern, search_text, re.IGNORECASE)

        if date_match and time_match:
            # Combine date and time
            combined = f"{date_match.group(1)} {time_match.group(1)}"
            try:
                dt = datetime.strptime(combined, '%m/%d/%Y %I:%M:%S %p')
                iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                return iso_timestamp, 0.75  # Lower confidence since they were separated
            except ValueError:
                # Try alternative date format
                try:
                    dt = datetime.strptime(combined, '%d/%m/%Y %I:%M:%S %p')
                    iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    return iso_timestamp, 0.7
                except:
                    pass

        # Fallback: Look for any datetime-like pattern in entire text
        match = re.search(datetime_patterns[0], normalized_text, re.IGNORECASE)
        if match:
            datetime_str = match.group(1).strip()
            try:
                dt = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p')
                iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                return iso_timestamp, 0.7
            except:
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

        # First, try to correct common OCR errors in score lines
        # Common mistakes when reading small numbers: O→0, B→8, S→5, I→1, l→1, etc.
        def correct_score_line(text: str) -> str:
            """Correct common OCR errors in score tables"""
            corrections = {
                'O': '0',
                'o': '0',
                'B': '8',
                'S': '5',
                's': '5',
                'I': '1',
                'l': '1',
                'Z': '2',
                'G': '6',
                'T': '7',
            }
            corrected = text
            for wrong, right in corrections.items():
                corrected = corrected.replace(wrong, right)
            return corrected

        # Find lines containing "SCORE" or "Score"
        for i, line in enumerate(lines):
            if re.search(r'\b(SCORE|Score|Sco)\b', line, re.IGNORECASE):
                # Extract numbers from this line and next 3 lines
                # Sometimes the scores are on the next line
                search_lines = lines[i:min(i+4, len(lines))]
                search_text = ' '.join(search_lines)

                # Try with score correction first
                corrected_text = correct_score_line(search_text)

                # Extract all single-digit and double-digit numbers
                # Use word boundaries to avoid splitting multi-digit numbers
                numbers = re.findall(r'\b(\d{1,2})\b', corrected_text)

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
