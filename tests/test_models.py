"""Tests for the models module."""

from pathlib import Path

import pytest

from chaptersaw.models import Chapter, ExtractionResult


class TestChapter:
    """Tests for the Chapter dataclass."""

    def test_chapter_creation(self) -> None:
        """Test basic chapter creation."""
        chapter = Chapter(
            title="Episode 1",
            start_time=0.0,
            end_time=300.0,
            index=0,
        )
        assert chapter.title == "Episode 1"
        assert chapter.start_time == 0.0
        assert chapter.end_time == 300.0
        assert chapter.index == 0

    def test_chapter_duration(self) -> None:
        """Test duration property calculation."""
        chapter = Chapter(
            title="Test Chapter",
            start_time=100.5,
            end_time=250.75,
        )
        assert chapter.duration == pytest.approx(150.25)

    def test_chapter_without_index(self) -> None:
        """Test chapter creation without optional index."""
        chapter = Chapter(
            title="No Index Chapter",
            start_time=0.0,
            end_time=60.0,
        )
        assert chapter.index is None

    def test_chapter_str_representation(self) -> None:
        """Test string representation of chapter."""
        chapter = Chapter(
            title="Test Title",
            start_time=10.0,
            end_time=100.5,
        )
        str_repr = str(chapter)
        assert "Test Title" in str_repr
        assert "10.00" in str_repr
        assert "100.50" in str_repr


class TestExtractionResult:
    """Tests for the ExtractionResult dataclass."""

    def test_extraction_result_defaults(self) -> None:
        """Test default values for extraction result."""
        result = ExtractionResult(source_file=Path("test.mkv"))
        assert result.source_file == Path("test.mkv")
        assert result.output_file is None
        assert result.chapters_found == 0
        assert result.chapters_matched == 0
        assert result.chapters_extracted == []
        assert result.success is True
        assert result.error_message is None

    def test_extraction_result_with_chapters(self) -> None:
        """Test extraction result with extracted chapters."""
        chapters = [
            Chapter("Chapter 1", 0.0, 100.0),
            Chapter("Chapter 2", 100.0, 200.0),
        ]
        result = ExtractionResult(
            source_file=Path("test.mkv"),
            output_file=Path("output.mkv"),
            chapters_found=5,
            chapters_matched=2,
            chapters_extracted=chapters,
        )
        assert result.chapters_found == 5
        assert result.chapters_matched == 2
        assert len(result.chapters_extracted) == 2

    def test_extraction_result_failed(self) -> None:
        """Test extraction result with failure."""
        result = ExtractionResult(
            source_file=Path("test.mkv"),
            success=False,
            error_message="File not found",
        )
        assert result.success is False
        assert result.error_message == "File not found"

    def test_extraction_result_str_success(self) -> None:
        """Test string representation for successful result."""
        result = ExtractionResult(
            source_file=Path("video.mkv"),
            chapters_found=10,
            chapters_matched=3,
        )
        str_repr = str(result)
        assert "video.mkv" in str_repr
        assert "3/10" in str_repr
        assert "Success" in str_repr

    def test_extraction_result_str_failure(self) -> None:
        """Test string representation for failed result."""
        result = ExtractionResult(
            source_file=Path("video.mkv"),
            success=False,
            error_message="Something went wrong",
        )
        str_repr = str(result)
        assert "Failed" in str_repr
        assert "Something went wrong" in str_repr
