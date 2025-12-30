"""Chaptersaw - Extract and merge chapters from video files.

A tool for extracting specific chapters from video files (MKV, MP4, AVI, WebM,
and more) based on chapter title keywords, with support for merging multiple files.
"""

from chaptersaw.exceptions import (
    ChaptersawError,
    ChapterExtractionError,
    FFmpegNotFoundError,
    UnsupportedFormatError,
)
from chaptersaw.extractor import (
    SUPPORTED_FORMATS,
    ChapterExtractor,
    extract_chapters,
    extract_chapters_to_separate_files,
    is_supported_format,
    validate_format,
)
from chaptersaw.models import Chapter, ExtractionResult

__version__ = "0.1.0"
__all__ = [
    # Main classes
    "ChapterExtractor",
    "Chapter",
    "ExtractionResult",
    # Convenience functions
    "extract_chapters",
    "extract_chapters_to_separate_files",
    # Format utilities
    "SUPPORTED_FORMATS",
    "is_supported_format",
    "validate_format",
    # Exceptions
    "ChaptersawError",
    "FFmpegNotFoundError",
    "ChapterExtractionError",
    "UnsupportedFormatError",
]
