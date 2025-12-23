from rembg import remove
from PIL import Image
import os
import sys

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Define the trophy images
trophies = ['masters.png', 'usopen.png', 'rydercup.png']
input_dir = 'static/images/trophies'

for trophy in trophies:
    input_path = os.path.join(input_dir, trophy)

    # Check if file exists
    if not os.path.exists(input_path):
        print(f"Warning: {input_path} not found, skipping...")
        continue

    print(f"Processing {trophy}...")

    # Open the image
    with open(input_path, 'rb') as input_file:
        input_data = input_file.read()

    # Remove background
    output_data = remove(input_data)

    # Save the processed image
    with open(input_path, 'wb') as output_file:
        output_file.write(output_data)

    print(f"Done - {trophy} background removed!")

print("\nAll trophy images processed successfully!")
