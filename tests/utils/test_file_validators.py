import pytest
import io
from werkzeug.datastructures import FileStorage
from utils.file_validators import validate_image_file, sanitize_filename


class TestValidateImageFile:
    """Test image file validation"""

    def test_valid_png_file(self):
        """Test valid PNG file passes validation"""
        # Create a valid PNG file header
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        file = FileStorage(
            stream=io.BytesIO(png_header + b'\x00' * 100),
            filename='test.png',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is True
        assert error == ""

    def test_valid_jpeg_file(self):
        """Test valid JPEG file passes validation"""
        # Create a valid JPEG file header
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        file = FileStorage(
            stream=io.BytesIO(jpeg_header + b'\x00' * 100),
            filename='test.jpg',
            content_type='image/jpeg'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is True
        assert error == ""

    def test_valid_gif_file(self):
        """Test valid GIF file passes validation"""
        # Create a valid GIF file header
        gif_header = b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
        file = FileStorage(
            stream=io.BytesIO(gif_header + b'\x00' * 100),
            filename='test.gif',
            content_type='image/gif'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is True
        assert error == ""

    def test_no_file_provided(self):
        """Test validation fails when no file provided"""
        is_valid, error = validate_image_file(None)
        assert is_valid is False
        assert error == "No file provided"

    def test_empty_filename(self):
        """Test validation fails when filename is empty"""
        file = FileStorage(
            stream=io.BytesIO(b'test'),
            filename='',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert error == "No file provided"

    def test_no_file_extension(self):
        """Test validation fails when file has no extension"""
        file = FileStorage(
            stream=io.BytesIO(b'test'),
            filename='testfile',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert error == "File must have an extension"

    def test_invalid_file_extension(self):
        """Test validation fails for invalid file extension"""
        file = FileStorage(
            stream=io.BytesIO(b'test'),
            filename='test.txt',
            content_type='text/plain'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert "File type not allowed" in error
        # Check that all allowed types are mentioned (order doesn't matter)
        assert "png" in error
        assert "jpg" in error or "jpeg" in error
        assert "gif" in error

    def test_file_too_large(self):
        """Test validation fails when file exceeds size limit"""
        # Create a file larger than 5MB
        large_content = b'\x00' * (6 * 1024 * 1024)  # 6MB
        file = FileStorage(
            stream=io.BytesIO(large_content),
            filename='test.png',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file, max_size=5 * 1024 * 1024)
        assert is_valid is False
        assert "File too large" in error
        assert "5.0MB" in error

    def test_empty_file(self):
        """Test validation fails for empty file"""
        file = FileStorage(
            stream=io.BytesIO(b''),
            filename='test.png',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert error == "File is empty"

    def test_file_content_mismatch(self):
        """Test validation fails when file content doesn't match extension"""
        # PNG extension but not PNG content
        file = FileStorage(
            stream=io.BytesIO(b'This is not an image'),
            filename='test.png',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert "doesn't match expected image format" in error

    def test_custom_max_size(self):
        """Test validation with custom max size"""
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        content = png_header + b'\x00' * 200
        file = FileStorage(
            stream=io.BytesIO(content),
            filename='test.png',
            content_type='image/png'
        )

        # Should pass with large max size
        is_valid, error = validate_image_file(file, max_size=1024)
        assert is_valid is True

        # Should fail with small max size
        file.stream.seek(0)
        is_valid, error = validate_image_file(file, max_size=100)
        assert is_valid is False
        assert "File too large" in error

    def test_case_insensitive_extensions(self):
        """Test that file extensions are case insensitive"""
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'

        # Test uppercase extension
        file = FileStorage(
            stream=io.BytesIO(png_header + b'\x00' * 100),
            filename='test.PNG',
            content_type='image/png'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is True
        assert error == ""

    def test_jpeg_alternative_extension(self):
        """Test that both .jpg and .jpeg extensions work"""
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'

        # Test .jpeg extension
        file = FileStorage(
            stream=io.BytesIO(jpeg_header + b'\x00' * 100),
            filename='test.jpeg',
            content_type='image/jpeg'
        )

        is_valid, error = validate_image_file(file)
        assert is_valid is True
        assert error == ""


class TestSanitizeFilename:
    """Test filename sanitization"""

    def test_simple_filename(self):
        """Test simple valid filename remains unchanged"""
        result = sanitize_filename('test.png')
        assert result == 'test.png'

    def test_filename_with_spaces(self):
        """Test spaces are replaced with underscores"""
        result = sanitize_filename('my test file.png')
        assert result == 'my_test_file.png'

    def test_filename_with_special_characters(self):
        """Test special characters are removed"""
        result = sanitize_filename('test@#$%file.png')
        assert 'test' in result
        assert 'file.png' in result
        # Special chars should be removed or replaced

    def test_filename_with_path_traversal(self):
        """Test path traversal attempts are neutralized"""
        result = sanitize_filename('../../../etc/passwd.png')
        assert '..' not in result
        assert '/' not in result
        assert 'passwd.png' in result

    def test_very_long_filename(self):
        """Test very long filenames are truncated"""
        long_name = 'a' * 150 + '.png'
        result = sanitize_filename(long_name)

        # Should be truncated to 100 chars + extension
        assert len(result) <= 104  # 100 + '.png'
        assert result.endswith('.png')

    def test_empty_filename(self):
        """Test empty filename gets default name"""
        result = sanitize_filename('')
        assert result == 'unnamed'

    def test_filename_with_only_special_chars(self):
        """Test filename with only special chars gets default name"""
        result = sanitize_filename('@#$%.png')
        assert 'unnamed' in result or result.endswith('.png')

    def test_custom_max_length(self):
        """Test custom maximum length"""
        long_name = 'a' * 50 + '.png'
        result = sanitize_filename(long_name, max_length=20)

        # Name should be truncated to 20 chars
        assert len(result.rsplit('.', 1)[0]) <= 20
        assert result.endswith('.png')

    def test_multiple_dots_in_filename(self):
        """Test filename with multiple dots"""
        result = sanitize_filename('my.test.file.png')
        assert result.endswith('.png')
        assert 'my' in result
        assert 'test' in result
        assert 'file' in result

    def test_unicode_filename(self):
        """Test unicode characters in filename"""
        result = sanitize_filename('tëst_fïlé.png')
        # Should handle unicode gracefully
        assert result.endswith('.png')
        assert len(result) > 0

    def test_filename_with_null_bytes(self):
        """Test filename with null bytes is sanitized"""
        result = sanitize_filename('test\x00file.png')
        assert '\x00' not in result
        assert result.endswith('.png')

    def test_preserve_extension(self):
        """Test that file extension is always preserved"""
        test_cases = [
            'test.png',
            'TEST.JPG',
            'my_file.gif',
            'document.jpeg'
        ]

        for filename in test_cases:
            result = sanitize_filename(filename)
            original_ext = filename.rsplit('.', 1)[1] if '.' in filename else ''
            if original_ext:
                assert result.endswith(original_ext) or result.endswith(original_ext.lower())


class TestFileValidatorsIntegration:
    """Integration tests for file validators"""

    def test_validate_and_sanitize_workflow(self):
        """Test typical workflow of validating and sanitizing a file"""
        # Create a valid file
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        file = FileStorage(
            stream=io.BytesIO(png_header + b'\x00' * 100),
            filename='My Test File!.png',
            content_type='image/png'
        )

        # Validate
        is_valid, error = validate_image_file(file)
        assert is_valid is True

        # Sanitize
        safe_filename = sanitize_filename(file.filename)
        assert safe_filename == 'My_Test_File.png'

    def test_reject_invalid_then_no_sanitize(self):
        """Test that invalid files are rejected before sanitization"""
        # Create an invalid file
        file = FileStorage(
            stream=io.BytesIO(b'not an image'),
            filename='test.txt',
            content_type='text/plain'
        )

        # Validate should fail
        is_valid, error = validate_image_file(file)
        assert is_valid is False
        assert error != ""

        # Would still sanitize filename if needed, but validation caught the issue
        safe_filename = sanitize_filename(file.filename)
        assert safe_filename == 'test.txt'
