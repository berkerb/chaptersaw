"""Tests for the parser module."""

from pathlib import Path

import pytest

from chaptersaw.parser import MediaInfo, parse_episode_range, parse_filename


class TestMediaInfo:
    """Tests for the MediaInfo dataclass."""

    def test_media_info_defaults(self) -> None:
        """Test default values for MediaInfo."""
        info = MediaInfo()
        assert info.title is None
        assert info.season is None
        assert info.episode is None
        assert info.episode_count is None
        assert info.year is None
        assert info.source is None
        assert info.resolution is None
        assert info.video_codec is None
        assert info.audio_codec is None
        assert info.release_group is None
        assert info.raw_data is None

    def test_is_episode_true(self) -> None:
        """Test is_episode returns True when episode is set."""
        info = MediaInfo(episode=5)
        assert info.is_episode is True

    def test_is_episode_false(self) -> None:
        """Test is_episode returns False when episode is None."""
        info = MediaInfo(title="Movie")
        assert info.is_episode is False

    def test_is_season_pack_true(self) -> None:
        """Test is_season_pack returns True for multiple episodes."""
        info = MediaInfo(episode=1, episode_count=12)
        assert info.is_season_pack is True

    def test_is_season_pack_false_single(self) -> None:
        """Test is_season_pack returns False for single episode."""
        info = MediaInfo(episode=5, episode_count=1)
        assert info.is_season_pack is False

    def test_is_season_pack_false_none(self) -> None:
        """Test is_season_pack returns False when episode_count is None."""
        info = MediaInfo(episode=5)
        assert info.is_season_pack is False

    def test_format_episode_id_season_episode(self) -> None:
        """Test format_episode_id with season and episode."""
        info = MediaInfo(season=1, episode=5)
        assert info.format_episode_id() == "S01E05"

    def test_format_episode_id_episode_only(self) -> None:
        """Test format_episode_id with episode only."""
        info = MediaInfo(episode=12)
        assert info.format_episode_id() == "E12"

    def test_format_episode_id_season_only(self) -> None:
        """Test format_episode_id with season only."""
        info = MediaInfo(season=3)
        assert info.format_episode_id() == "S03"

    def test_format_episode_id_range(self) -> None:
        """Test format_episode_id with episode range."""
        info = MediaInfo(season=1, episode=1, episode_count=12)
        assert info.format_episode_id() == "S01E01-E12"

    def test_format_episode_id_empty(self) -> None:
        """Test format_episode_id returns empty string when no season/episode."""
        info = MediaInfo(title="Movie")
        assert info.format_episode_id() == ""

    def test_str_basic(self) -> None:
        """Test string representation with title."""
        info = MediaInfo(title="Show Name")
        assert str(info) == "Show Name"

    def test_str_with_episode(self) -> None:
        """Test string representation with episode."""
        info = MediaInfo(title="Show Name", season=1, episode=5)
        assert str(info) == "Show Name S01E05"

    def test_str_with_year(self) -> None:
        """Test string representation with year."""
        info = MediaInfo(title="Movie", year=2023)
        assert str(info) == "Movie (2023)"

    def test_str_empty(self) -> None:
        """Test string representation when empty."""
        info = MediaInfo()
        assert str(info) == "(Unknown)"


class TestParseFilename:
    """Tests for the parse_filename function."""

    def test_parse_anime_batch_release(self) -> None:
        """Test parsing anime batch release filename."""
        info = parse_filename("[SubsPlease] Frieren - 01-28 [1080p].mkv")
        assert info.title == "Frieren"
        assert info.episode == 1
        assert info.episode_count == 28
        assert info.resolution == "1080p"
        assert info.release_group == "SubsPlease"

    def test_parse_tv_show_episode(self) -> None:
        """Test parsing standard TV show episode filename."""
        info = parse_filename("Show.Name.S01E05.720p.BluRay.x264.mkv")
        assert info.title == "Show Name"
        assert info.season == 1
        assert info.episode == 5
        assert info.resolution == "720p"
        assert info.source == "Blu-ray"

    def test_parse_anime_with_group(self) -> None:
        """Test parsing anime with release group."""
        info = parse_filename(
            "[Coalgirls] Clannad After Story - 01-24 (BD 1920x1080 x264 FLAC).mkv"
        )
        assert info.title == "Clannad After Story"
        assert info.episode == 1
        assert info.episode_count == 24
        assert info.release_group == "Coalgirls"
        assert info.resolution == "1080p"

    def test_parse_season_pack(self) -> None:
        """Test parsing season pack filename."""
        info = parse_filename("The.Office.S03.COMPLETE.1080p.WEB-DL.mkv")
        assert info.title == "The Office"
        assert info.season == 3
        assert info.resolution == "1080p"
        assert info.source == "Web"

    def test_parse_path_object(self) -> None:
        """Test parsing with Path object."""
        info = parse_filename(Path("/some/path/Show.S01E01.mkv"))
        assert info.title == "Show"
        assert info.season == 1
        assert info.episode == 1

    def test_parse_movie_with_year(self) -> None:
        """Test parsing movie filename with year."""
        info = parse_filename("Movie.Name.2023.1080p.BluRay.x265.mkv")
        assert info.title == "Movie Name"
        assert info.year == 2023
        assert info.resolution == "1080p"

    def test_parse_preserves_raw_data(self) -> None:
        """Test that raw guessit data is preserved."""
        info = parse_filename("Show.S01E01.mkv")
        assert info.raw_data is not None
        assert isinstance(info.raw_data, dict)


class TestParseEpisodeRange:
    """Tests for the parse_episode_range function."""

    def test_parse_range(self) -> None:
        """Test parsing episode range."""
        start, count = parse_episode_range("1-12")
        assert start == 1
        assert count == 12

    def test_parse_range_padded(self) -> None:
        """Test parsing padded episode range."""
        start, count = parse_episode_range("01-24")
        assert start == 1
        assert count == 24

    def test_parse_range_mid(self) -> None:
        """Test parsing episode range not starting from 1."""
        start, count = parse_episode_range("13-24")
        assert start == 13
        assert count == 12

    def test_parse_count_only(self) -> None:
        """Test parsing episode count only."""
        start, count = parse_episode_range("12")
        assert start == 1
        assert count == 12

    def test_parse_whitespace(self) -> None:
        """Test parsing with whitespace."""
        start, count = parse_episode_range("  5-10  ")
        assert start == 5
        assert count == 6

    def test_parse_invalid_range(self) -> None:
        """Test parsing invalid range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid episode range"):
            parse_episode_range("1-2-3")

    def test_parse_invalid_number(self) -> None:
        """Test parsing non-numeric value raises ValueError."""
        with pytest.raises(ValueError):
            parse_episode_range("abc")
