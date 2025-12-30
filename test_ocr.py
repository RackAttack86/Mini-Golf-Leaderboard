"""Quick test of OCR service"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.ocr_service import WalkaboutOCRService
import json

# Test with sample image
image_path = 'data/round_pictures/605667758_25923012437302661_9070130609374273700_n.jpg'

print("Testing OCR extraction...")
print(f"Image: {image_path}\n")

result = WalkaboutOCRService.extract_scorecard_data(image_path)

print("=" * 70)
print("OCR EXTRACTION RESULTS")
print("=" * 70)
print(f"Success: {result['success']}")
print(f"Confidence: {result['confidence']:.2%}\n")

print("EXTRACTED DATA:")
print(f"  Course Name: {result['data'].get('course_name')}")
print(f"  Player Username: {result['data'].get('player_username')}")
print(f"  Start Time: {result['data'].get('start_time')}")
print(f"  Hole Scores: {result['data'].get('hole_scores')}")
print(f"  Total Score: {result['data'].get('total_score')}\n")

if result['errors']:
    print("ERRORS:")
    for error in result['errors']:
        print(f"  - {error}")
    print()

print("RAW OCR TEXT:")
print("-" * 70)
print(result['raw_text'])
print("-" * 70)
