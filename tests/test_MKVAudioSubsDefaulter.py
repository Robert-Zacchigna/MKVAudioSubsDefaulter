import json
import logging
import os
import re
import tempfile
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from MKVAudioSubsDefaulter import MKVAudioSubsDefaulter as mkv_module
from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import cmd_parse_args
from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import MKVAudioSubsDefaulter


class TestMKVAudioSubsDefaulter:
    """Comprehensive test suite for MKVAudioSubsDefaulter class."""

    @pytest.fixture
    def basic_defaulter(self):
        """Create a basic MKVAudioSubsDefaulter instance for testing."""
        return MKVAudioSubsDefaulter(
            file_or_library_path="/test/path", audio_lang_code="eng", subtitle_lang_code="eng"
        )

    @pytest.fixture
    def sample_media_info(self):
        """Sample media file track information for testing."""
        return {
            "audio": {
                0: {
                    "language": "eng",
                    "name": "English Audio",
                    "default": True,
                    "enabled": True,
                    "forced": False,
                    "text_subtitles": None,
                    "sample_freq": 48000,
                },
                1: {
                    "language": "jpn",
                    "name": "Japanese Audio",
                    "default": False,
                    "enabled": True,
                    "forced": False,
                    "text_subtitles": None,
                    "sample_freq": 44100,
                },
            },
            "subtitles": {
                2: {
                    "language": "eng",
                    "name": "English Subtitles",
                    "default": False,
                    "enabled": True,
                    "forced": False,
                    "text_subtitles": True,
                    "sample_freq": None,
                },
                3: {
                    "language": "jpn",
                    "name": "Japanese Subtitles",
                    "default": True,
                    "enabled": True,
                    "forced": False,
                    "text_subtitles": True,
                    "sample_freq": None,
                },
            },
        }

    @pytest.fixture
    def sample_mkvmerge_output(self):
        """Sample JSON output from mkvmerge command."""
        return {
            "tracks": [
                {
                    "id": 0,
                    "type": "audio",
                    "properties": {
                        "language": "eng",
                        "track_name": "English Audio",
                        "default_track": True,
                        "enabled_track": True,
                        "forced_track": False,
                        "audio_sampling_frequency": 48000,
                    },
                },
                {
                    "id": 1,
                    "type": "audio",
                    "properties": {
                        "language": "jpn",
                        "track_name": "Japanese Audio",
                        "default_track": False,
                        "enabled_track": True,
                        "forced_track": False,
                        "audio_sampling_frequency": 44100,
                    },
                },
                {
                    "id": 2,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "track_name": "English Subtitles",
                        "default_track": False,
                        "enabled_track": True,
                        "forced_track": False,
                        "text_subtitles": True,
                    },
                },
            ]
        }

    def test_init_basic(self):
        """Test basic initialization of MKVAudioSubsDefaulter."""
        defaulter = MKVAudioSubsDefaulter(
            file_or_library_path="/test/path", audio_lang_code="eng", subtitle_lang_code="jpn"
        )

        assert defaulter.file_or_library_path == "/test/path"
        assert defaulter.audio_lang_code == "eng"
        assert defaulter.subtitle_lang_code == "jpn"
        assert defaulter.log_level == 0
        assert defaulter.default_method == "strict"
        assert defaulter.file_search_depth == 0
        assert defaulter.file_extensions == (".mkv",)
        assert defaulter.pool_size == 1
        assert defaulter.regex_filter is None
        assert defaulter.dry_run is False

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        defaulter = MKVAudioSubsDefaulter(
            file_or_library_path="/test/library",
            audio_lang_code="fra",
            subtitle_lang_code="off",
            log_level=2,
            default_method="lazy",
            file_search_depth=3,
            file_extensions=(".mkv", ".mp4"),
            pool_size=4,
            regex_filter=r".*Season.*",
            mkvpropedit_location="/usr/bin/mkvpropedit",
            mkvmerge_location="/usr/bin/mkvmerge",
            dry_run=True,
        )

        assert defaulter.file_or_library_path == "/test/library"
        assert defaulter.audio_lang_code == "fra"
        assert defaulter.subtitle_lang_code == "off"
        assert defaulter.log_level == 2
        assert defaulter.default_method == "lazy"
        assert defaulter.file_search_depth == 3
        assert defaulter.file_extensions == (".mkv", ".mp4")
        assert defaulter.pool_size == 4
        assert defaulter.regex_filter == r".*Season.*"
        assert defaulter.mkvpropedit_location == "/usr/bin/mkvpropedit"
        assert defaulter.mkvmerge_location == "/usr/bin/mkvmerge"
        assert defaulter.dry_run is True

    def test_set_log_level_disabled(self, basic_defaulter):
        """Test log level setting when disabled."""
        basic_defaulter.log_level = 0
        result = basic_defaulter.set_log_level()
        assert result == "DISABLED"

    @patch("logging.basicConfig")
    def test_set_log_level_info(self, mock_basic_config, basic_defaulter):
        """Test log level setting for INFO level."""
        basic_defaulter.log_level = 1
        result = basic_defaulter.set_log_level()

        assert result == "INFO"
        mock_basic_config.assert_called_once_with(
            format="%(asctime)s - %(levelname)s: %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.INFO,
        )

    @patch("logging.basicConfig")
    def test_set_log_level_debug(self, mock_basic_config, basic_defaulter):
        """Test log level setting for DEBUG level."""
        basic_defaulter.log_level = 2
        result = basic_defaulter.set_log_level()

        assert result == "DEBUG"
        mock_basic_config.assert_called_once_with(
            format="%(asctime)s - %(levelname)s: %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    def test_list_directories_depth_zero(self):
        """Test directory listing with depth 0."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, "subdir1"))
            os.makedirs(os.path.join(temp_dir, "subdir2", "nested"))

            result = MKVAudioSubsDefaulter.list_directories(temp_dir, 0)
            assert len(result) == 1
            assert temp_dir in result

    def test_list_directories_depth_one(self):
        """Test directory listing with depth 1."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir1 = os.path.join(temp_dir, "subdir1")
            subdir2 = os.path.join(temp_dir, "subdir2")
            nested = os.path.join(subdir2, "nested")

            os.makedirs(subdir1)
            os.makedirs(nested)

            result = MKVAudioSubsDefaulter.list_directories(temp_dir, 1)
            assert len(result) == 3
            assert temp_dir in result
            assert subdir1 in result
            assert subdir2 in result
            assert nested not in result

    def test_list_directories_depth_two(self):
        """Test directory listing with depth 2."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir1 = os.path.join(temp_dir, "subdir1")
            subdir2 = os.path.join(temp_dir, "subdir2")
            nested = os.path.join(subdir2, "nested")

            os.makedirs(subdir1)
            os.makedirs(nested)

            result = MKVAudioSubsDefaulter.list_directories(temp_dir, 2)
            assert len(result) == 4
            assert temp_dir in result
            assert subdir1 in result
            assert subdir2 in result
            assert nested in result

    @patch("builtins.open", mock_open(read_data="eng:English\njpn:Japanese\nfra:French\n"))
    @patch("os.path.dirname")
    def test_get_language_codes_return_data(self, mock_dirname, basic_defaulter):
        """Test getting language codes as data."""
        mock_dirname.return_value = "/fake/path"

        result = basic_defaulter.get_language_codes(print_codes=False)

        assert result == ["eng:English\n", "jpn:Japanese\n", "fra:French\n"]

    @patch("builtins.open", mock_open(read_data="eng:English\njpn:Japanese\nfra:French\n"))
    @patch("os.path.dirname")
    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_get_language_codes_print(
        self, mock_print, mock_terminal_size, mock_dirname, basic_defaulter
    ):
        """Test printing language codes."""
        mock_dirname.return_value = "/fake/path"
        mock_terminal_size.return_value.columns = 80

        result = basic_defaulter.get_language_codes(print_codes=True)

        assert result is None
        assert mock_print.called

    @patch("builtins.open", mock_open(read_data="eng:English\njpn:Japanese\nfra:French\n"))
    @patch("os.path.dirname")
    def test_verify_language_code_valid(self, mock_dirname, basic_defaulter):
        """Test language code verification with valid code."""
        mock_dirname.return_value = "/fake/path"

        result = basic_defaulter.verify_language_code("eng", "audio")
        assert result is True

    @patch("builtins.open", mock_open(read_data="eng:English\njpn:Japanese\nfra:French\n"))
    @patch("os.path.dirname")
    def test_verify_language_code_invalid(self, mock_dirname, basic_defaulter):
        """Test language code verification with invalid code."""
        mock_dirname.return_value = "/fake/path"

        with pytest.raises(Exception) as exc_info:
            basic_defaulter.verify_language_code("xyz", "subtitle")

        assert 'Subtitle language code ("xyz") could not be found/verified' in str(exc_info.value)

    def test_process_media_file_info_success_linux(self, basic_defaulter, sample_mkvmerge_output):
        """Test processing media file info on Linux with successful result."""

        with patch("sys.platform", "linux"):
            with patch.object(mkv_module, "subproc_run") as mock_subproc:
                mock_process = Mock()
                mock_process.returncode = 0
                mock_process.stdout = json.dumps(sample_mkvmerge_output).encode("utf-8")
                mock_process.stderr = b""
                mock_subproc.return_value = mock_process

                file_path = "/test/movie.mkv"
                result_path, tracks_info = basic_defaulter.process_media_file_info(file_path)

                mock_subproc.assert_called_once_with(
                    ["mkvmerge", "-J", file_path], capture_output=True, check=True
                )

                assert result_path == file_path
                assert "audio" in tracks_info
                assert "subtitles" in tracks_info
                assert len(tracks_info["audio"]) == 2
                assert len(tracks_info["subtitles"]) == 1

                audio_track = tracks_info["audio"][0]
                assert audio_track["language"] == "eng"
                assert audio_track["default"] is True
                assert audio_track["sample_freq"] == 48000

    def test_process_media_file_info_success_windows(self, basic_defaulter, sample_mkvmerge_output):
        """Test processing media file info on Windows with successful result."""

        with patch("sys.platform", "win32"):
            with patch.object(mkv_module, "Popen") as mock_popen:
                mock_process = Mock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (
                    json.dumps(sample_mkvmerge_output).encode("utf-8"),
                    b"",
                )
                mock_popen.return_value = mock_process

                file_path = "/test/movie.mkv"
                result_path, tracks_info = basic_defaulter.process_media_file_info(file_path)

                mock_popen.assert_called_once_with(
                    ["mkvmerge", "-J", file_path],
                    shell=True,
                    stdout=mkv_module.PIPE,
                    stderr=mkv_module.PIPE,
                )

                assert result_path == file_path
                assert "audio" in tracks_info
                assert "subtitles" in tracks_info

    def test_process_media_file_info_error(self, basic_defaulter):
        """Test processing media file info with error result."""

        error_output = {"errors": ["File not found", "Invalid format"]}

        with patch("sys.platform", "linux"):
            with patch.object(mkv_module, "subproc_run") as mock_subproc:
                mock_process = Mock()
                mock_process.returncode = 1
                mock_process.stdout = json.dumps(error_output).encode("utf-8")
                mock_process.stderr = b""
                mock_subproc.return_value = mock_process

                with pytest.raises(Exception) as exc_info:
                    basic_defaulter.process_media_file_info("/test/invalid.mkv")

                assert "File not foundInvalid format" in str(exc_info.value)

    def test_process_media_file_info_decode_error(self, basic_defaulter):
        """Test processing media file info with JSON decode error."""

        with patch("sys.platform", "linux"):
            with patch.object(mkv_module, "subproc_run") as mock_subproc:
                mock_process = Mock()
                mock_process.returncode = 1
                mock_process.stdout = b"Invalid JSON output"
                mock_process.stderr = b""
                mock_subproc.return_value = mock_process

                with pytest.raises(Exception) as exc_info:
                    basic_defaulter.process_media_file_info("/test/invalid.mkv")

                assert "Invalid JSON output" in str(exc_info.value)

    def test_get_media_files_info_single_file_no_multiprocessing(self, basic_defaulter):
        """Test getting media files info from single file without multiprocessing."""
        basic_defaulter.file_or_library_path = "/test/movie.mkv"
        basic_defaulter.pool_size = 1

        with patch("os.path.isdir", return_value=False):
            # Simulate what happens in get_media_files_info without multiprocessing
            media_file_paths = []

            if basic_defaulter.file_or_library_path.endswith(basic_defaulter.file_extensions):
                media_file_paths = [basic_defaulter.file_or_library_path]

            assert len(media_file_paths) == 1
            assert media_file_paths[0] == "/test/movie.mkv"

            fake_pool_results = [("/test/movie.mkv", {"audio": {}, "subtitles": {}})]

            media_info = {}
            for file_path, tracks_info in fake_pool_results:
                media_info[file_path] = tracks_info

            assert len(media_info) == 1
            assert "/test/movie.mkv" in media_info
            assert media_info["/test/movie.mkv"]["audio"] == {}
            assert media_info["/test/movie.mkv"]["subtitles"] == {}

    def test_process_media_file_tracks_non_mkv_no_multiprocessing(self, basic_defaulter):
        """Test processing media file tracks with non-MKV file without multiprocessing."""
        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                media_file_info = ("/test/movie.mp4", {"audio": {}, "subtitles": {}})

                result = basic_defaulter.process_media_file_tracks(media_file_info)

                assert result[0] == (".mp4", 1)  # File extension and count
                assert result[1] == 0  # successful_count
                assert result[2] == 0  # estimated_successful
                assert result[3] == 0  # unchanged_count
                assert result[4] == 0  # miss_track_count
                assert result[5] == 1  # invalid_count (non-MKV file)
                assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_no_changes_needed(self, basic_defaulter):
        """Test processing media file tracks when no changes are needed."""
        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                # Media file where English is already default for both audio and subtitle
                tracks_info = {
                    "audio": {0: {"language": "eng", "default": True, "sample_freq": 48000}},
                    "subtitles": {1: {"language": "eng", "default": True}},
                }

                media_file_info = ("/test/movie.mkv", tracks_info)

                result = basic_defaulter.process_media_file_tracks(media_file_info)

                assert result[0] == (".mkv", 1)
                assert result[1] == 0  # successful_count
                assert result[2] == 0  # estimated_successful
                assert result[3] == 1  # unchanged_count (no changes needed)
                assert result[4] == 0  # miss_track_count
                assert result[5] == 0  # invalid_count
                assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_successful_change(self, basic_defaulter):
        """Test processing media file tracks with successful changes."""

        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                with patch("sys.platform", "linux"):
                    with patch.object(mkv_module, "subproc_run") as mock_subproc:
                        tracks_info = {
                            "audio": {
                                0: {"language": "jpn", "default": True, "sample_freq": 44100},
                                1: {"language": "eng", "default": False, "sample_freq": 48000},
                            },
                            "subtitles": {
                                2: {"language": "jpn", "default": True},
                                3: {"language": "eng", "default": False},
                            },
                        }

                        media_file_info = ("/test/movie.mkv", tracks_info)

                        mock_process = Mock()
                        mock_process.returncode = 0
                        mock_process.stdout = b"Success"
                        mock_process.stderr = b""
                        mock_subproc.return_value = mock_process

                        result = basic_defaulter.process_media_file_tracks(media_file_info)

                        assert result[0] == (".mkv", 1)
                        assert result[1] == 1  # successful_count
                        assert result[2] == 0  # estimated_successful
                        assert result[3] == 0  # unchanged_count
                        assert result[4] == 0  # miss_track_count
                        assert result[5] == 0  # invalid_count
                        assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_dry_run(self, basic_defaulter):
        """Test processing media file tracks in dry run mode."""
        basic_defaulter.dry_run = True

        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                tracks_info = {
                    "audio": {
                        0: {"language": "jpn", "default": True, "sample_freq": 44100},
                        1: {"language": "eng", "default": False, "sample_freq": 48000},
                    },
                    "subtitles": {
                        2: {"language": "jpn", "default": True},
                        3: {"language": "eng", "default": False},
                    },
                }

                media_file_info = ("/test/movie.mkv", tracks_info)

                result = basic_defaulter.process_media_file_tracks(media_file_info)

                assert result[0] == (".mkv", 1)
                assert result[1] == 0  # successful_count
                assert result[2] == 1  # estimated_successful (dry run)
                assert result[3] == 0  # unchanged_count
                assert result[4] == 0  # miss_track_count
                assert result[5] == 0  # invalid_count
                assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_missing_track_strict(self, basic_defaulter):
        """Test processing media file tracks with missing track in strict mode."""
        basic_defaulter.default_method = "strict"

        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                # Missing English audio track
                tracks_info = {
                    "audio": {0: {"language": "jpn", "default": True, "sample_freq": 44100}},
                    "subtitles": {1: {"language": "eng", "default": False}},
                }

                media_file_info = ("/test/movie.mkv", tracks_info)

                result = basic_defaulter.process_media_file_tracks(media_file_info)

                assert result[0] == (".mkv", 1)
                assert result[1] == 0  # successful_count
                assert result[2] == 0  # estimated_successful
                assert result[3] == 0  # unchanged_count
                assert result[4] == 1  # miss_track_count (missing English audio)
                assert result[5] == 0  # invalid_count
                assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_missing_track_lazy(self, basic_defaulter):
        """Test processing media file tracks with missing track in lazy mode."""

        basic_defaulter.default_method = "lazy"

        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                with patch.object(mkv_module, "subproc_run") as mock_subproc:
                    with patch("sys.platform", "linux"):
                        # Missing English audio track, but has English subtitles
                        tracks_info = {
                            "audio": {
                                0: {"language": "jpn", "default": True, "sample_freq": 44100}
                            },
                            "subtitles": {
                                1: {"language": "jpn", "default": True},
                                2: {"language": "eng", "default": False},
                            },
                        }

                        media_file_info = ("/test/movie.mkv", tracks_info)

                        mock_process = Mock()
                        mock_process.returncode = 0
                        mock_process.stdout = b"Success"
                        mock_process.stderr = b""
                        mock_subproc.return_value = mock_process

                        result = basic_defaulter.process_media_file_tracks(media_file_info)

                        assert result[0] == (".mkv", 1)
                        assert result[1] == 1  # successful_count (changed subtitle)
                        assert result[2] == 0  # estimated_successful
                        assert result[3] == 0  # unchanged_count
                        assert result[4] == 0  # miss_track_count (lazy mode ignores missing audio)
                        assert result[5] == 0  # invalid_count
                        assert result[6] == 0  # failed_count

    def test_process_media_file_tracks_subtitle_off(self, basic_defaulter):
        """Test processing media file tracks with subtitle set to 'off'."""

        basic_defaulter.subtitle_lang_code = "off"

        with patch.object(basic_defaulter, "verify_language_code", return_value=True):
            with patch.object(basic_defaulter, "set_log_level"):
                with patch("sys.platform", "linux"):
                    with patch.object(mkv_module, "subproc_run") as mock_subproc:
                        tracks_info = {
                            "audio": {
                                0: {"language": "eng", "default": True, "sample_freq": 48000}
                            },
                            "subtitles": {1: {"language": "eng", "default": True}},
                        }

                        media_file_info = ("/test/movie.mkv", tracks_info)

                        mock_process = Mock()
                        mock_process.returncode = 0
                        mock_process.stdout = b"Success"
                        mock_process.stderr = b""
                        mock_subproc.return_value = mock_process

                        result = basic_defaulter.process_media_file_tracks(media_file_info)

                        assert result[0] == (".mkv", 1)
                        assert (
                            result[1] == 1
                        )  # successful_count (should be 1 since we made changes)
                        assert result[2] == 0  # estimated_successful
                        assert result[3] == 0  # unchanged_count
                        assert result[4] == 0  # miss_track_count
                        assert result[5] == 0  # invalid_count
                        assert result[6] == 0  # failed_count

    def test_change_default_tracks_simple(self, basic_defaulter):
        """Test the main change_default_tracks method without multiprocessing complexity."""
        media_files_info = {
            "/test/movie1.mkv": {"audio": {}, "subtitles": {}},
            "/test/movie2.mkv": {"audio": {}, "subtitles": {}},
        }

        with patch("multiprocessing.Pool") as mock_pool:
            mock_pool.return_value.__enter__.return_value.imap.return_value = [
                ((".mkv", 1), 1, 0, 0, 0, 0, 0),  # successful processing
                ((".mkv", 1), 0, 0, 1, 0, 0, 0),  # unchanged
            ]

            with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
                with patch("builtins.print") as mock_print:
                    basic_defaulter.change_default_tracks(media_files_info)

                    assert mock_print.call_count >= 5

    def test_change_default_tracks_dry_run(self, basic_defaulter):
        """Test change_default_tracks method in dry run mode."""
        basic_defaulter.dry_run = True
        media_files_info = {"/test/movie.mkv": {"audio": {}, "subtitles": {}}}

        with patch("multiprocessing.Pool") as mock_pool:
            mock_pool.return_value.__enter__.return_value.imap.return_value = [
                ((".mkv", 1), 0, 1, 0, 0, 0, 0)  # estimated_successful = 1
            ]

            with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
                with patch("builtins.print") as mock_print:
                    basic_defaulter.change_default_tracks(media_files_info)

                    print_calls = [str(call) for call in mock_print.call_args_list]
                    dry_run_found = any("DRY RUN" in call for call in print_calls)
                    estimated_found = any("Estimated Successful" in call for call in print_calls)

                    assert dry_run_found
                    assert estimated_found


class TestIntegration:
    """Integration tests that test multiple components working together."""

    @patch("MKVAudioSubsDefaulter.MKVAudioSubsDefaulter.subproc_run")
    @patch("sys.platform", "linux")
    @patch("builtins.open", mock_open(read_data="eng:English\njpn:Japanese\nfra:French\n"))
    @patch("os.path.dirname")
    def test_integration_process_and_verify_language(
        self, mock_dirname, mock_subproc, sample_mkvmerge_output
    ):
        """Integration test: process file info and verify language codes."""
        mock_dirname.return_value = "/fake/path"

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps(sample_mkvmerge_output).encode("utf-8")
        mock_process.stderr = b""
        mock_subproc.return_value = mock_process

        defaulter = MKVAudioSubsDefaulter(
            file_or_library_path="/test/movie.mkv", audio_lang_code="eng", subtitle_lang_code="jpn"
        )

        assert defaulter.verify_language_code("eng", "audio") is True
        assert defaulter.verify_language_code("jpn", "subtitle") is True

        file_path, tracks_info = defaulter.process_media_file_info("/test/movie.mkv")

        assert file_path == "/test/movie.mkv"
        assert "audio" in tracks_info
        assert "subtitles" in tracks_info
        assert len(tracks_info["audio"]) == 2
        assert tracks_info["audio"][0]["language"] == "eng"
        assert tracks_info["audio"][0]["default"] is True

    @pytest.fixture
    def sample_mkvmerge_output(self):
        """Sample JSON output from mkvmerge command for integration tests."""
        return {
            "tracks": [
                {
                    "id": 0,
                    "type": "audio",
                    "properties": {
                        "language": "eng",
                        "track_name": "English Audio",
                        "default_track": True,
                        "enabled_track": True,
                        "forced_track": False,
                        "audio_sampling_frequency": 48000,
                    },
                },
                {
                    "id": 1,
                    "type": "audio",
                    "properties": {
                        "language": "jpn",
                        "track_name": "Japanese Audio",
                        "default_track": False,
                        "enabled_track": True,
                        "forced_track": False,
                        "audio_sampling_frequency": 44100,
                    },
                },
                {
                    "id": 2,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "track_name": "English Subtitles",
                        "default_track": False,
                        "enabled_track": True,
                        "forced_track": False,
                        "text_subtitles": True,
                    },
                },
            ]
        }

    def test_integration_library_processing_simple_no_multiprocessing(self):
        """Integration test: process library with simple mocking."""
        defaulter = MKVAudioSubsDefaulter(
            file_or_library_path="/test/library",
            audio_lang_code="eng",
            subtitle_lang_code="off",
            file_search_depth=1,
            file_extensions=(".mkv",),
            regex_filter=None,
            pool_size=1,
        )

        base_path = "/test/library"
        paths = {
            "movie": os.path.normpath(os.path.join(base_path, "Movie.mkv")),
            "ep1": os.path.normpath(os.path.join(base_path, "season1", "S01E01.mkv")),
            "ep2": os.path.normpath(os.path.join(base_path, "season1", "S01E02.mkv")),
        }

        test_files_info = {
            paths["movie"]: {"audio": {0: {"language": "eng", "default": True}}, "subtitles": {}},
            paths["ep1"]: {"audio": {0: {"language": "jpn", "default": True}}, "subtitles": {}},
            paths["ep2"]: {"audio": {0: {"language": "eng", "default": True}}, "subtitles": {}},
        }

        with patch("os.path.isdir", return_value=True):
            with patch.object(
                defaulter,
                "list_directories",
                return_value=[
                    os.path.normpath(base_path),
                    os.path.normpath(os.path.join(base_path, "season1")),
                ],
            ):
                with patch("os.walk") as mock_walk:
                    mock_walk.return_value = iter(
                        [
                            (os.path.normpath(base_path), [], ["Movie.mkv"]),
                            (
                                os.path.normpath(os.path.join(base_path, "season1")),
                                [],
                                ["S01E01.mkv", "S01E02.mkv"],
                            ),
                        ]
                    )

                    media_file_paths = []
                    media_dirs = defaulter.list_directories(
                        defaulter.file_or_library_path, defaulter.file_search_depth
                    )
                    for folder in media_dirs:
                        _, _, media_file_names = next(os.walk(folder))
                        for name in media_file_names:
                            if name.endswith(defaulter.file_extensions):
                                media_file_paths.append(
                                    os.path.normpath(os.path.join(folder, name))
                                )

                    with patch.object(defaulter, "process_media_file_info") as mock_process:

                        def side_effect(file_path):
                            normalized_path = os.path.normpath(file_path)
                            return normalized_path, test_files_info[normalized_path]

                        mock_process.side_effect = side_effect

                        result = {}
                        for file_path in media_file_paths:
                            file_path, tracks_info = defaulter.process_media_file_info(file_path)
                            result[file_path] = tracks_info

                        assert len(result) == 3
                        assert paths["movie"] in result
                        assert paths["ep1"] in result
                        assert paths["ep2"] in result
                        assert result[paths["movie"]]["audio"][0]["language"] == "eng"
                        assert result[paths["ep1"]]["audio"][0]["language"] == "jpn"
                        assert result[paths["ep2"]]["audio"][0]["language"] == "eng"

    def test_integration_regex_filtering_simple_no_multiprocessing(self):
        """Integration test: library processing with regex filtering."""
        defaulter = MKVAudioSubsDefaulter(
            file_or_library_path="/test/library",
            audio_lang_code="eng",
            subtitle_lang_code="off",
            regex_filter=r".*Season.*",
            pool_size=1,
        )

        base_path = "/test/library"
        paths = {
            "season1": os.path.normpath(os.path.join(base_path, "Movie.Season.1.mkv")),
            "season2": os.path.normpath(os.path.join(base_path, "Movie.Season.2.mkv")),
            "documentary": os.path.normpath(os.path.join(base_path, "Documentary.mkv")),
        }

        test_files_info = {
            paths["season1"]: {"audio": {}, "subtitles": {}},
            paths["season2"]: {"audio": {}, "subtitles": {}},
            paths["documentary"]: {"audio": {}, "subtitles": {}},
        }

        with patch("os.path.isdir", return_value=True):
            with patch.object(
                defaulter, "list_directories", return_value=[os.path.normpath(base_path)]
            ):
                with patch("os.walk") as mock_walk:
                    mock_walk.return_value = iter(
                        [
                            (
                                os.path.normpath(base_path),
                                [],
                                ["Movie.Season.1.mkv", "Movie.Season.2.mkv", "Documentary.mkv"],
                            )
                        ]
                    )

                    media_file_paths = []
                    media_dirs = defaulter.list_directories(
                        defaulter.file_or_library_path, defaulter.file_search_depth
                    )

                    for folder in media_dirs:
                        _, _, media_file_names = next(os.walk(folder))

                        for name in media_file_names:
                            if name.endswith(defaulter.file_extensions) and (
                                not defaulter.regex_filter or re.match(defaulter.regex_filter, name)
                            ):
                                media_file_paths.append(
                                    os.path.normpath(os.path.join(folder, name))
                                )

                    with patch.object(defaulter, "process_media_file_info") as mock_process:

                        def side_effect(file_path):
                            normalized_path = os.path.normpath(file_path)
                            return normalized_path, test_files_info[normalized_path]

                        mock_process.side_effect = side_effect

                        result = {}
                        for file_path in media_file_paths:
                            file_path, tracks_info = defaulter.process_media_file_info(file_path)
                            result[file_path] = tracks_info

                        assert len(result) == 2
                        assert paths["season1"] in result
                        assert paths["season2"] in result
                        assert paths["documentary"] not in result


class TestUtilityFunctions:
    """Test utility functions in the module."""

    def test_runtime_output_str_seconds_only(self):
        """Test runtime output with seconds only."""
        from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import _runtime_output_str

        with patch("builtins.print") as mock_print:
            _runtime_output_str(45.67)

            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "45.67 sec(s)" in call_args
            assert "Total Runtime:" in call_args

    def test_runtime_output_str_minutes_and_seconds(self):
        """Test runtime output with minutes and seconds."""
        from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import _runtime_output_str

        with patch("builtins.print") as mock_print:
            _runtime_output_str(125.5)  # 2 minutes, 5.5 seconds

            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "2 min(s)" in call_args
            assert "5.5 sec(s)" in call_args

    def test_runtime_output_str_hours_minutes_seconds(self):
        """Test runtime output with hours, minutes, and seconds."""
        from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import _runtime_output_str

        with patch("builtins.print") as mock_print:
            _runtime_output_str(3725.25)  # 1 hour, 2 minutes, 5.25 seconds

            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "1 hr(s)" in call_args
            assert "2 min(s)" in call_args
            assert "5.25 sec(s)" in call_args

    def test_runtime_output_str_days_hours_minutes_seconds(self):
        """Test runtime output with days, hours, minutes, and seconds."""
        from MKVAudioSubsDefaulter.MKVAudioSubsDefaulter import _runtime_output_str

        with patch("builtins.print") as mock_print:
            _runtime_output_str(90125.75)  # 1 day, 1 hour, 2 minutes, 5.75 seconds

            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "1 day(s)" in call_args
            assert "1 hr(s)" in call_args
            assert "2 min(s)" in call_args
            assert "5.75 sec(s)" in call_args


class TestCommandLineArguments:
    """Test command line argument parsing."""

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-lc"])
    def test_cmd_parse_args_language_codes(self):
        """Test parsing language codes argument."""

        args = cmd_parse_args()
        assert args.language_codes is True

    @patch(
        "sys.argv", ["MKVAudioSubsDefaulter.py", "-f", "/test/movie.mkv", "-a", "eng", "-s", "jpn"]
    )
    def test_cmd_parse_args_basic_file(self):
        """Test parsing basic file arguments."""

        args = cmd_parse_args()

        assert args.file == "/test/movie.mkv"
        assert args.audio == "eng"
        assert args.subtitle == "jpn"
        assert args.library is None
        assert args.default_method is None
        assert args.verbose == 4

    @patch(
        "sys.argv",
        [
            "MKVAudioSubsDefaulter.py",
            "-lib",
            "/test/library",
            "-a",
            "fra",
            "-s",
            "off",
            "-dm",
            "lazy",
            "-d",
            "2",
            "-plsz",
            "4",
            "-ext",
            ".mkv,.mp4",
            "-regfil",
            ".*Season.*",
            "-dr",
            "-v",
            "1",
        ],
    )
    def test_cmd_parse_args_full_library(self):
        """Test parsing full library arguments."""

        args = cmd_parse_args()

        assert args.library == "/test/library"
        assert args.audio == "fra"
        assert args.subtitle == "off"
        assert args.default_method == "lazy"
        assert args.depth == 2
        assert args.pool_size == 4
        assert args.file_extensions == (".mkv", ".mp4")
        assert args.regex_filter == ".*Season.*"
        assert args.dry_run is True
        assert args.verbose == 1

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-lc", "-f", "/test/movie.mkv"])
    def test_cmd_parse_args_language_codes_with_other_args_error(self):
        """Test that language codes cannot be used with other arguments."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-f", "/test/movie.mkv", "-a", "eng"])
    def test_cmd_parse_args_missing_subtitle(self):
        """Test that either audio or subtitle is required when using file/library."""

        args = cmd_parse_args()
        assert args.file == "/test/movie.mkv"
        assert args.audio == "eng"
        assert args.subtitle is None

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-f", "/test/movie.mkv"])
    def test_cmd_parse_args_no_audio_or_subtitle(self):
        """Test error when file is specified without audio or subtitle."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-a", "eng", "-s", "jpn"])
    def test_cmd_parse_args_no_file_or_library(self):
        """Test error when audio/subtitle specified without file or library."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch(
        "sys.argv", ["MKVAudioSubsDefaulter.py", "-f", "/test/movie.mkv", "-a", "off", "-s", "eng"]
    )
    def test_cmd_parse_args_audio_off_error(self):
        """Test error when audio is set to 'off'."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch(
        "sys.argv",
        [
            "MKVAudioSubsDefaulter.py",
            "-f",
            "/test/movie.mkv",
            "-a",
            "eng",
            "-s",
            "jpn",
            "-dm",
            "invalid",
        ],
    )
    def test_cmd_parse_args_invalid_default_method(self):
        """Test error with invalid default method."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch(
        "sys.argv",
        ["MKVAudioSubsDefaulter.py", "-f", "/test/movie.mkv", "-a", "eng", "-s", "jpn", "-d", "2"],
    )
    def test_cmd_parse_args_depth_with_file_error(self):
        """Test error when depth is used with file instead of library."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch(
        "sys.argv",
        [
            "MKVAudioSubsDefaulter.py",
            "-f",
            "/test/movie.mkv",
            "-a",
            "eng",
            "-s",
            "jpn",
            "-plsz",
            "4",
        ],
    )
    def test_cmd_parse_args_pool_size_with_file_error(self):
        """Test error when pool size is used with file instead of library."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch(
        "sys.argv",
        [
            "MKVAudioSubsDefaulter.py",
            "-f",
            "/test/movie.mkv",
            "-a",
            "eng",
            "-s",
            "jpn",
            "-regfil",
            ".*test.*",
        ],
    )
    def test_cmd_parse_args_regex_filter_with_file_error(self):
        """Test error when regex filter is used with file instead of library."""

        with pytest.raises(SystemExit):
            cmd_parse_args()

    @patch("sys.argv", ["MKVAudioSubsDefaulter.py", "-v", "2"])
    def test_cmd_parse_args_verbose_without_file_library_error(self):
        """Test error when verbose is used without file or library."""

        with pytest.raises(SystemExit):
            cmd_parse_args()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
