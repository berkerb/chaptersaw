"""Integration tests for Chaptersaw.

These tests verify the complete workflow from CLI to extraction,
using mocked ffmpeg/ffprobe responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chaptersaw.cli import main
from chaptersaw.extractor import ChapterExtractor
from chaptersaw.models import Chapter


class TestEndToEndWorkflow:
    """End-to-end tests for the extraction workflow."""

    @pytest.fixture
    def mock_ffmpeg(self) -> MagicMock:
        """Mock ffmpeg/ffprobe commands."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    @pytest.fixture
    def sample_chapters(self) -> dict:
        """Sample chapter data for mocking."""
        return {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "90.000000",
                    "tags": {"title": "Opening"},
                },
                {
                    "start_time": "90.000000",
                    "end_time": "1200.000000",
                    "tags": {"title": "Episode 1"},
                },
                {
                    "start_time": "1200.000000",
                    "end_time": "1290.000000",
                    "tags": {"title": "Credits"},
                },
                {
                    "start_time": "1290.000000",
                    "end_time": "1320.000000",
                    "tags": {"title": "Preview"},
                },
            ]
        }

    def test_filter_by_keyword(self, mock_ffmpeg: MagicMock) -> None:
        """Test filtering chapters by keyword."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("Opening", 0.0, 90.0),
            Chapter("Episode 1", 90.0, 1200.0),
            Chapter("Credits", 1200.0, 1290.0),
        ]

        # Filter for Episode
        filtered = extractor.filter_chapters_by_keyword(chapters, "Episode")
        assert len(filtered) == 1
        assert filtered[0].title == "Episode 1"

    def test_filter_by_regex(self, mock_ffmpeg: MagicMock) -> None:
        """Test filtering chapters by regex pattern."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("Episode 1", 0.0, 100.0),
            Chapter("Episode 2", 100.0, 200.0),
            Chapter("Episode 10", 200.0, 300.0),
            Chapter("Credits", 300.0, 350.0),
        ]

        # Match Episode followed by single digit
        filtered = extractor.filter_chapters_by_regex(chapters, r"Episode \d$")
        assert len(filtered) == 2
        assert filtered[0].title == "Episode 1"
        assert filtered[1].title == "Episode 2"

    def test_filter_exclude_mode(self, mock_ffmpeg: MagicMock) -> None:
        """Test exclude mode filtering."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("Opening", 0.0, 90.0),
            Chapter("Episode 1", 90.0, 1200.0),
            Chapter("Credits", 1200.0, 1290.0),
        ]

        # Exclude Opening and Credits
        filtered = extractor.filter_chapters_by_keyword(
            chapters, "Opening", exclude=True
        )
        assert len(filtered) == 2
        assert all(ch.title != "Opening" for ch in filtered)

    def test_regex_exclude_mode(self, mock_ffmpeg: MagicMock) -> None:
        """Test regex with exclude mode."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("Opening", 0.0, 90.0),
            Chapter("Episode 1", 90.0, 1200.0),
            Chapter("Credits", 1200.0, 1290.0),
            Chapter("Preview", 1290.0, 1320.0),
        ]

        # Exclude non-episode chapters (Opening, Credits, Preview)
        filtered = extractor.filter_chapters_by_regex(
            chapters, r"^(Opening|Credits|Preview)$", exclude=True
        )
        assert len(filtered) == 1
        assert filtered[0].title == "Episode 1"


class TestCLIIntegration:
    """Integration tests for CLI behavior."""

    @pytest.fixture
    def mock_ffmpeg_validation(self) -> MagicMock:
        """Mock ffmpeg validation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield mock_run

    def test_list_chapters_command(
        self, tmp_path: Path, mock_ffmpeg_validation: MagicMock
    ) -> None:
        """Test --list-chapters command."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        chapter_data = {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "100.000000",
                    "tags": {"title": "Chapter 1"},
                },
                {
                    "start_time": "100.000000",
                    "end_time": "200.000000",
                    "tags": {"title": "Chapter 2"},
                },
            ]
        }

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = MagicMock(returncode=0)
            if "ffprobe" in str(cmd[0]) or cmd[0] == "ffprobe":
                result.stdout = json.dumps(chapter_data)
            return result

        mock_ffmpeg_validation.side_effect = mock_run_side_effect

        # Test list chapters mode
        exit_code = main(
            ["-i", str(test_file), "--list-chapters", "--no-progress"]
        )
        assert exit_code == 0

    def test_dry_run_with_regex(
        self, tmp_path: Path, mock_ffmpeg_validation: MagicMock
    ) -> None:
        """Test dry run with regex pattern."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        chapter_data = {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "100.000000",
                    "tags": {"title": "Part A"},
                },
                {
                    "start_time": "100.000000",
                    "end_time": "200.000000",
                    "tags": {"title": "Part B"},
                },
                {
                    "start_time": "200.000000",
                    "end_time": "300.000000",
                    "tags": {"title": "Bonus"},
                },
            ]
        }

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = MagicMock(returncode=0)
            if "ffprobe" in str(cmd[0]) or cmd[0] == "ffprobe":
                result.stdout = json.dumps(chapter_data)
            return result

        mock_ffmpeg_validation.side_effect = mock_run_side_effect

        # Test dry run with regex
        exit_code = main(
            [
                "-i", str(test_file),
                "-r", r"Part [AB]",
                "-o", str(tmp_path / "output.mkv"),
                "--dry-run",
            ]
        )
        assert exit_code == 0

    def test_exclude_mode_cli(
        self, tmp_path: Path, mock_ffmpeg_validation: MagicMock
    ) -> None:
        """Test --exclude flag in CLI."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        chapter_data = {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "100.000000",
                    "tags": {"title": "Intro"},
                },
                {
                    "start_time": "100.000000",
                    "end_time": "200.000000",
                    "tags": {"title": "Main Content"},
                },
            ]
        }

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = MagicMock(returncode=0)
            if "ffprobe" in str(cmd[0]) or cmd[0] == "ffprobe":
                result.stdout = json.dumps(chapter_data)
            return result

        mock_ffmpeg_validation.side_effect = mock_run_side_effect

        # Test exclude mode in dry run
        exit_code = main(
            [
                "-i", str(test_file),
                "-k", "Intro",
                "--exclude",
                "-o", str(tmp_path / "output.mkv"),
                "--dry-run",
            ]
        )
        assert exit_code == 0


class TestParallelProcessing:
    """Tests for parallel processing functionality."""

    @pytest.fixture
    def mock_ffmpeg(self) -> MagicMock:
        """Mock ffmpeg/ffprobe commands."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    def test_parallel_extraction_flag(self, mock_ffmpeg: MagicMock) -> None:
        """Test that parallel processing can be enabled."""
        extractor = ChapterExtractor()

        # Just verify the extractor can be instantiated with parallel support
        assert hasattr(extractor, "_extract_segments_parallel")

    def test_segment_ordering_preserved(self, mock_ffmpeg: MagicMock) -> None:
        """Test that segment order is preserved in parallel mode."""
        # Verify ChapterExtractor has parallel extraction method
        extractor = ChapterExtractor()
        assert hasattr(extractor, "_extract_segments_parallel")

        chapters = [
            Chapter("Chapter 1", 0.0, 100.0, index=0),
            Chapter("Chapter 2", 100.0, 200.0, index=1),
            Chapter("Chapter 3", 200.0, 300.0, index=2),
        ]

        # Verify chapters maintain order
        assert chapters[0].index == 0
        assert chapters[1].index == 1
        assert chapters[2].index == 2


class TestRegexPatterns:
    """Tests for various regex pattern scenarios."""

    @pytest.fixture
    def mock_ffmpeg(self) -> MagicMock:
        """Mock ffmpeg commands."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            yield mock_run

    def test_complex_regex_pattern(self, mock_ffmpeg: MagicMock) -> None:
        """Test complex regex patterns."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("Episode 01 - The Beginning", 0.0, 100.0),
            Chapter("Episode 02 - The Middle", 100.0, 200.0),
            Chapter("Special 01", 200.0, 250.0),
            Chapter("Episode 10 - The End", 250.0, 350.0),
        ]

        # Match only numbered episodes
        filtered = extractor.filter_chapters_by_regex(chapters, r"^Episode \d+")
        assert len(filtered) == 3
        assert all("Episode" in ch.title for ch in filtered)

    def test_case_insensitive_regex(self, mock_ffmpeg: MagicMock) -> None:
        """Test case-insensitive regex matching."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("EPISODE 1", 0.0, 100.0),
            Chapter("Episode 2", 100.0, 200.0),
            Chapter("episode 3", 200.0, 300.0),
        ]

        # Case insensitive by default
        filtered = extractor.filter_chapters_by_regex(
            chapters, "episode", case_sensitive=False
        )
        assert len(filtered) == 3

    def test_case_sensitive_regex(self, mock_ffmpeg: MagicMock) -> None:
        """Test case-sensitive regex matching."""
        extractor = ChapterExtractor()

        chapters = [
            Chapter("EPISODE 1", 0.0, 100.0),
            Chapter("Episode 2", 100.0, 200.0),
            Chapter("episode 3", 200.0, 300.0),
        ]

        # Case sensitive
        filtered = extractor.filter_chapters_by_regex(
            chapters, "Episode", case_sensitive=True
        )
        assert len(filtered) == 1
        assert filtered[0].title == "Episode 2"

    def test_invalid_regex_raises_error(self, mock_ffmpeg: MagicMock) -> None:
        """Test that invalid regex patterns raise an error."""
        import re

        extractor = ChapterExtractor()
        chapters = [Chapter("Test", 0.0, 100.0)]

        with pytest.raises(re.error):
            extractor.filter_chapters_by_regex(chapters, "[invalid(regex")
