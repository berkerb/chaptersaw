"""Custom exceptions for Chaptersaw."""


class ChaptersawError(Exception):
    """Base exception for all chaptersaw errors.

    This can be used to catch any exception raised by the package:

        try:
            extractor.extract_and_merge(...)
        except ChaptersawError as e:
            print(f"Extraction failed: {e}")
    """


class FFmpegNotFoundError(ChaptersawError):
    """Raised when FFmpeg or FFprobe executables are not found.

    This typically occurs when:
    - FFmpeg is not installed on the system
    - FFmpeg is not in the system PATH
    - A custom path was provided but the executable doesn't exist
    """


class ChapterExtractionError(ChaptersawError):
    """Raised when chapter extraction fails.

    This can occur due to:
    - Input file not found
    - No chapters found in the input file
    - No chapters matching the filter criteria
    - FFmpeg/FFprobe command failures
    - Invalid input file format
    """


class UnsupportedFormatError(ChaptersawError):
    """Raised when input file format is not supported.

    Supported formats include: MKV, MP4, M4V, AVI, WebM, TS, M2TS.
    """
