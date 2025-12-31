"""Core extraction functionality for Chaptersaw.

This module provides the main ChapterExtractor class and convenience functions
for extracting chapters from video files.
"""

import json
import logging
import re
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob
from pathlib import Path

from chaptersaw.exceptions import (
    ChapterExtractionError,
    FFmpegNotFoundError,
    UnsupportedFormatError,
)
from chaptersaw.models import Chapter, ExtractionResult, Track

logger = logging.getLogger(__name__)

# Supported video container formats
SUPPORTED_FORMATS: frozenset[str] = frozenset({
    ".mkv",   # Matroska
    ".mp4",   # MPEG-4 Part 14
    ".m4v",   # iTunes Video
    ".avi",   # Audio Video Interleave
    ".webm",  # WebM
    ".ts",    # MPEG Transport Stream
    ".m2ts",  # Blu-ray MPEG-2 Transport Stream
})


class ChapterExtractor:
    """Extract and merge chapters from video files.

    This class provides methods to:
    - Probe video files for chapter information
    - Filter chapters by title keywords
    - Extract chapter segments
    - Merge segments into output files
    - Modify track properties (default flags, etc.)

    Attributes:
        ffmpeg_path: Path to the ffmpeg executable.
        ffprobe_path: Path to the ffprobe executable.
        mkvpropedit_path: Path to the mkvpropedit executable (optional).
        temp_dir: Temporary directory for intermediate files.

    Example:
        >>> extractor = ChapterExtractor()
        >>> chapters = extractor.get_chapters("video.mkv")
        >>> filtered = extractor.filter_chapters_by_keyword(chapters, "Episode")
        >>> extractor.extract_and_merge(["video.mkv"], "output.mkv", "Episode")
    """

    def __init__(
        self,
        ffmpeg_path: str | Path = "ffmpeg",
        ffprobe_path: str | Path = "ffprobe",
        mkvpropedit_path: str | Path = "mkvpropedit",
        temp_dir: Path | None = None,
    ) -> None:
        """Initialize the ChapterExtractor.

        Args:
            ffmpeg_path: Path to the ffmpeg executable. Defaults to "ffmpeg"
                (assumes it's in PATH).
            ffprobe_path: Path to the ffprobe executable. Defaults to "ffprobe"
                (assumes it's in PATH).
            mkvpropedit_path: Path to the mkvpropedit executable. Defaults to
                "mkvpropedit" (assumes it's in PATH). Optional for MKV editing.
            temp_dir: Directory for temporary files. If None, uses system temp.

        Raises:
            FFmpegNotFoundError: If ffmpeg or ffprobe cannot be found.
        """
        self.ffmpeg_path = Path(ffmpeg_path)
        self.ffprobe_path = Path(ffprobe_path)
        self.mkvpropedit_path = Path(mkvpropedit_path)
        self._temp_dir = temp_dir
        self._mkvpropedit_available: bool | None = None
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Validate that ffmpeg and ffprobe are available."""
        for tool, path in [
            ("ffprobe", self.ffprobe_path),
            ("ffmpeg", self.ffmpeg_path),
        ]:
            try:
                subprocess.run(
                    [str(path), "-version"],
                    capture_output=True,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise FFmpegNotFoundError(
                    f"{tool} not found at '{path}'. Please install FFmpeg and ensure "
                    "it's in your PATH, or provide the full path to the executable."
                ) from e

    def get_chapters(self, input_file: str | Path) -> list[Chapter]:
        """Extract chapter information from an MKV file.

        Args:
            input_file: Path to the MKV file.

        Returns:
            List of Chapter objects containing chapter metadata.

        Raises:
            ChapterExtractionError: If chapter extraction fails.
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise ChapterExtractionError(f"Input file not found: {input_path}")

        cmd = [
            str(self.ffprobe_path),
            "-i",
            str(input_path),
            "-print_format",
            "json",
            "-show_chapters",
            "-loglevel",
            "error",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise ChapterExtractionError(
                f"Failed to probe file '{input_path}': {e.stderr}"
            ) from e
        except json.JSONDecodeError as e:
            raise ChapterExtractionError(
                f"Failed to parse chapter data from '{input_path}'"
            ) from e

        chapters = []
        for idx, chapter_data in enumerate(data.get("chapters", [])):
            tags = chapter_data.get("tags", {})
            title = tags.get("title", f"Chapter {idx + 1}")
            chapters.append(
                Chapter(
                    title=title,
                    start_time=float(chapter_data["start_time"]),
                    end_time=float(chapter_data["end_time"]),
                    index=idx,
                )
            )

        return chapters

    def get_tracks(self, input_file: str | Path) -> list[Track]:
        """Extract track information from a video file.

        Args:
            input_file: Path to the video file.

        Returns:
            List of Track objects containing track metadata.

        Raises:
            ChapterExtractionError: If track extraction fails.
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise ChapterExtractionError(f"Input file not found: {input_path}")

        cmd = [
            str(self.ffprobe_path),
            "-i",
            str(input_path),
            "-print_format",
            "json",
            "-show_streams",
            "-loglevel",
            "error",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise ChapterExtractionError(
                f"Failed to probe file '{input_path}': {e.stderr}"
            ) from e
        except json.JSONDecodeError as e:
            raise ChapterExtractionError(
                f"Failed to parse track data from '{input_path}'"
            ) from e

        tracks = []
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type", "unknown")

            # Map ffprobe codec_type to our track type
            if codec_type == "video":
                track_type = "video"
            elif codec_type == "audio":
                track_type = "audio"
            elif codec_type == "subtitle":
                track_type = "subtitles"
            else:
                track_type = codec_type

            # Get language from tags
            tags = stream.get("tags", {})
            language = tags.get("language")
            name = tags.get("title")

            # Get disposition flags
            disposition = stream.get("disposition", {})
            is_default = disposition.get("default", 0) == 1
            is_forced = disposition.get("forced", 0) == 1

            track = Track(
                id=stream.get("index", 0),
                type=track_type,
                codec=stream.get("codec_name", "unknown"),
                language=language,
                name=name,
                default=is_default,
                forced=is_forced,
                channels=stream.get("channels") if codec_type == "audio" else None,
                sample_rate=(
                    int(stream.get("sample_rate"))
                    if codec_type == "audio" and stream.get("sample_rate")
                    else None
                ),
                width=stream.get("width") if codec_type == "video" else None,
                height=stream.get("height") if codec_type == "video" else None,
            )
            tracks.append(track)

        return tracks

    def _is_mkvpropedit_available(self) -> bool:
        """Check if mkvpropedit is available."""
        if self._mkvpropedit_available is None:
            try:
                subprocess.run(
                    [str(self.mkvpropedit_path), "--version"],
                    capture_output=True,
                    check=True,
                )
                self._mkvpropedit_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._mkvpropedit_available = False
        return self._mkvpropedit_available

    def set_default_track(
        self,
        input_file: str | Path,
        track_id: int | None = None,
        track_type: str | None = None,
        language: str | None = None,
    ) -> None:
        """Set the default track for a specific track type in an MKV file.

        This modifies the file in-place using mkvpropedit. You can specify
        the track by ID, or by type and language.

        Args:
            input_file: Path to the MKV file to modify.
            track_id: Specific track ID to set as default. If provided,
                track_type and language are ignored.
            track_type: Type of track ('audio' or 'subtitles'). Used with
                language to find matching track.
            language: Language code (e.g., 'jpn', 'eng') to match.

        Raises:
            ChapterExtractionError: If modification fails or no matching track found.
            UnsupportedFormatError: If file is not MKV format.

        Example:
            >>> extractor.set_default_track("video.mkv", track_id=2)
            >>> extractor.set_default_track(
            ...     "video.mkv", track_type="audio", language="jpn"
            ... )
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise ChapterExtractionError(f"Input file not found: {input_path}")

        if input_path.suffix.lower() != ".mkv":
            raise UnsupportedFormatError(
                f"set_default_track only works with MKV files, got: {input_path.suffix}"
            )

        if not self._is_mkvpropedit_available():
            raise ChapterExtractionError(
                "mkvpropedit not found. Please install MKVToolNix to use this feature."
            )

        # If track_id is provided, use it directly
        if track_id is not None:
            target_track_id = track_id
            # Get tracks to find the type
            tracks = self.get_tracks(input_path)
            target_track = next((t for t in tracks if t.id == track_id), None)
            if target_track is None:
                raise ChapterExtractionError(f"Track ID {track_id} not found in file")
            target_type = target_track.type
        elif track_type and language:
            # Find track by type and language
            tracks = self.get_tracks(input_path)
            matching = [
                t for t in tracks
                if t.type == track_type and t.language == language
            ]
            if not matching:
                raise ChapterExtractionError(
                    f"No {track_type} track with language '{language}' found"
                )
            target_track_id = matching[0].id
            target_type = track_type
        else:
            raise ValueError(
                "Either track_id or both track_type and language must be provided"
            )

        # Get all tracks of the same type to clear their default flags
        tracks = self.get_tracks(input_path)
        same_type_tracks = [t for t in tracks if t.type == target_type]

        # Build mkvpropedit command
        # First, clear default flag on all tracks of same type
        # Then set default on target track
        cmd = [str(self.mkvpropedit_path), str(input_path)]

        for track in same_type_tracks:
            # mkvpropedit uses 1-based track numbers within each type
            # But we need to use the actual track selector
            cmd.extend([
                "--edit", f"track:={track.id}",
                "--set", "flag-default=0",
            ])

        # Set the target track as default
        cmd.extend([
            "--edit", f"track:={target_track_id}",
            "--set", "flag-default=1",
        ])

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ChapterExtractionError(
                f"Failed to set default track: {e.stderr.decode()}"
            ) from e

    def set_default_tracks_by_language(
        self,
        input_file: str | Path,
        audio_language: str | None = None,
        subtitle_language: str | None = None,
    ) -> dict[str, int | None]:
        """Set default audio and/or subtitle tracks by language preference.

        Args:
            input_file: Path to the MKV file to modify.
            audio_language: Language code for preferred audio (e.g., 'jpn').
            subtitle_language: Language code for preferred subtitle (e.g., 'eng').

        Returns:
            Dictionary with 'audio' and 'subtitle' keys, containing the track IDs
            that were set as default (or None if not found/changed).

        Raises:
            ChapterExtractionError: If modification fails.
            UnsupportedFormatError: If file is not MKV format.

        Example:
            >>> result = extractor.set_default_tracks_by_language(
            ...     "video.mkv", audio_language="jpn", subtitle_language="eng"
            ... )
            >>> print(result)
            {'audio': 1, 'subtitle': 3}
        """
        result: dict[str, int | None] = {"audio": None, "subtitle": None}

        if audio_language:
            try:
                self.set_default_track(
                    input_file, track_type="audio", language=audio_language
                )
                tracks = self.get_tracks(input_file)
                audio_track = next(
                    (
                        t for t in tracks
                        if t.type == "audio" and t.language == audio_language
                    ),
                    None,
                )
                if audio_track:
                    result["audio"] = audio_track.id
            except ChapterExtractionError:
                pass  # Track not found, continue

        if subtitle_language:
            try:
                self.set_default_track(
                    input_file, track_type="subtitles", language=subtitle_language
                )
                tracks = self.get_tracks(input_file)
                sub_track = next(
                    (
                        t for t in tracks
                        if t.type == "subtitles" and t.language == subtitle_language
                    ),
                    None,
                )
                if sub_track:
                    result["subtitle"] = sub_track.id
            except ChapterExtractionError:
                pass  # Track not found, continue

        return result

    def filter_chapters_by_keyword(
        self,
        chapters: list[Chapter],
        keyword: str,
        case_sensitive: bool = False,
        exclude: bool = False,
    ) -> list[Chapter]:
        """Filter chapters whose titles contain the specified keyword.

        Args:
            chapters: List of Chapter objects to filter.
            keyword: Keyword to search for in chapter titles.
            case_sensitive: Whether the search should be case-sensitive.
                Defaults to False.
            exclude: If True, return chapters that do NOT contain the keyword.
                Defaults to False.

        Returns:
            List of Chapter objects whose titles contain (or don't contain if
            exclude=True) the keyword.
        """
        if case_sensitive:
            matches = [ch for ch in chapters if keyword in ch.title]
        else:
            matches = [ch for ch in chapters if keyword.lower() in ch.title.lower()]

        if exclude:
            # Return chapters that are NOT in matches
            matched_set = set(matches)
            return [ch for ch in chapters if ch not in matched_set]
        return matches

    def filter_chapters_by_regex(
        self,
        chapters: list[Chapter],
        pattern: str,
        case_sensitive: bool = False,
        exclude: bool = False,
    ) -> list[Chapter]:
        """Filter chapters whose titles match the specified regex pattern.

        Args:
            chapters: List of Chapter objects to filter.
            pattern: Regular expression pattern to match against chapter titles.
            case_sensitive: Whether the regex should be case-sensitive.
                Defaults to False.
            exclude: If True, return chapters that do NOT match the pattern.
                Defaults to False.

        Returns:
            List of Chapter objects whose titles match (or don't match if
            exclude=True) the regex pattern.

        Raises:
            re.error: If the regex pattern is invalid.
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)

        if exclude:
            return [ch for ch in chapters if not compiled.search(ch.title)]
        return [ch for ch in chapters if compiled.search(ch.title)]

    def filter_chapters_by_predicate(
        self,
        chapters: list[Chapter],
        predicate: Callable[[Chapter], bool],
    ) -> list[Chapter]:
        """Filter chapters using a custom predicate function.

        Args:
            chapters: List of Chapter objects to filter.
            predicate: A function that takes a Chapter and returns True if it
                should be included.

        Returns:
            List of Chapter objects that satisfy the predicate.

        Example:
            >>> # Keep chapters longer than 5 minutes
            >>> filtered = extractor.filter_chapters_by_predicate(
            ...     chapters, lambda ch: ch.duration > 300
            ... )
        """
        return [ch for ch in chapters if predicate(ch)]

    def _extract_segment(
        self,
        input_file: Path,
        chapter: Chapter,
        output_file: Path,
    ) -> None:
        """Extract a single chapter segment from an MKV file.

        Args:
            input_file: Path to the source MKV file.
            chapter: Chapter object defining the segment boundaries.
            output_file: Path where the extracted segment will be saved.

        Raises:
            ChapterExtractionError: If extraction fails.
        """
        cmd = [
            str(self.ffmpeg_path),
            "-i",
            str(input_file),
            "-ss",
            str(chapter.start_time),
            "-to",
            str(chapter.end_time),
            "-c",
            "copy",
            "-y",
            str(output_file),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ChapterExtractionError(
                f"Failed to extract chapter '{chapter.title}': {e.stderr.decode()}"
            ) from e

    def _merge_segments(
        self,
        segment_files: list[Path],
        output_file: Path,
        temp_dir: Path,
    ) -> None:
        """Merge multiple video segments into a single file.

        Args:
            segment_files: List of paths to segment files to merge.
            output_file: Path where the merged file will be saved.
            temp_dir: Directory for temporary files.

        Raises:
            ChapterExtractionError: If merging fails.
        """
        if not segment_files:
            raise ChapterExtractionError("No segments to merge")

        concat_file = temp_dir / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for segment in segment_files:
                abs_path = segment.resolve()
                f.write(f"file '{abs_path}'\n")

        cmd = [
            str(self.ffmpeg_path),
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-y",
            str(output_file),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ChapterExtractionError(
                f"Failed to merge segments: {e.stderr.decode()}"
            ) from e

    def _filter_chapters(
        self,
        chapters: list[Chapter],
        keyword: str | None = None,
        pattern: str | None = None,
        case_sensitive: bool = False,
        exclude: bool = False,
    ) -> list[Chapter]:
        """Filter chapters using keyword or regex pattern.

        Args:
            chapters: List of Chapter objects to filter.
            keyword: Keyword to search for (mutually exclusive with pattern).
            pattern: Regex pattern to match (mutually exclusive with keyword).
            case_sensitive: Whether matching is case-sensitive.
            exclude: If True, return chapters that don't match.

        Returns:
            List of matching (or non-matching if exclude=True) chapters.

        Raises:
            ValueError: If neither keyword nor pattern is provided.
        """
        if pattern:
            return self.filter_chapters_by_regex(
                chapters, pattern, case_sensitive, exclude
            )
        elif keyword:
            return self.filter_chapters_by_keyword(
                chapters, keyword, case_sensitive, exclude
            )
        else:
            raise ValueError("Either keyword or pattern must be provided")

    def extract_and_merge(
        self,
        input_files: Sequence[str | Path],
        output_file: str | Path,
        keyword: str | None = None,
        pattern: str | None = None,
        case_sensitive: bool = False,
        exclude: bool = False,
        on_progress: Callable[[str, int, int], None] | None = None,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> list[ExtractionResult]:
        """Extract matching chapters from multiple files and merge into one output.

        Args:
            input_files: List of input MKV file paths.
            output_file: Path for the merged output file.
            keyword: Keyword to filter chapters by title (mutually exclusive
                with pattern).
            pattern: Regex pattern to match chapter titles (mutually exclusive
                with keyword).
            case_sensitive: Whether keyword/pattern matching is case-sensitive.
            exclude: If True, extract chapters that do NOT match.
            on_progress: Optional callback for progress updates.
                Called with (current_file, current_index, total_files).
            parallel: If True, use parallel processing for extraction.
            max_workers: Maximum number of worker threads for parallel processing.
                Defaults to number of CPU cores.

        Returns:
            List of ExtractionResult objects, one per input file.

        Raises:
            ChapterExtractionError: If no chapters match or extraction fails.
            ValueError: If neither keyword nor pattern is provided.
        """
        if not keyword and not pattern:
            raise ValueError("Either keyword or pattern must be provided")

        filter_desc = pattern if pattern else keyword

        results: list[ExtractionResult] = []
        output_path = Path(output_file)
        total = len(input_files)

        # Phase 1: Scan all files and collect matching chapters
        file_chapters: list[tuple[Path, list[Chapter]]] = []
        total_matches = 0

        for idx, input_file in enumerate(input_files):
            input_path = Path(input_file)

            if on_progress:
                on_progress(f"Scanning: {input_path}", idx + 1, total)

            # Check if file exists
            if not input_path.exists():
                logger.warning(f"File not found, skipping: {input_path}")
                result = ExtractionResult(
                    source_file=input_path,
                    success=False,
                    error_message="File not found",
                )
                results.append(result)
                continue

            result = ExtractionResult(source_file=input_path)

            try:
                chapters = self.get_chapters(input_path)
                result.chapters_found = len(chapters)

                # Fail if file has no chapter information
                if len(chapters) == 0:
                    raise ChapterExtractionError(
                        f"No chapter information found in '{input_path.name}'"
                    )

                matching = self._filter_chapters(
                    chapters, keyword, pattern, case_sensitive, exclude
                )
                result.chapters_matched = len(matching)

                if matching:
                    file_chapters.append((input_path, matching))
                    total_matches += len(matching)

            except ChapterExtractionError:
                # Re-raise ChapterExtractionError to stop processing
                raise
            except Exception as e:
                result.success = False
                result.error_message = str(e)
                logger.error(f"Failed to process {input_path}: {e}")

            results.append(result)

        # Fail early if no matches found in any file
        if total_matches == 0:
            raise ChapterExtractionError(
                f"No chapters matching '{filter_desc}' found in any input files"
            )

        # Phase 2: Extract segments and merge
        with tempfile.TemporaryDirectory(dir=self._temp_dir) as temp_dir:
            temp_path = Path(temp_dir)
            all_segments: list[Path] = []

            if parallel:
                all_segments = self._extract_segments_parallel(
                    file_chapters, temp_path, results, on_progress, max_workers
                )
            else:
                all_segments = self._extract_segments_sequential(
                    file_chapters, temp_path, results, on_progress
                )

            if all_segments:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._merge_segments(all_segments, output_path, temp_path)

                for result in results:
                    if result.success and result.chapters_extracted:
                        result.output_file = output_path

        return results

    def _extract_segments_sequential(
        self,
        file_chapters: list[tuple[Path, list[Chapter]]],
        temp_path: Path,
        results: list[ExtractionResult],
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> list[Path]:
        """Extract segments sequentially.

        Args:
            file_chapters: List of (input_path, chapters) tuples.
            temp_path: Temporary directory for segment files.
            results: List of ExtractionResult to update.
            on_progress: Optional progress callback.

        Returns:
            List of segment file paths in order.
        """
        all_segments: list[Path] = []

        for input_path, matching in file_chapters:
            if on_progress:
                on_progress(f"Extracting: {input_path}", 0, 0)

            # Find the corresponding result to update
            result = next(r for r in results if r.source_file == input_path)

            try:
                for ch_idx, chapter in enumerate(matching):
                    segment_file = (
                        temp_path / f"{input_path.stem}_segment_{ch_idx}.mkv"
                    )
                    self._extract_segment(input_path, chapter, segment_file)
                    all_segments.append(segment_file)
                    result.chapters_extracted.append(chapter)

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                logger.error(f"Failed to extract from {input_path}: {e}")

        return all_segments

    def _extract_segments_parallel(
        self,
        file_chapters: list[tuple[Path, list[Chapter]]],
        temp_path: Path,
        results: list[ExtractionResult],
        on_progress: Callable[[str, int, int], None] | None = None,
        max_workers: int | None = None,
    ) -> list[Path]:
        """Extract segments in parallel using thread pool.

        Args:
            file_chapters: List of (input_path, chapters) tuples.
            temp_path: Temporary directory for segment files.
            results: List of ExtractionResult to update.
            on_progress: Optional progress callback.
            max_workers: Maximum number of worker threads.

        Returns:
            List of segment file paths in order.
        """
        # Build a list of all extraction tasks with ordering info
        tasks: list[tuple[int, Path, int, Chapter, Path]] = []
        global_idx = 0
        for input_path, matching in file_chapters:
            for ch_idx, chapter in enumerate(matching):
                segment_file = temp_path / f"{input_path.stem}_segment_{ch_idx}.mkv"
                tasks.append((global_idx, input_path, ch_idx, chapter, segment_file))
                global_idx += 1

        # Results storage: segment_file indexed by global_idx
        segment_results: dict[int, Path] = {}
        extraction_errors: dict[Path, str] = {}

        def extract_task(
            task: tuple[int, Path, int, Chapter, Path],
        ) -> tuple[int, Path, Path, Chapter, Exception | None]:
            idx, input_path, ch_idx, chapter, segment_file = task
            try:
                self._extract_segment(input_path, chapter, segment_file)
                return (idx, input_path, segment_file, chapter, None)
            except Exception as e:
                return (idx, input_path, segment_file, chapter, e)

        total_tasks = len(tasks)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(extract_task, task): task for task in tasks}

            for future in as_completed(futures):
                idx, input_path, segment_file, chapter, error = future.result()
                completed += 1

                if on_progress:
                    on_progress(f"Extracted: {chapter.title}", completed, total_tasks)

                if error:
                    extraction_errors[input_path] = str(error)
                    logger.error(f"Failed to extract {chapter.title}: {error}")
                else:
                    segment_results[idx] = segment_file
                    # Update the result
                    result = next(r for r in results if r.source_file == input_path)
                    result.chapters_extracted.append(chapter)

        # Mark failed files
        for input_path, error_msg in extraction_errors.items():
            result = next(r for r in results if r.source_file == input_path)
            result.success = False
            result.error_message = error_msg

        # Return segments in order
        return [segment_results[i] for i in sorted(segment_results.keys())]

    def extract_to_separate_files(
        self,
        input_files: Sequence[str | Path],
        keyword: str | None = None,
        pattern: str | None = None,
        output_dir: str | Path | None = None,
        case_sensitive: bool = False,
        exclude: bool = False,
        output_suffix: str = "_filtered",
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> list[ExtractionResult]:
        """Extract matching chapters from each file into separate output files.

        Args:
            input_files: List of input MKV file paths.
            keyword: Keyword to filter chapters by title (mutually exclusive
                with pattern).
            pattern: Regex pattern to match chapter titles (mutually exclusive
                with keyword).
            output_dir: Directory for output files. If None, outputs are placed
                in the same directory as their source files.
            case_sensitive: Whether keyword/pattern matching is case-sensitive.
            exclude: If True, extract chapters that do NOT match.
            output_suffix: Suffix to append to output filenames.
            on_progress: Optional callback for progress updates.

        Returns:
            List of ExtractionResult objects, one per input file.

        Raises:
            ValueError: If neither keyword nor pattern is provided.
        """
        if not keyword and not pattern:
            raise ValueError("Either keyword or pattern must be provided")

        results: list[ExtractionResult] = []
        output_path = Path(output_dir) if output_dir else None

        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=self._temp_dir) as temp_dir:
            temp_path = Path(temp_dir)
            total = len(input_files)

            for idx, input_file in enumerate(input_files):
                input_path = Path(input_file)

                if on_progress:
                    on_progress(str(input_path), idx + 1, total)

                # Check if file exists
                if not input_path.exists():
                    logger.warning(f"File not found, skipping: {input_path}")
                    result = ExtractionResult(
                        source_file=input_path,
                        success=False,
                        error_message="File not found",
                    )
                    results.append(result)
                    continue

                result = ExtractionResult(source_file=input_path)

                try:
                    chapters = self.get_chapters(input_path)
                    result.chapters_found = len(chapters)

                    # Fail if file has no chapter information
                    if len(chapters) == 0:
                        raise ChapterExtractionError(
                            f"No chapter information found in '{input_path.name}'"
                        )

                    matching = self._filter_chapters(
                        chapters, keyword, pattern, case_sensitive, exclude
                    )
                    result.chapters_matched = len(matching)

                    if not matching:
                        results.append(result)
                        continue

                    segments: list[Path] = []
                    for ch_idx, chapter in enumerate(matching):
                        segment_file = (
                            temp_path / f"{input_path.stem}_segment_{ch_idx}.mkv"
                        )
                        self._extract_segment(input_path, chapter, segment_file)
                        segments.append(segment_file)
                        result.chapters_extracted.append(chapter)

                    # Determine output path
                    if output_path:
                        out_file = output_path / f"{input_path.stem}{output_suffix}.mkv"
                    else:
                        out_file = (
                            input_path.parent / f"{input_path.stem}{output_suffix}.mkv"
                        )

                    self._merge_segments(segments, out_file, temp_path)
                    result.output_file = out_file

                except ChapterExtractionError:
                    # Re-raise ChapterExtractionError to stop processing
                    raise
                except Exception as e:
                    result.success = False
                    result.error_message = str(e)
                    logger.error(f"Failed to process {input_path}: {e}")

                results.append(result)

        return results


def is_supported_format(file_path: str | Path) -> bool:
    """Check if a file has a supported video format extension.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file extension is supported, False otherwise.
    """
    return Path(file_path).suffix.lower() in SUPPORTED_FORMATS


def validate_format(file_path: str | Path) -> None:
    """Validate that a file has a supported video format extension.

    Args:
        file_path: Path to the file to validate.

    Raises:
        UnsupportedFormatError: If the file format is not supported.
    """
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported format '{path.suffix}' for file '{path.name}'. "
            f"Supported formats: {supported}"
        )


def resolve_input_files(
    input_pattern: str | list[str | Path],
    filter_supported: bool = True,
) -> list[Path]:
    """Resolve input files from a glob pattern or list of paths.

    Args:
        input_pattern: Either a glob pattern string or a list of file paths.
        filter_supported: If True, only return files with supported formats.
            Defaults to True.

    Returns:
        Sorted list of Path objects for matching files.

    Raises:
        ValueError: If the input type is invalid.
        FileNotFoundError: If no files match the pattern.
    """
    if isinstance(input_pattern, str):
        files = sorted(Path(p) for p in glob(input_pattern))
        if not files:
            raise FileNotFoundError(f"No files found matching pattern: {input_pattern}")
    elif isinstance(input_pattern, list):
        files = sorted(Path(p) for p in input_pattern)
    else:
        raise ValueError(
            "input_pattern must be a string (glob pattern) or list of file paths"
        )

    if filter_supported:
        files = [f for f in files if is_supported_format(f)]

    return files


def extract_chapters(
    input_pattern: str | list[str | Path],
    output_file: str | Path,
    keyword: str | None = None,
    pattern: str | None = None,
    case_sensitive: bool = False,
    exclude: bool = False,
    parallel: bool = False,
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    r"""Convenience function to extract and merge chapters from MKV files.

    Args:
        input_pattern: Glob pattern or list of input file paths.
        output_file: Path for the merged output file.
        keyword: Keyword to filter chapters by title.
        pattern: Regex pattern to match chapter titles.
        case_sensitive: Whether matching is case-sensitive.
        exclude: If True, extract chapters that do NOT match.
        parallel: If True, use parallel processing for extraction.
        max_workers: Maximum number of worker threads for parallel processing.

    Returns:
        List of ExtractionResult objects.

    Example:
        >>> results = extract_chapters(
        ...     r"C:\\Videos\\*.mkv",
        ...     "output.mkv",
        ...     keyword="Episode"
        ... )
    """
    input_files = resolve_input_files(input_pattern)
    extractor = ChapterExtractor()
    return extractor.extract_and_merge(
        input_files,
        output_file,
        keyword=keyword,
        pattern=pattern,
        case_sensitive=case_sensitive,
        exclude=exclude,
        parallel=parallel,
        max_workers=max_workers,
    )


def extract_chapters_to_separate_files(
    input_pattern: str | list[str | Path],
    keyword: str | None = None,
    pattern: str | None = None,
    output_dir: str | Path | None = None,
    case_sensitive: bool = False,
    exclude: bool = False,
    output_suffix: str = "_filtered",
) -> list[ExtractionResult]:
    r"""Convenience function to extract chapters to separate output files.

    Args:
        input_pattern: Glob pattern or list of input file paths.
        keyword: Keyword to filter chapters by title.
        pattern: Regex pattern to match chapter titles.
        output_dir: Directory for output files. Defaults to source directories.
        case_sensitive: Whether matching is case-sensitive.
        exclude: If True, extract chapters that do NOT match.
        output_suffix: Suffix to append to output filenames.

    Returns:
        List of ExtractionResult objects.

    Example:
        >>> results = extract_chapters_to_separate_files(
        ...     r"C:\\Videos\\*.mkv",
        ...     keyword="Episode",
        ...     output_dir=r"C:\\Videos\\filtered"
        ... )
    """
    input_files = resolve_input_files(input_pattern)
    extractor = ChapterExtractor()
    return extractor.extract_to_separate_files(
        input_files,
        keyword=keyword,
        pattern=pattern,
        output_dir=output_dir,
        case_sensitive=case_sensitive,
        exclude=exclude,
        output_suffix=output_suffix,
    )
