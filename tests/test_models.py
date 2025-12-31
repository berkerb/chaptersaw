"""Tests for the models module."""

from pathlib import Path

import pytest

from chaptersaw.models import Chapter, ExtractionResult, Track


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


class TestTrack:
    """Tests for the Track dataclass."""

    def test_track_creation_video(self) -> None:
        """Test basic video track creation."""
        track = Track(
            id=0,
            type="video",
            codec="h264",
            width=1920,
            height=1080,
        )
        assert track.id == 0
        assert track.type == "video"
        assert track.codec == "h264"
        assert track.width == 1920
        assert track.height == 1080

    def test_track_creation_audio(self) -> None:
        """Test basic audio track creation."""
        track = Track(
            id=1,
            type="audio",
            codec="aac",
            language="eng",
            channels=2,
            sample_rate=48000,
            default=True,
        )
        assert track.id == 1
        assert track.type == "audio"
        assert track.codec == "aac"
        assert track.language == "eng"
        assert track.channels == 2
        assert track.sample_rate == 48000
        assert track.default is True

    def test_track_creation_subtitle(self) -> None:
        """Test basic subtitle track creation."""
        track = Track(
            id=2,
            type="subtitles",
            codec="subrip",
            language="jpn",
            name="Japanese",
            forced=True,
        )
        assert track.id == 2
        assert track.type == "subtitles"
        assert track.codec == "subrip"
        assert track.language == "jpn"
        assert track.name == "Japanese"
        assert track.forced is True

    def test_track_defaults(self) -> None:
        """Test default values for track."""
        track = Track(id=0, type="video", codec="h264")
        assert track.language is None
        assert track.name is None
        assert track.default is False
        assert track.forced is False
        assert track.channels is None
        assert track.sample_rate is None
        assert track.width is None
        assert track.height is None

    def test_track_str_basic(self) -> None:
        """Test basic string representation of track."""
        track = Track(id=0, type="video", codec="h264")
        str_repr = str(track)
        assert "#0" in str_repr
        assert "video" in str_repr
        assert "h264" in str_repr

    def test_track_str_with_language(self) -> None:
        """Test string representation with language."""
        track = Track(id=1, type="audio", codec="aac", language="jpn")
        str_repr = str(track)
        assert "[jpn]" in str_repr

    def test_track_str_with_name(self) -> None:
        """Test string representation with name."""
        track = Track(id=2, type="subtitles", codec="ass", name="English Subs")
        str_repr = str(track)
        assert '"English Subs"' in str_repr

    def test_track_str_with_flags(self) -> None:
        """Test string representation with default and forced flags."""
        track = Track(
            id=1,
            type="audio",
            codec="aac",
            default=True,
            forced=True,
        )
        str_repr = str(track)
        assert "(default)" in str_repr
        assert "(forced)" in str_repr
