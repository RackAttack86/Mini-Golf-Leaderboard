import os
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

    # Verify file is actually an image (content-based validation using magic numbers)
    file_header = file.read(512)
    file.seek(0)  # Reset again

    # Detect image type from magic numbers (file signatures)
    image_type = _detect_image_type(file_header)
    if image_type not in ['png', 'jpeg', 'gif']:
        return False, "File content doesn't match expected image format"

    return True, ""


def _detect_image_type(header: bytes) -> str:
    """
    Detect image type from file header (magic numbers)

    Args:
        header: First bytes of the file

    Returns:
        Image type string ('png', 'jpeg', 'gif') or empty string if not recognized
    """
    if len(header) < 12:
        return ""

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'

    # JPEG: FF D8 FF
    if header[:3] == b'\xff\xd8\xff':
        return 'jpeg'

    # GIF: GIF87a or GIF89a
    if header[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'

    return ""


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
