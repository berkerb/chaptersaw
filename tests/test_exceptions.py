"""Tests for the exceptions module."""

import pytest

from chaptersaw.exceptions import (
    ChapterExtractionError,
    ChaptersawError,
    FFmpegNotFoundError,
    UnsupportedFormatError,
)


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_base_exception_is_exception(self) -> None:
        """Test that ChaptersawError inherits from Exception."""
        assert issubclass(ChaptersawError, Exception)

    def test_ffmpeg_not_found_inherits_base(self) -> None:
        """Test FFmpegNotFoundError inherits from base."""
        assert issubclass(FFmpegNotFoundError, ChaptersawError)
        assert issubclass(FFmpegNotFoundError, Exception)

    def test_chapter_extraction_error_inherits_base(self) -> None:
        """Test ChapterExtractionError inherits from base."""
        assert issubclass(ChapterExtractionError, ChaptersawError)
        assert issubclass(ChapterExtractionError, Exception)

    def test_unsupported_format_error_inherits_base(self) -> None:
        """Test UnsupportedFormatError inherits from base."""
        assert issubclass(UnsupportedFormatError, ChaptersawError)
        assert issubclass(UnsupportedFormatError, Exception)


class TestExceptionCatching:
    """Tests for catching exceptions."""

    def test_catch_all_with_base_exception(self) -> None:
        """Test that base exception catches all subclasses."""
        exceptions = [
            FFmpegNotFoundError("FFmpeg not found"),
            ChapterExtractionError("Extraction failed"),
            UnsupportedFormatError("Bad format"),
        ]

        for exc in exceptions:
            with pytest.raises(ChaptersawError):
                raise exc

    def test_catch_specific_exception(self) -> None:
        """Test that specific exceptions can be caught individually."""
        with pytest.raises(FFmpegNotFoundError):
            raise FFmpegNotFoundError("FFmpeg not found")

        with pytest.raises(ChapterExtractionError):
            raise ChapterExtractionError("Extraction failed")

        with pytest.raises(UnsupportedFormatError):
            raise UnsupportedFormatError("Unsupported format")

    def test_exception_message_preserved(self) -> None:
        """Test that exception messages are preserved."""
        msg = "Custom error message"

        exc = ChaptersawError(msg)
        assert str(exc) == msg

        exc = FFmpegNotFoundError(msg)
        assert str(exc) == msg

        exc = ChapterExtractionError(msg)
        assert str(exc) == msg

        exc = UnsupportedFormatError(msg)
        assert str(exc) == msg


class TestExceptionImports:
    """Tests for exception imports from package root."""

    def test_import_from_package_root(self) -> None:
        """Test that exceptions can be imported from package root."""
        from chaptersaw import (
            ChapterExtractionError,
            ChaptersawError,
            FFmpegNotFoundError,
            UnsupportedFormatError,
        )

        # Verify they're the same classes
        from chaptersaw.exceptions import (
            ChapterExtractionError as CE,
        )
        from chaptersaw.exceptions import (
            ChaptersawError as CSE,
        )
        from chaptersaw.exceptions import (
            FFmpegNotFoundError as FNF,
        )
        from chaptersaw.exceptions import (
            UnsupportedFormatError as UFE,
        )

        assert ChapterExtractionError is CE
        assert FFmpegNotFoundError is FNF
        assert ChaptersawError is CSE
        assert UnsupportedFormatError is UFE
