"""Filename parsing and media information extraction.

This module provides utilities for parsing video filenames to extract
show names, season/episode numbers, and other metadata.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guessit import guessit  # type: ignore[import-untyped]


@dataclass(frozen=True)
class MediaInfo:
    """Parsed media information from a filename.

    Attributes:
        title: The show/movie title.
        season: Season number (for TV shows).
        episode: Episode number or range.
        episode_count: Number of episodes (for merged files).
        year: Release year.
        source: Video source (e.g., 'BluRay', 'WEB-DL').
        resolution: Video resolution (e.g., '1080p', '720p').
        video_codec: Video codec (e.g., 'H.264', 'HEVC').
        audio_codec: Audio codec (e.g., 'AAC', 'FLAC').
        release_group: Release group name.
        raw_data: Original guessit output dictionary.
    """

    title: str | None = None
    season: int | None = None
    episode: int | None = None
    episode_count: int | None = None
    year: int | None = None
    source: str | None = None
    resolution: str | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    release_group: str | None = None
    raw_data: dict[str, Any] | None = None

    @property
    def is_episode(self) -> bool:
        """Check if this is a TV episode."""
        return self.episode is not None

    @property
    def is_season_pack(self) -> bool:
        """Check if this appears to be a season pack (multiple episodes)."""
        return self.episode_count is not None and self.episode_count > 1

    def format_episode_id(self) -> str:
        """Format the season/episode identifier (e.g., 'S01E05')."""
        parts = []
        if self.season is not None:
            parts.append(f"S{self.season:02d}")
        if self.episode is not None:
            parts.append(f"E{self.episode:02d}")
            if self.episode_count and self.episode_count > 1:
                last_ep = self.episode + self.episode_count - 1
                parts.append(f"-E{last_ep:02d}")
        return "".join(parts) if parts else ""

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = []
        if self.title:
            parts.append(self.title)
        ep_id = self.format_episode_id()
        if ep_id:
            parts.append(ep_id)
        if self.year:
            parts.append(f"({self.year})")
        return " ".join(parts) if parts else "(Unknown)"


def parse_filename(filename: str | Path) -> MediaInfo:
    """Parse a video filename to extract media information.

    Uses the guessit library to intelligently parse common naming patterns
    for TV shows, anime, and movies.

    Args:
        filename: The filename or path to parse.

    Returns:
        MediaInfo object containing parsed information.

    Example:
        >>> info = parse_filename("Show.Name.S01E05.720p.BluRay.x264.mkv")
        >>> print(info.title)
        'Show Name'
        >>> print(info.season, info.episode)
        1 5

        >>> info = parse_filename("[Group] Anime - 01-12 [1080p].mkv")
        >>> print(info.title)
        'Anime'
        >>> print(info.episode, info.episode_count)
        1 12
    """
    # Get just the filename if a path was provided
    name = filename.name if isinstance(filename, Path) else Path(filename).name

    # Parse with guessit
    result = guessit(name)

    # Extract episode information
    episode = None
    episode_count = None

    ep_value = result.get("episode")
    if ep_value is not None:
        if isinstance(ep_value, list):
            # Episode range like [1, 2, 3] or [1, 12]
            episode = min(ep_value)
            episode_count = max(ep_value) - min(ep_value) + 1
        else:
            episode = int(ep_value)
            episode_count = 1

    # Check for episode_count field (some patterns set this directly)
    if result.get("episode_count"):
        episode_count = int(result["episode_count"])

    return MediaInfo(
        title=result.get("title"),
        season=result.get("season"),
        episode=episode,
        episode_count=episode_count,
        year=result.get("year"),
        source=result.get("source"),
        resolution=result.get("screen_size"),
        video_codec=result.get("video_codec"),
        audio_codec=result.get("audio_codec"),
        release_group=result.get("release_group"),
        raw_data=dict(result),
    )


def parse_episode_range(range_str: str) -> tuple[int, int]:
    """Parse an episode range string like '1-12' or '01-24'.

    Args:
        range_str: Episode range in format 'start-end' or just 'count'.

    Returns:
        Tuple of (start_episode, episode_count).

    Raises:
        ValueError: If the range string is invalid.

    Example:
        >>> parse_episode_range("1-12")
        (1, 12)
        >>> parse_episode_range("5")
        (1, 5)
    """
    range_str = range_str.strip()

    if "-" in range_str:
        parts = range_str.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid episode range: {range_str}")
        start = int(parts[0])
        end = int(parts[1])
        return (start, end - start + 1)
    else:
        # Just a count, assume starting from episode 1
        count = int(range_str)
        return (1, count)
