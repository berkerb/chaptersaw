"""Command-line interface for Chaptersaw.

This module provides a CLI for extracting chapters from video files
using argparse.
"""

import argparse
import logging
import sys
from pathlib import Path

from chaptersaw import __version__
from chaptersaw.exceptions import (
    ChapterExtractionError,
    FFmpegNotFoundError,
)
from chaptersaw.extractor import (
    ChapterExtractor,
    resolve_input_files,
)

# Try to import rich for progress bar support
try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="chaptersaw",
        description=(
            "Extract and merge specific chapters from video files based on "
            "chapter title keywords or regex patterns."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s -i 'videos/*.mkv' -k Episode -o merged.mkv\n"
            "  %(prog)s -i 'videos/*.mkv' -k Episode --separate -d output/\n"
            "  %(prog)s -i video1.mkv -i video2.mkv -k 'Part A' -o output.mkv\n"
            "  %(prog)s -i video.mkv --list-chapters\n"
            "  %(prog)s -i 'videos/*.mkv' -r 'Episode \\d+' -o merged.mkv\n"
            "  %(prog)s -i video.mkv -k Credits --exclude -o no_credits.mkv\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Input options
    input_group = parser.add_argument_group("Input options")
    input_group.add_argument(
        "-i",
        "--input",
        dest="inputs",
        action="append",
        required=True,
        metavar="PATH",
        help=(
            "Input file path or glob pattern. Can be specified multiple times. "
            "Use quotes around glob patterns to prevent shell expansion."
        ),
    )

    # Filter options
    filter_group = parser.add_argument_group("Filter options")
    filter_mode = filter_group.add_mutually_exclusive_group()
    filter_mode.add_argument(
        "-k",
        "--keyword",
        metavar="KEYWORD",
        help="Keyword to search for in chapter titles.",
    )
    filter_mode.add_argument(
        "-r",
        "--regex",
        metavar="PATTERN",
        help="Regular expression pattern to match chapter titles.",
    )
    filter_group.add_argument(
        "-c",
        "--case-sensitive",
        action="store_true",
        help="Make keyword/regex matching case-sensitive (default: case-insensitive).",
    )
    filter_group.add_argument(
        "-e",
        "--exclude",
        action="store_true",
        help="Exclude matching chapters instead of including them.",
    )

    # Output options
    output_group = parser.add_argument_group("Output options")
    output_mode = output_group.add_mutually_exclusive_group()
    output_mode.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file path for merged result (merge mode).",
    )
    output_mode.add_argument(
        "-s",
        "--separate",
        action="store_true",
        help="Create separate output files for each input file.",
    )
    output_mode.add_argument(
        "-l",
        "--list-chapters",
        action="store_true",
        help="List all chapters in input files without extracting.",
    )
    output_group.add_argument(
        "-d",
        "--output-dir",
        metavar="DIR",
        help=(
            "Output directory for separate files. "
            "If not specified, files are saved alongside inputs."
        ),
    )
    output_group.add_argument(
        "--suffix",
        default="_filtered",
        metavar="SUFFIX",
        help="Suffix for output filenames in separate mode (default: _filtered).",
    )

    # Behavior options
    behavior_group = parser.add_argument_group("Behavior options")
    behavior_group.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually extracting.",
    )
    behavior_group.add_argument(
        "-p",
        "--parallel",
        action="store_true",
        help="Use parallel processing for faster extraction.",
    )
    behavior_group.add_argument(
        "-w",
        "--workers",
        type=int,
        metavar="N",
        help="Number of parallel workers (default: CPU count).",
    )
    behavior_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    behavior_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors.",
    )
    behavior_group.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar (uses simple text output).",
    )

    return parser


def print_progress(file: str, current: int, total: int) -> None:
    """Print progress information."""
    print(f"[{current}/{total}] Processing: {file}")


def list_chapters(
    extractor: ChapterExtractor, input_files: list[Path], use_rich: bool = True
) -> None:
    """List all chapters in the input files."""
    if use_rich and RICH_AVAILABLE:
        console = Console()

        for input_file in input_files:
            try:
                chapters = extractor.get_chapters(input_file)

                table = Table(title=f"Chapters in {input_file.name}")
                table.add_column("#", style="cyan", justify="right")
                table.add_column("Title", style="green")
                table.add_column("Start", style="yellow", justify="right")
                table.add_column("End", style="yellow", justify="right")
                table.add_column("Duration", style="magenta", justify="right")

                for idx, ch in enumerate(chapters, 1):
                    table.add_row(
                        str(idx),
                        ch.title,
                        f"{ch.start_time:.2f}s",
                        f"{ch.end_time:.2f}s",
                        f"{ch.duration:.2f}s",
                    )

                console.print(table)
                console.print()

            except ChapterExtractionError as e:
                console.print(f"[red]Error reading {input_file}: {e}[/red]")
    else:
        for input_file in input_files:
            print(f"\nChapters in {input_file.name}:")
            print("-" * 60)

            try:
                chapters = extractor.get_chapters(input_file)

                if not chapters:
                    print("  No chapters found")
                    continue

                for idx, ch in enumerate(chapters, 1):
                    print(
                        f"  {idx:3d}. {ch.title:<30} "
                        f"[{ch.start_time:.2f}s - {ch.end_time:.2f}s] "
                        f"({ch.duration:.2f}s)"
                    )

            except ChapterExtractionError as e:
                print(f"  Error: {e}")


def run_dry_run(
    extractor: ChapterExtractor,
    input_files: list[Path],
    keyword: str | None,
    pattern: str | None,
    case_sensitive: bool,
    exclude: bool,
) -> None:
    """Execute a dry run showing what would be extracted."""
    print("\n=== DRY RUN ===\n")

    filter_desc = pattern if pattern else keyword
    mode = "Excluding" if exclude else "Matching"

    total_matched = 0
    for input_file in input_files:
        print(f"File: {input_file}")
        try:
            chapters = extractor.get_chapters(input_file)

            if pattern:
                matching = extractor.filter_chapters_by_regex(
                    chapters, pattern, case_sensitive, exclude
                )
            else:
                matching = extractor.filter_chapters_by_keyword(
                    chapters, keyword or "", case_sensitive, exclude
                )

            print(f"  Total chapters: {len(chapters)}")
            print(f"  {mode} '{filter_desc}': {len(matching)}")

            for chapter in matching:
                print(f"    - {chapter}")

            total_matched += len(matching)
        except Exception as e:
            print(f"  Error: {e}")
        print()

    print(f"Total chapters to extract: {total_matched}")


class RichProgressCallback:
    """Progress callback using rich library."""

    def __init__(self, total: int, description: str = "Processing") -> None:
        """Initialize the progress callback."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        )
        self.task_id = self.progress.add_task(description, total=total)
        self.progress.start()

    def __call__(self, file: str, current: int, total: int) -> None:
        """Update progress."""
        self.progress.update(
            self.task_id, completed=current, description=f"Processing: {file[:50]}"
        )

    def stop(self) -> None:
        """Stop the progress bar."""
        self.progress.stop()


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose, quiet=args.quiet)
    logger = logging.getLogger(__name__)

    # Validate arguments
    if args.output_dir and not args.separate:
        parser.error("--output-dir can only be used with --separate")

    if args.workers and not args.parallel:
        parser.error("--workers can only be used with --parallel")

    # Check if we need a filter (keyword or regex)
    needs_filter = not args.list_chapters
    if needs_filter and not args.keyword and not args.regex:
        parser.error("Either -k/--keyword or -r/--regex is required for extraction")

    # Check if we need an output mode
    if needs_filter and not args.output and not args.separate:
        parser.error("Either -o/--output or -s/--separate is required for extraction")

    # Resolve input files
    try:
        input_files: list[Path] = []
        for input_pattern in args.inputs:
            input_files.extend(resolve_input_files(input_pattern))

        if not input_files:
            logger.error("No input files found")
            return 1

        # Remove duplicates while preserving order
        seen: set[Path] = set()
        unique_files: list[Path] = []
        for f in input_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        input_files = unique_files

        logger.info(f"Found {len(input_files)} input file(s)")

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    # Initialize extractor
    try:
        extractor = ChapterExtractor()
    except FFmpegNotFoundError as e:
        logger.error(str(e))
        return 1

    # List chapters mode
    if args.list_chapters:
        use_rich = RICH_AVAILABLE and not args.no_progress and not args.quiet
        list_chapters(extractor, input_files, use_rich)
        return 0

    # Dry run mode
    if args.dry_run:
        run_dry_run(
            extractor,
            input_files,
            args.keyword,
            args.regex,
            args.case_sensitive,
            args.exclude,
        )
        return 0

    # Execute extraction
    try:
        # Set up progress callback
        use_rich_progress = (
            RICH_AVAILABLE and not args.no_progress and not args.quiet
        )

        from collections.abc import Callable

        progress_callback: Callable[[str, int, int], None] | None = None
        rich_progress: RichProgressCallback | None = None

        if not args.quiet:
            if use_rich_progress:
                rich_progress = RichProgressCallback(
                    len(input_files), "Extracting chapters"
                )
                progress_callback = rich_progress
            else:
                progress_callback = print_progress

        if args.separate:
            results = extractor.extract_to_separate_files(
                input_files,
                keyword=args.keyword,
                pattern=args.regex,
                output_dir=args.output_dir,
                case_sensitive=args.case_sensitive,
                exclude=args.exclude,
                output_suffix=args.suffix,
                on_progress=progress_callback,
            )
        else:
            results = extractor.extract_and_merge(
                input_files,
                output_file=args.output,
                keyword=args.keyword,
                pattern=args.regex,
                case_sensitive=args.case_sensitive,
                exclude=args.exclude,
                on_progress=progress_callback,
                parallel=args.parallel,
                max_workers=args.workers,
            )

        if rich_progress:
            rich_progress.stop()

        # Print summary
        if not args.quiet:
            print("\n=== Summary ===")
            total_extracted = 0
            failed = 0

            for result in results:
                if result.success:
                    total_extracted += len(result.chapters_extracted)
                    if result.chapters_extracted:
                        logger.info(f"  {result}")
                else:
                    failed += 1
                    logger.error(
                        f"  FAILED: {result.source_file} - {result.error_message}"
                    )

            print(f"\nTotal chapters extracted: {total_extracted}")
            if failed:
                print(f"Failed files: {failed}")

            if args.separate:
                output_files = [r.output_file for r in results if r.output_file]
                print(f"Output files created: {len(output_files)}")
            elif results and results[0].output_file:
                print(f"Output file: {results[0].output_file}")

        return 0 if all(r.success for r in results) else 1

    except ChapterExtractionError as e:
        if rich_progress:
            rich_progress.stop()
        logger.error(f"Extraction failed: {e}")
        return 1
    except Exception as e:
        if rich_progress:
            rich_progress.stop()
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
