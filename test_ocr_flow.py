#!/usr/bin/env python3
"""
End-to-end test for OCR scorecard upload flow
Tests: OCR extraction, course matching, player matching, data validation
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.ocr_service import WalkaboutOCRService
from models.database import init_database
from models.course import Course
from models.player import Player
from config import Config

def test_ocr_extraction(image_path):
    """Test OCR extraction on a scorecard image"""
    print(f"\n{'='*60}")
    print(f"Testing OCR Extraction")
    print(f"{'='*60}")
    print(f"Image: {image_path}")

    if not Path(image_path).exists():
        print(f"[FAIL] Image not found: {image_path}")
        return None

    print("\nRunning OCR extraction...")
    result = WalkaboutOCRService.extract_scorecard_data(str(image_path))

    print(f"\nSuccess: {result['success']}")
    print(f"Confidence: {result['confidence']:.1%}")

    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    # Show raw OCR text for debugging
    if result.get('raw_text'):
        print(f"\nRaw OCR Text (first 500 chars):")
        print(f"  {result['raw_text'][:500]}")

    # Show extracted data even if not fully successful
    data = result['data']
    print(f"\nExtracted Data:")
    print(f"  Course Name: {data.get('course_name', 'NOT FOUND')}")
    print(f"  Player Username: {data.get('player_username', 'NOT FOUND')}")
    print(f"  Start Time: {data.get('start_time', 'NOT FOUND')}")
    print(f"  Total Score: {data.get('total_score', 'NOT FOUND')}")

    hole_scores = data.get('hole_scores', [])
    if hole_scores:
        print(f"\n  Hole Scores ({len(hole_scores)}/18 extracted):")
        for i in range(0, len(hole_scores), 6):
            holes_line = "    "
            for j in range(i, min(i+6, len(hole_scores))):
                holes_line += f"H{j+1:2d}:{hole_scores[j]:2d}  "
            print(holes_line)

        if len(hole_scores) == 18:
            calculated_total = sum(hole_scores)
            print(f"\n  Calculated Total: {calculated_total}")
            if data.get('total_score') and calculated_total != data['total_score']:
                print(f"  [WARNING] Mismatch with OCR total: {data['total_score']}")
    else:
        print(f"\n  Hole Scores: NONE EXTRACTED")

    return result

def test_course_matching(ocr_course_name):
    """Test course fuzzy matching"""
    print(f"\n{'='*60}")
    print(f"Testing Course Matching")
    print(f"{'='*60}")
    print(f"OCR Course Name: '{ocr_course_name}'")

    courses = Course.get_all()
    print(f"\nTotal courses in database: {len(courses)}")

    matched_id, confidence, suggestions = WalkaboutOCRService.find_matching_course(
        ocr_course_name,
        courses
    )

    if matched_id:
        matched_course = next((c for c in courses if c['id'] == matched_id), None)
        print(f"\n[MATCH FOUND] {matched_course['name']} ({confidence}% confidence)")
    else:
        print(f"\n[NO MATCH] Confidence too low")

    print(f"\nTop 5 Suggestions:")
    for course, score in suggestions[:5]:
        marker = " <-- MATCHED" if course['id'] == matched_id else ""
        print(f"  {score:3d}% - {course['name']}{marker}")

    return matched_id, confidence

def test_player_matching(meta_quest_username):
    """Test player matching by Meta Quest username"""
    print(f"\n{'='*60}")
    print(f"Testing Player Matching")
    print(f"{'='*60}")
    print(f"Meta Quest Username: '{meta_quest_username}'")

    if not meta_quest_username:
        print("[SKIP] No username provided")
        return None

    player = Player.get_by_meta_quest_username(meta_quest_username)

    if player:
        print(f"\n[MATCH FOUND]")
        print(f"  Player Name: {player['name']}")
        print(f"  Player ID: {player['id']}")
        print(f"  Meta Quest Username: {player.get('meta_quest_username', 'N/A')}")
    else:
        print(f"\n[NO MATCH] No player with this Meta Quest username")
        print(f"\nAvailable players:")
        all_players = Player.get_all()
        for p in all_players:
            meta = p.get('meta_quest_username', 'Not set')
            print(f"  - {p['name']} (Meta Quest: {meta})")

    return player

def test_validation(ocr_result):
    """Test data validation"""
    print(f"\n{'='*60}")
    print(f"Testing Data Validation")
    print(f"{'='*60}")

    validation_passed = True

    # Check course name
    if not ocr_result['data'].get('course_name'):
        print("[FAIL] Missing course name")
        validation_passed = False
    else:
        print("[PASS] Course name extracted")

    # Check start time
    if not ocr_result['data'].get('start_time'):
        print("[WARN] Missing start time (duplicate detection disabled)")
    else:
        print("[PASS] Start time extracted")

    # Check hole scores
    hole_scores = ocr_result['data'].get('hole_scores') or []
    if len(hole_scores) == 18:
        print("[PASS] All 18 hole scores extracted")
    elif len(hole_scores) > 0:
        print(f"[WARN] Only {len(hole_scores)}/18 hole scores extracted (manual entry needed)")
    else:
        print("[FAIL] No hole scores extracted")
        validation_passed = False

    # Check score validity
    if hole_scores:
        invalid_scores = [s for s in hole_scores if s < 1 or s > 15]
        if invalid_scores:
            print(f"[WARN] Some scores out of range 1-15: {invalid_scores}")
        else:
            print("[PASS] All scores in valid range")

    # Check total score
    if ocr_result['data'].get('total_score'):
        total = ocr_result['data']['total_score']
        if 18 <= total <= 200:
            print(f"[PASS] Total score reasonable: {total}")
        else:
            print(f"[WARN] Total score unusual: {total}")

    print(f"\nOverall Validation: {'PASSED' if validation_passed else 'NEEDS REVIEW'}")
    return validation_passed

def main():
    """Run end-to-end OCR flow test"""
    print("\n" + "="*60)
    print("OCR UPLOAD FLOW - END TO END TEST")
    print("="*60)

    # Initialize database
    print("\nInitializing database...")
    init_database(Config.DATABASE_PATH)
    print("[OK] Database initialized")

    # Test image path
    test_image = "data/round_pictures/mars.jpg"

    if not Path(test_image).exists():
        print(f"\n[ERROR] Test image not found: {test_image}")
        print("\nAvailable test images:")
        for img in Path("data/round_pictures").glob("*.jpg"):
            print(f"  - {img}")
        return

    # Step 1: OCR Extraction
    ocr_result = test_ocr_extraction(test_image)
    if not ocr_result:
        print("\n[FATAL] OCR extraction returned no result")
        return

    # Step 2: Course Matching (even if OCR not fully successful)
    course_name = ocr_result['data'].get('course_name')
    if course_name:
        test_course_matching(course_name)
    else:
        print("\n[SKIP] Course matching - no course name extracted")

    # Step 3: Player Matching
    player_username = ocr_result['data'].get('player_username')
    if player_username:
        test_player_matching(player_username)
    else:
        print("\n[SKIP] Player matching - no username extracted")

    # Step 4: Data Validation
    test_validation(ocr_result)

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"OCR Confidence: {ocr_result['confidence']:.1%}")
    print(f"Course: {ocr_result['data'].get('course_name', 'NOT FOUND')}")
    print(f"Player: {ocr_result['data'].get('player_username', 'NOT FOUND')}")
    hole_count = len(ocr_result['data'].get('hole_scores') or [])
    print(f"Holes Extracted: {hole_count}/18")

    if ocr_result['confidence'] >= 0.70:
        print("\n[READY] Data ready for review screen")
    else:
        print("\n[NEEDS WORK] Confidence below threshold (70%)")

    print()

if __name__ == "__main__":
    main()
