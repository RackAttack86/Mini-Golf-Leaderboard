import os
import imghdr
from typing import Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage


def validate_image_file(file: FileStorage, max_size: int = 5 * 1024 * 1024) -> Tuple[bool, str]:
    """
    Validate uploaded image file

    Args:
        file: Uploaded file from request.files
        max_size: Maximum file size in bytes (default 5MB)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "No file provided"

    # Check file extension
    filename = secure_filename(file.filename)
    if '.' not in filename:
        return False, "File must have an extension"

    ext = filename.rsplit('.', 1)[1].lower()
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"

    # Check file size by reading
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File too large. Maximum size: {max_mb:.1f}MB"

    if file_size == 0:
        return False, "File is empty"

    # Verify file is actually an image (content-based validation)
    file_header = file.read(512)
    file.seek(0)  # Reset again

    # Try to detect image type from content
    image_type = imghdr.what(None, h=file_header)
    if image_type not in ['png', 'jpeg', 'gif']:
        return False, "File content doesn't match expected image format"

    return True, ""


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize uploaded filename

    Args:
        filename: Original filename
        max_length: Maximum filename length (default 100)

    Returns:
        Sanitized filename
    """
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)

    # Additional sanitization: limit length
    if not safe_name:
        return "unnamed"

    name, ext = os.path.splitext(safe_name)

    # If only extension remains after sanitization, use default name
    if not name and ext:
        return f"unnamed{ext}"

    # Check if the result is just an extension name without the dot
    # (e.g., "@#$%.png" becomes "png" after secure_filename)
    common_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx'}
    if not ext and name.lower() in common_extensions:
        return f"unnamed.{name}"

    if len(name) > max_length:
        name = name[:max_length]

    return f"{name}{ext}"
