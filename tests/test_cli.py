"""Tests for the CLI module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chaptersaw.cli import create_parser, main


class TestCreateParser:
    """Tests for the argument parser."""

    def test_parser_requires_input(self) -> None:
        """Test that parser requires input argument."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-k", "Episode", "-o", "out.mkv"])

    def test_parser_accepts_no_keyword_for_list_chapters(self) -> None:
        """Test that parser accepts no keyword when listing chapters."""
        parser = create_parser()
        # Should not raise since --list-chapters doesn't need a keyword
        args = parser.parse_args(["-i", "test.mkv", "-l"])
        assert args.list_chapters is True
        assert args.keyword is None

    def test_main_requires_keyword_for_extraction(self, tmp_path: "Path") -> None:
        """Test that main requires keyword/regex for extraction."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        with (
            patch("chaptersaw.cli.ChapterExtractor"),
            pytest.raises(SystemExit),
        ):
            # No keyword or regex, should fail
            main(["-i", str(test_file), "-o", "out.mkv"])

    def test_main_requires_output_for_extraction(self, tmp_path: "Path") -> None:
        """Test that main requires output for extraction."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        with (
            patch("chaptersaw.cli.ChapterExtractor"),
            pytest.raises(SystemExit),
        ):
            # Has keyword but no output mode
            main(["-i", str(test_file), "-k", "Episode"])

    def test_parser_output_mutually_exclusive(self) -> None:
        """Test that -o and -s are mutually exclusive."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["-i", "test.mkv", "-k", "Episode", "-o", "out.mkv", "-s"]
            )

    def test_parser_merge_mode(self) -> None:
        """Test parser in merge mode."""
        parser = create_parser()
        args = parser.parse_args(
            ["-i", "test.mkv", "-k", "Episode", "-o", "output.mkv"]
        )
        assert args.inputs == ["test.mkv"]
        assert args.keyword == "Episode"
        assert args.output == "output.mkv"
        assert args.separate is False

    def test_parser_separate_mode(self) -> None:
        """Test parser in separate mode."""
        parser = create_parser()
        args = parser.parse_args(
            ["-i", "test.mkv", "-k", "Episode", "-s", "-d", "output/"]
        )
        assert args.separate is True
        assert args.output_dir == "output/"

    def test_parser_multiple_inputs(self) -> None:
        """Test parser with multiple input arguments."""
        parser = create_parser()
        args = parser.parse_args(
            ["-i", "test1.mkv", "-i", "test2.mkv", "-k", "Episode", "-o", "out.mkv"]
        )
        assert args.inputs == ["test1.mkv", "test2.mkv"]

    def test_parser_optional_flags(self) -> None:
        """Test parser optional flags."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "-i", "test.mkv",
                "-k", "Episode",
                "-o", "out.mkv",
                "-c",
                "-v",
                "-n",
            ]
        )
        assert args.case_sensitive is True
        assert args.verbose is True
        assert args.dry_run is True


class TestMain:
    """Tests for the main function."""

    @pytest.fixture
    def mock_extractor(self) -> MagicMock:
        """Create a mock ChapterExtractor."""
        with patch(
            "chaptersaw.cli.ChapterExtractor"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            yield mock_instance

    def test_main_no_files_found(self, tmp_path: Path) -> None:
        """Test main returns error when no files found."""
        with patch("chaptersaw.cli.ChapterExtractor"):
            exit_code = main(
                [
                    "-i", str(tmp_path / "*.mkv"),
                    "-k", "Episode",
                    "-o", "out.mkv",
                ]
            )
        assert exit_code == 1

    def test_main_ffmpeg_not_found(self, tmp_path: Path) -> None:
        """Test main returns error when ffmpeg not found."""
        from chaptersaw.extractor import FFmpegNotFoundError

        test_file = tmp_path / "test.mkv"
        test_file.touch()

        with patch(
            "chaptersaw.cli.ChapterExtractor"
        ) as mock_class:
            mock_class.side_effect = FFmpegNotFoundError("FFmpeg not found")
            exit_code = main(
                [
                    "-i", str(test_file),
                    "-k", "Episode",
                    "-o", "out.mkv",
                ]
            )
        assert exit_code == 1

    def test_main_output_dir_without_separate(self, tmp_path: Path) -> None:
        """Test main errors when --output-dir used without --separate."""
        test_file = tmp_path / "test.mkv"
        test_file.touch()

        with patch("chaptersaw.cli.ChapterExtractor"):
            with pytest.raises(SystemExit) as exc_info:
                main(
                    [
                        "-i", str(test_file),
                        "-k", "Episode",
                        "-o", "out.mkv",
                        "-d", "output/",
                    ]
                )
            assert exc_info.value.code != 0
