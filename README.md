# Chaptersaw

Extract and merge specific chapters from video files based on chapter title keywords or regex patterns.

## Features

- **Multi-format support**: MKV, MP4, M4V, AVI, WebM, TS, M2TS
- **Flexible filtering**: Match chapters by keyword or regex pattern
- **Exclude mode**: Filter out unwanted chapters (e.g., skip intros/credits)
- **Merge mode**: Combine chapters from multiple files into a single output
- **Separate mode**: Create individual output files for each input
- **Glob patterns**: Process multiple files with wildcards
- **Parallel processing**: Speed up extraction with multi-threading
- **Progress bar**: Visual feedback with rich library
- **Dry-run mode**: Preview what will be extracted
- **Python API**: Full programmatic access

## Requirements

- Python 3.11+
- FFmpeg (must be installed and in PATH)

## Installation

```bash
# Using uv
uv pip install chaptersaw

# Using pip
pip install chaptersaw

# From source
git clone https://github.com/berkerbozdag/chaptersaw.git
cd chaptersaw
uv pip install -e .
```

## Usage

### Command Line

```bash
# Merge all "Episode" chapters from multiple files into one
chaptersaw -i "videos/*.mkv" -k Episode -o merged.mkv

# Use regex pattern to match chapters
chaptersaw -i "videos/*.mkv" -r "Episode \d+" -o merged.mkv

# Exclude chapters (e.g., remove intros and credits)
chaptersaw -i video.mkv -k "Opening|Credits" --exclude -o no_extras.mkv

# List all chapters in a file
chaptersaw -i video.mkv --list-chapters

# Create separate output files for each input
chaptersaw -i "videos/*.mkv" -k Episode --separate -d output/

# Multiple input files (supports MP4, AVI, WebM, etc.)
chaptersaw -i video1.mp4 -i video2.mkv -k "Part A" -o output.mkv

# Dry run to preview what will be extracted
chaptersaw -i "videos/*.mkv" -k Episode -o merged.mkv --dry-run

# Enable parallel processing for faster extraction
chaptersaw -i "videos/*.mkv" -k Episode -o merged.mkv --parallel

# Case-sensitive matching
chaptersaw -i "videos/*.mkv" -k Episode -o merged.mkv --case-sensitive
```

### Python API

```python
from chaptersaw import (
    ChapterExtractor,
    extract_chapters,
    extract_chapters_to_separate_files,
    SUPPORTED_FORMATS,
    is_supported_format,
    ChaptersawError,
)

# Check supported formats
print(SUPPORTED_FORMATS)  # frozenset({'.mkv', '.mp4', '.m4v', '.avi', '.webm', '.ts', '.m2ts'})

# Validate file format
if is_supported_format("video.mp4"):
    print("Format supported!")

# Simple usage with convenience functions
results = extract_chapters(
    input_pattern=r"C:\Videos\*.mkv",
    output_file="merged.mkv",
    keyword="Episode",
)

# Use regex pattern
results = extract_chapters(
    input_pattern="videos/*.mp4",
    output_file="merged.mkv",
    pattern=r"Episode \d+",
)

# Exclude matching chapters
results = extract_chapters(
    input_pattern="video.mkv",
    output_file="no_credits.mkv",
    keyword="Credits",
    exclude=True,
)

# Create separate files
results = extract_chapters_to_separate_files(
    input_pattern=r"C:\Videos\*.mkv",
    keyword="Episode",
    output_dir=r"C:\Videos\filtered",
)

# Full control with ChapterExtractor class
extractor = ChapterExtractor()

# Get all chapters from a file
chapters = extractor.get_chapters("video.mkv")
for chapter in chapters:
    print(f"{chapter.title}: {chapter.start_time}s - {chapter.end_time}s")

# Filter by keyword
matching = extractor.filter_chapters_by_keyword(chapters, "Episode")

# Filter by regex
matching = extractor.filter_chapters_by_regex(chapters, r"Episode \d+")

# Exclude chapters
non_credits = extractor.filter_chapters_by_keyword(
    chapters, "Credits", exclude=True
)

# Custom filtering
long_chapters = extractor.filter_chapters_by_predicate(
    chapters,
    lambda ch: ch.duration > 300  # Chapters longer than 5 minutes
)

# Extract and merge with parallel processing
results = extractor.extract_and_merge(
    input_files=["video1.mkv", "video2.mp4"],
    output_file="merged.mkv",
    keyword="Episode",
    parallel=True,
    max_workers=4,
)

# Check results
for result in results:
    print(f"{result.source_file}: {result.chapters_matched} chapters matched")
    if result.success:
        print(f"  Output: {result.output_file}")
    else:
        print(f"  Error: {result.error_message}")

# Catch all package errors
try:
    extractor.extract_and_merge(...)
except ChaptersawError as e:
    print(f"Extraction failed: {e}")
```

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Matroska | `.mkv` | Full chapter support |
| MP4 | `.mp4`, `.m4v` | Chapter support varies |
| AVI | `.avi` | Limited chapter support |
| WebM | `.webm` | Chapter support |
| MPEG-TS | `.ts`, `.m2ts` | Broadcast recordings |

## CLI Reference

```
usage: chaptersaw [-h] [-V] -i PATH [-k KEYWORD | -r PATTERN]
                  [-c] [-e] (-o FILE | -s | -l) [-d DIR]
                  [--suffix SUFFIX] [-n] [-p] [-w N] [-v] [-q]
                  [--no-progress]

Extract and merge specific chapters from video files based on chapter title
keywords or regex patterns.

Input options:
  -i, --input PATH       Input file path or glob pattern (can be repeated)

Filter options:
  -k, --keyword KEYWORD  Keyword to search for in chapter titles
  -r, --regex PATTERN    Regular expression pattern to match chapter titles
  -c, --case-sensitive   Make keyword/regex matching case-sensitive
  -e, --exclude          Exclude matching chapters instead of including them

Output options:
  -o, --output FILE      Output file path for merged result
  -s, --separate         Create separate output files for each input
  -l, --list-chapters    List all chapters in input files without extracting
  -d, --output-dir DIR   Output directory for separate files
  --suffix SUFFIX        Suffix for output filenames (default: _filtered)

Behavior options:
  -n, --dry-run          Show what would be done without extracting
  -p, --parallel         Use parallel processing for faster extraction
  -w, --workers N        Number of parallel workers (default: CPU count)
  -v, --verbose          Enable verbose output
  -q, --quiet            Suppress all output except errors
  --no-progress          Disable progress bar
```

## License

MIT License
