"""Tests for the extractor module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chaptersaw.exceptions import (
    ChapterExtractionError,
    FFmpegNotFoundError,
    UnsupportedFormatError,
)
from chaptersaw.extractor import (
    SUPPORTED_FORMATS,
    ChapterExtractor,
    is_supported_format,
    resolve_input_files,
    validate_format,
)
from chaptersaw.models import Chapter


class TestChapterExtractor:
    """Tests for the ChapterExtractor class."""

    @pytest.fixture
    def mock_ffmpeg_validation(self) -> MagicMock:
        """Mock the ffmpeg/ffprobe validation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield mock_run

    @pytest.fixture
    def extractor(self, mock_ffmpeg_validation: MagicMock) -> ChapterExtractor:
        """Create an extractor instance with mocked dependencies."""
        return ChapterExtractor()

    def test_init_validates_dependencies(self) -> None:
        """Test that initialization validates ffmpeg/ffprobe."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(FFmpegNotFoundError):
                ChapterExtractor()

    def test_init_with_custom_paths(self) -> None:
        """Test initialization with custom ffmpeg paths."""
        with patch("subprocess.run"):
            extractor = ChapterExtractor(
                ffmpeg_path="/custom/ffmpeg",
                ffprobe_path="/custom/ffprobe",
            )
            assert extractor.ffmpeg_path == Path("/custom/ffmpeg")
            assert extractor.ffprobe_path == Path("/custom/ffprobe")

    def test_get_chapters_file_not_found(
        self, extractor: ChapterExtractor
    ) -> None:
        """Test get_chapters raises error for missing file."""
        with pytest.raises(ChapterExtractionError, match="not found"):
            extractor.get_chapters("nonexistent.mkv")

    def test_get_chapters_success(
        self, extractor: ChapterExtractor, tmp_path: Path
    ) -> None:
        """Test successful chapter extraction."""
        # Create a dummy file
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        # Mock ffprobe output
        chapter_data = {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "120.000000",
                    "tags": {"title": "Episode 1"},
                },
                {
                    "start_time": "120.000000",
                    "end_time": "240.000000",
                    "tags": {"title": "Credits"},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(chapter_data),
                returncode=0,
            )
            chapters = extractor.get_chapters(test_file)

        assert len(chapters) == 2
        assert chapters[0].title == "Episode 1"
        assert chapters[0].start_time == 0.0
        assert chapters[0].end_time == 120.0
        assert chapters[1].title == "Credits"

    def test_get_chapters_no_title_tag(
        self, extractor: ChapterExtractor, tmp_path: Path
    ) -> None:
        """Test chapters without title tags get default names."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        chapter_data = {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "60.000000",
                    "tags": {},
                },
            ]
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(chapter_data),
                returncode=0,
            )
            chapters = extractor.get_chapters(test_file)

        assert len(chapters) == 1
        assert chapters[0].title == "Chapter 1"

    def test_filter_chapters_by_keyword(
        self, extractor: ChapterExtractor
    ) -> None:
        """Test keyword filtering of chapters."""
        chapters = [
            Chapter("Episode 1", 0.0, 100.0),
            Chapter("Opening", 100.0, 120.0),
            Chapter("Episode 2", 120.0, 220.0),
            Chapter("Credits", 220.0, 240.0),
        ]

        filtered = extractor.filter_chapters_by_keyword(chapters, "Episode")
        assert len(filtered) == 2
        assert all("Episode" in ch.title for ch in filtered)

    def test_filter_chapters_by_keyword_case_insensitive(
        self, extractor: ChapterExtractor
    ) -> None:
        """Test case-insensitive keyword filtering."""
        chapters = [
            Chapter("EPISODE 1", 0.0, 100.0),
            Chapter("episode 2", 100.0, 200.0),
            Chapter("Other", 200.0, 300.0),
        ]

        filtered = extractor.filter_chapters_by_keyword(chapters, "episode")
        assert len(filtered) == 2

    def test_filter_chapters_by_keyword_case_sensitive(
        self, extractor: ChapterExtractor
    ) -> None:
        """Test case-sensitive keyword filtering."""
        chapters = [
            Chapter("EPISODE 1", 0.0, 100.0),
            Chapter("episode 2", 100.0, 200.0),
            Chapter("Episode 3", 200.0, 300.0),
        ]

        filtered = extractor.filter_chapters_by_keyword(
            chapters, "Episode", case_sensitive=True
        )
        assert len(filtered) == 1
        assert filtered[0].title == "Episode 3"

    def test_filter_chapters_by_predicate(
        self, extractor: ChapterExtractor
    ) -> None:
        """Test custom predicate filtering."""
        chapters = [
            Chapter("Short", 0.0, 30.0),
            Chapter("Long", 30.0, 330.0),
            Chapter("Medium", 330.0, 430.0),
        ]

        # Filter chapters longer than 60 seconds
        filtered = extractor.filter_chapters_by_predicate(
            chapters, lambda ch: ch.duration > 60
        )
        assert len(filtered) == 2
        assert filtered[0].title == "Long"
        assert filtered[1].title == "Medium"


class TestResolveInputFiles:
    """Tests for the resolve_input_files function."""

    def test_resolve_single_file(self, tmp_path: Path) -> None:
        """Test resolving a single file path."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        files = resolve_input_files([str(test_file)])
        assert len(files) == 1
        assert files[0] == test_file

    def test_resolve_glob_pattern(self, tmp_path: Path) -> None:
        """Test resolving a glob pattern."""
        # Create test files
        (tmp_path / "video1.mkv").touch()
        (tmp_path / "video2.mkv").touch()
        (tmp_path / "other.mp4").touch()

        pattern = str(tmp_path / "*.mkv")
        files = resolve_input_files(pattern)

        assert len(files) == 2
        assert all(f.suffix == ".mkv" for f in files)

    def test_resolve_no_matches(self, tmp_path: Path) -> None:
        """Test error when glob pattern matches nothing."""
        pattern = str(tmp_path / "*.mkv")
        with pytest.raises(FileNotFoundError, match="No files found"):
            resolve_input_files(pattern)

    def test_resolve_invalid_type(self) -> None:
        """Test error for invalid input type."""
        with pytest.raises(ValueError, match="must be a string"):
            resolve_input_files(123)  # type: ignore[arg-type]

    def test_resolve_list_sorted(self, tmp_path: Path) -> None:
        """Test that file list is sorted."""
        files = [
            tmp_path / "c.mkv",
            tmp_path / "a.mkv",
            tmp_path / "b.mkv",
        ]
        for f in files:
            f.touch()

        resolved = resolve_input_files([str(f) for f in files])
        assert resolved[0].name == "a.mkv"
        assert resolved[1].name == "b.mkv"
        assert resolved[2].name == "c.mkv"

    def test_resolve_filters_unsupported_formats(self, tmp_path: Path) -> None:
        """Test that unsupported formats are filtered out by default."""
        (tmp_path / "video.mkv").touch()
        (tmp_path / "video.mp4").touch()
        (tmp_path / "document.txt").touch()
        (tmp_path / "image.png").touch()

        pattern = str(tmp_path / "*")
        files = resolve_input_files(pattern, filter_supported=True)

        assert len(files) == 2
        assert all(f.suffix in SUPPORTED_FORMATS for f in files)

    def test_resolve_includes_all_when_filter_disabled(self, tmp_path: Path) -> None:
        """Test that filter_supported=False includes all files."""
        (tmp_path / "video.mkv").touch()
        (tmp_path / "document.txt").touch()

        pattern = str(tmp_path / "*")
        files = resolve_input_files(pattern, filter_supported=False)

        assert len(files) == 2


class TestFormatSupport:
    """Tests for multi-format support utilities."""

    def test_supported_formats_contains_expected(self) -> None:
        """Test that SUPPORTED_FORMATS contains expected formats."""
        expected = {".mkv", ".mp4", ".m4v", ".avi", ".webm", ".ts", ".m2ts"}
        assert expected == SUPPORTED_FORMATS

    def test_supported_formats_is_frozenset(self) -> None:
        """Test that SUPPORTED_FORMATS is immutable."""
        assert isinstance(SUPPORTED_FORMATS, frozenset)

    def test_is_supported_format_with_string(self) -> None:
        """Test is_supported_format with string paths."""
        assert is_supported_format("video.mkv")
        assert is_supported_format("video.mp4")
        assert is_supported_format("video.avi")
        assert is_supported_format("/path/to/video.webm")
        assert not is_supported_format("document.txt")
        assert not is_supported_format("image.png")

    def test_is_supported_format_with_path(self) -> None:
        """Test is_supported_format with Path objects."""
        assert is_supported_format(Path("video.mkv"))
        assert is_supported_format(Path("video.MP4"))  # Case insensitive
        assert not is_supported_format(Path("file.pdf"))

    def test_is_supported_format_case_insensitive(self) -> None:
        """Test that format checking is case-insensitive."""
        assert is_supported_format("video.MKV")
        assert is_supported_format("video.Mp4")
        assert is_supported_format("video.AVI")

    def test_validate_format_success(self) -> None:
        """Test validate_format passes for supported formats."""
        # Should not raise
        validate_format("video.mkv")
        validate_format(Path("video.mp4"))
        validate_format("video.webm")

    def test_validate_format_raises_for_unsupported(self) -> None:
        """Test validate_format raises UnsupportedFormatError."""
        with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
            validate_format("document.txt")

        with pytest.raises(UnsupportedFormatError, match=".pdf"):
            validate_format(Path("file.pdf"))

    def test_validate_format_error_message_includes_supported(self) -> None:
        """Test error message lists supported formats."""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            validate_format("file.xyz")

        error_msg = str(exc_info.value)
        assert ".mkv" in error_msg
        assert ".mp4" in error_msg
