# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-format support: MP4, M4V, AVI, WebM, TS, M2TS in addition to MKV
- `SUPPORTED_FORMATS` constant for programmatic format checking
- `is_supported_format()` and `validate_format()` helper functions
- `UnsupportedFormatError` exception for invalid file formats
- Base `ChaptersawError` exception class for catching all package errors
- Regex pattern matching for chapter filtering (`--regex` flag)
- Exclude mode for inverse filtering (`--exclude` flag)
- Chapter listing command (`--list-chapters`)
- Progress bar with rich library for visual feedback
- Parallel processing for faster extraction of multiple files (`--parallel`)
- Integration tests for end-to-end testing
- Track listing command (`--list-tracks`) to show audio, video, and subtitle tracks
- Set default track feature (`--set-default`) with `--audio` and `--subtitle` language options
- Auto-chapter generation for merged files (`--auto-chapters`)
- Custom chapter format for auto-generated chapters (`--merge-chapter-format`)
- Filename parsing with guessit library (`--parse-filename`)
- `Track` model for representing audio/video/subtitle tracks
- `parser` module with `MediaInfo` dataclass and `parse_filename()` function

### Changed
- **BREAKING**: Renamed project from `mkv-chapter-extractor` to `chaptersaw`
- **BREAKING**: Renamed base exception from `MKVChapterExtractorError` to `ChaptersawError`
- Extracted exceptions to dedicated `exceptions.py` module for cleaner imports
- Removed unused `ffmpeg-python` dependency (using subprocess directly)

## [0.1.0] - 2025-01-01

### Added
- Initial release
- Extract chapters from MKV files based on keyword matching
- Merge mode: combine matched chapters into a single output file
- Separate mode: create individual output files per input
- Case-sensitive and case-insensitive keyword matching
- Glob pattern support for input files
- Dry-run mode to preview operations
- Two-phase processing: scan all files before extraction
- Error handling for missing files and missing chapter info
- Command-line interface with argparse
- Full type annotations (py.typed)
- Comprehensive test suite

[Unreleased]: https://github.com/berkerbozdag/chaptersaw/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/berkerbozdag/chaptersaw/releases/tag/v0.1.0
