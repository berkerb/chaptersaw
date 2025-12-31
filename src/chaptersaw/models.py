"""Data models for Chaptersaw."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Track:
    """Represents an audio, video, or subtitle track within a video file.

    Attributes:
        id: Track ID (used for selection).
        type: Track type ('video', 'audio', 'subtitles').
        codec: Codec name (e.g., 'H.264', 'AAC', 'SRT').
        language: Language code (e.g., 'eng', 'jpn').
        name: Track name/title if available.
        default: Whether this track is marked as default.
        forced: Whether this track is marked as forced.
        channels: Number of audio channels (audio tracks only).
        sample_rate: Sample rate in Hz (audio tracks only).
        width: Video width in pixels (video tracks only).
        height: Video height in pixels (video tracks only).
    """

    id: int
    type: str
    codec: str
    language: str | None = None
    name: str | None = None
    default: bool = False
    forced: bool = False
    channels: int | None = None
    sample_rate: int | None = None
    width: int | None = None
    height: int | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = [f"#{self.id} {self.type}: {self.codec}"]
        if self.language:
            parts.append(f"[{self.language}]")
        if self.name:
            parts.append(f'"{self.name}"')
        if self.default:
            parts.append("(default)")
        if self.forced:
            parts.append("(forced)")
        return " ".join(parts)


@dataclass(frozen=True)
class Chapter:
    """Represents a chapter within a video file.

    Attributes:
        title: The title/name of the chapter.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        index: Optional chapter index within the source file.
    """

    title: str
    start_time: float
    end_time: float
    index: int | None = None

    @property
    def duration(self) -> float:
        """Calculate the duration of the chapter in seconds."""
        return self.end_time - self.start_time

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"{self.title} ({self.start_time:.2f}s - {self.end_time:.2f}s)"


@dataclass
class ExtractionResult:
    """Result of a chapter extraction operation.

    Attributes:
        source_file: Path to the source video file.
        output_file: Path to the output file (if created).
        chapters_found: Total number of chapters found in the source.
        chapters_matched: Number of chapters matching the filter criteria.
        chapters_extracted: List of Chapter objects that were extracted.
        success: Whether the extraction was successful.
        error_message: Error message if extraction failed.
    """

    source_file: Path
    output_file: Path | None = None
    chapters_found: int = 0
    chapters_matched: int = 0
    chapters_extracted: list[Chapter] = field(default_factory=list)
    success: bool = True
    error_message: str | None = None

    def __str__(self) -> str:
        """Return a human-readable summary of the extraction result."""
        status = "Success" if self.success else f"Failed: {self.error_message}"
        return (
            f"{self.source_file.name}: {self.chapters_matched}/{self.chapters_found} "
            f"chapters matched - {status}"
        )
