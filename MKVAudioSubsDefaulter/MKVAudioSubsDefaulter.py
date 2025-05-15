import argparse
import json
import logging
import os
import re
import sys
from multiprocessing import Pool
from pathlib import Path
from subprocess import PIPE
from subprocess import Popen
from subprocess import run as subproc_run
from time import perf_counter

try:
    from tqdm import tqdm
except ImportError:
    raise ImportError(
        'Python is unable to find the "tqdm" package, this package is '
        "required to use the CLI (it's used for terminal loading bars)."
        '\nPlease verify its installation, "pip install tqdm", and try again.'
    )

__version__ = "1.3.3"
LOGGER = logging.getLogger(__name__)


class MKVAudioSubsDefaulter(object):
    """:description: Object to set up MKVAudioSubsDefaulter

    :param file_or_library_path: Full file path of desired .mkv file or Full directory path of desired group of .mkv files
    :type file_or_library_path: str, required
    :param audio_lang_code: Desired audio language (refer to language codes (CANNOT be 'OFF'): -lc, --language-codes)
    :type audio_lang_code: str, required
    :param subtitle_lang_code: Desired subtitle language (refer to language codes (CAN be 'OFF'): -lc, --language-codes)
    :type subtitle_lang_code: str, required
    :param log_level: Adjust log level (0: NONE (Default), 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR)
    :type log_level: int, optional
    :param default_method: The method of changing the default audio and subtitle language tracks: 'strict' (default) or 'lazy'
    :type default_method: str, optional
    :param file_search_depth: When using the '-lib' arg, how many directories deep to search within the specified library
                              folder (Default: 0)
    :type file_search_depth: int, optional
    :param file_extensions: Specify media file extensions to search for in a comma separated list, EX: .mkv,.mp4,.avi
    :type file_extensions: tuple[str], optional
    :param pool_size: When using the '-lib/--library' arg, specify the size of the processing pool (number of concurrent
                      processes) to speed up media file processing (Default: 1)
    :type pool_size: int, optional
    :param regex_filter: When using the '-lib/--library' arg, specify a regex query to filter for specific media files
    :type regex_filter: str, optional
    :param mkvpropedit_location: Full path of "mkvpropedit" binary location (OPTIONAL if the binary is on system path).
    :type mkvpropedit_location: str, optional
    :param mkvmerge_location: Full path of "mkvmerge" binary location (OPTIONAL if the binary is on system path).
    :type mkvmerge_location: str, optional
    :param dry_run: If set, no changes will be made to files but summary of predicted changes will be outputted
    :type dry_run: bool, optional
    """

    def __init__(
        self,
        file_or_library_path: str,
        audio_lang_code: str,
        subtitle_lang_code: str,
        log_level: int = 0,
        default_method: str = "strict",
        file_search_depth: int = 0,
        file_extensions: tuple[str] = tuple([".mkv"]),
        pool_size: int = 1,
        regex_filter: str = None,
        mkvpropedit_location: str = None,
        mkvmerge_location: str = None,
        dry_run: bool = False,
    ):
        self.log_level = log_level
        self.file_or_library_path = file_or_library_path
        self.audio_lang_code = audio_lang_code
        self.subtitle_lang_code = subtitle_lang_code
        self.default_method = default_method
        self.file_search_depth = file_search_depth
        self.file_extensions = file_extensions
        self.pool_size = pool_size
        self.regex_filter = regex_filter
        self.mkvpropedit_location = mkvpropedit_location
        self.mkvmerge_location = mkvmerge_location
        self.dry_run = dry_run

    def set_log_level(self) -> str:
        log_levels = {
            0: (None, "DISABLED"),
            1: (logging.INFO, "INFO"),
            2: (logging.DEBUG, "DEBUG"),
            3: (logging.WARNING, "WARNING"),
            4: (logging.ERROR, "ERROR"),
        }

        if log_levels[self.log_level][0] is not None:
            logging.basicConfig(
                format="%(asctime)s - %(levelname)s: %(message)s",
                datefmt="%m/%d/%Y %I:%M:%S %p",
                level=log_levels[self.log_level][0],
            )
        else:
            LOGGER.disabled = True

        return str(log_levels[self.log_level][1])

    @staticmethod
    def list_directories(root_dir: str, depth: int) -> list:
        directories = []

        def list_dirs_recursive(current_dir, current_depth):
            if current_depth <= depth:
                directories.append(current_dir)

                for item in os.listdir(current_dir):
                    full_path = os.path.join(current_dir, item)

                    if os.path.isdir(full_path):
                        list_dirs_recursive(full_path, current_depth + 1)

        list_dirs_recursive(root_dir, 0)

        return directories

    @staticmethod
    def get_language_codes(print_codes: bool = False) -> dict or None:
        with open(os.path.join(os.path.dirname(__file__), "language_codes.txt"), "r") as f:
            lines = f.readlines()

        if print_codes:
            # Get terminal size
            terminal_width = os.get_terminal_size().columns

            # Calculate the number of columns based on the terminal width
            max_column_width = max(len(line.strip()) for line in lines)
            num_columns = terminal_width // (max_column_width + 1)  # Add padding between columns

            # Calculate the number of lines per column
            num_lines_per_column = (len(lines) + num_columns - 1) // num_columns

            # Print the lines in dynamic number of columns
            for i in range(num_lines_per_column):
                columns = [
                    (
                        lines[i + j * num_lines_per_column].strip()
                        if i + j * num_lines_per_column < len(lines)
                        else ""
                    )
                    for j in range(num_columns)
                ]

                print(
                    "".join(
                        "{:<{width}}".format(column, width=max_column_width + 2)
                        for column in columns
                    )
                )
        else:
            return lines

    def verify_language_code(self, lang_code: str, track_type: str) -> bool:
        if lang_code not in [
            code.split(":")[0] for code in self.get_language_codes(print_codes=False)
        ]:
            raise Exception(
                f"[!] {track_type.capitalize()} language code "
                f'("{lang_code}") could not be found/verified, check code and try again [!]'
            )
        return True

    def process_media_file_info(self, file_path: str) -> [str, str]:
        def extract_track_info(track: dict) -> dict:
            track_prop = track["properties"]

            return {
                "language": track_prop.get("language"),
                "name": track_prop.get("track_name"),
                "default": track_prop.get("default_track"),
                "enabled": track_prop.get("enabled_track"),
                "forced": track_prop.get("forced_track"),
                "text_subtitles": (
                    track_prop.get("text_subtitles") if track["type"] == "subtitles" else None
                ),
            }

        mkvmerge_path = os.path.join(
            "mkvmerge" if not self.mkvmerge_location else Path(self.mkvmerge_location)
        )

        # Windows and linux handle subporcess cmds differently, this should ensure each system performs the same
        if sys.platform == "win32":
            process = Popen([mkvmerge_path, "-J", file_path], shell=True, stdout=PIPE, stderr=PIPE)
            output, _ = process.communicate()
        else:
            process = subproc_run([mkvmerge_path, "-J", file_path], capture_output=True, check=True)
            output, _ = process.stdout, process.stderr

        if process.returncode == 0:
            media_tracks_info = json.loads(output.decode("utf-8"))["tracks"]
            tracks_info = {"audio": {}, "subtitles": {}}

            for track in media_tracks_info:
                if track["type"] in ["audio", "subtitles"]:
                    tracks_info[track["type"]][track["id"]] = extract_track_info(track)

            return file_path, tracks_info
        else:
            try:
                raise Exception(
                    "".join(error for error in json.loads(output.decode("utf8"))["errors"])
                )
            except json.decoder.JSONDecodeError:
                raise Exception(output.decode("utf8"))

    def get_media_files_info(self) -> dict:
        media_file_paths = []

        if os.path.isdir(self.file_or_library_path):
            media_dirs = self.list_directories(self.file_or_library_path, self.file_search_depth)

            for folder in media_dirs:
                _, _, media_file_names = next(os.walk(folder))

                for name in media_file_names:
                    if name.endswith(self.file_extensions) and (
                        not self.regex_filter or re.match(self.regex_filter, name)
                    ):
                        media_file_paths.append(os.path.join(folder, name))
        else:
            if self.file_or_library_path.endswith(self.file_extensions):
                media_file_paths = [self.file_or_library_path]

        if len(media_file_paths) == 0:
            LOGGER.error(
                f"Media file list is empty (no .mkv file(s) could "
                f'be found), double check pathing and/or filters: "{self.file_or_library_path}", "{self.regex_filter}"'
            )

        media_info = {}

        with Pool(processes=self.pool_size) as pool:
            results = list(
                tqdm(
                    pool.imap(self.process_media_file_info, media_file_paths),
                    total=len(media_file_paths),
                    desc="Gathering Media Files Info",
                    unit="files",
                )
            )

        for file_path, tracks_info in results:
            media_info[file_path] = tracks_info

        return media_info

    def process_media_file_tracks(
        self, media_file_info: tuple
    ) -> tuple[tuple[str, int], int, int, int, int, int, int]:
        successful_count = 0
        estimated_successful = 0
        unchanged_count = 0
        miss_track_count = 0
        invalid_count = 0
        failed_count = 0

        self.set_log_level()

        media_file, tracks_info = media_file_info

        LOGGER.info("")
        LOGGER.info(f"Processing media file: {media_file}")

        media_file_ext = os.path.splitext(media_file.lower())[1]

        if not media_file.lower().endswith(".mkv"):
            LOGGER.warning(f'Skipping File - "{media_file}" is NOT a matroska (.mkv) file')
            invalid_count += 1
        else:
            mkv_cmds = []
            no_changes = False

            for code, track_type in [
                (self.audio_lang_code, "audio"),
                (self.subtitle_lang_code, "subtitles"),
            ]:
                code = code.lower() if code is not None else code

                if code is not None and self.verify_language_code(code, track_type):
                    current_default_track_num = None
                    new_default_track_num = None

                    # --set flag-default=<1_for_ENABLE_0_for_DISABLE>
                    for track_num, track in tracks_info.get(track_type, {}).items():
                        if track["default"]:
                            current_default_track_num = track_num

                            if code not in [track["language"], "off"]:
                                track_num = (
                                    (current_default_track_num - len(tracks_info.get("audio", {})))
                                    if track_type == "subtitles"
                                    else current_default_track_num
                                )

                                mkv_cmds += [
                                    "--edit",
                                    f"track:{track_type[0]}{track_num}",
                                    "--set",
                                    "flag-default=0",
                                ]
                            LOGGER.debug(f"Current Default - File: {media_file}, Track: {track}")
                        elif track_type == "subtitles" and current_default_track_num is None:
                            current_default_track_num = "off"

                        if track["language"] == code:
                            new_default_track_num = track_num
                            LOGGER.debug(f"New Default - File: {media_file}, Track: {track}")
                        elif current_default_track_num == code == "off":
                            new_default_track_num = code

                    # Checks if no subtitles exist in the media file
                    if (
                        track_type == "subtitles"
                        and not tracks_info.get(track_type)
                        and code == "off"
                    ):
                        LOGGER.warning(
                            f'The desired {track_type} language ("{code}") is already the default {track_type} track'
                        )
                    else:
                        if new_default_track_num is None:
                            if self.default_method == "strict":
                                if code != "off" or current_default_track_num is None:
                                    LOGGER.error(
                                        f'"{track_type.capitalize()}" language ("{code}") track does not exist in media file: "{media_file}"'
                                    )
                                    miss_track_count += 1
                                    no_changes = True
                                else:
                                    LOGGER.info(
                                        f'"{track_type.capitalize()}" language ("{code}") track exists in media file: "{media_file}"'
                                    )
                                    current_default_track_num -= (
                                        len(tracks_info.get("audio", {}))
                                        if track_type == "subtitles"
                                        else 0
                                    )
                                    mkv_cmds += [
                                        "--edit",
                                        f"track:{track_type[0]}{current_default_track_num}",
                                        "--set",
                                        "flag-default=0",
                                    ]
                            elif self.default_method == "lazy":
                                LOGGER.warning(
                                    f'"{self.default_method}" -dm/--default-method used, error ignored: "{track_type.capitalize()}" '
                                    f'language ("{code}") track does not exist in media file: "{media_file}"'
                                )
                        elif current_default_track_num == new_default_track_num:
                            LOGGER.warning(
                                f'The desired {track_type} language ("{code}") is already the default {track_type} track'
                            )
                        else:
                            LOGGER.info(
                                f'"{track_type.capitalize()}" language ("{code}") track exists in media file: "{media_file}"'
                            )

                            flag = 0 if new_default_track_num == "off" else 1

                            new_default_track_num = (
                                current_default_track_num
                                if new_default_track_num == "off"
                                else new_default_track_num
                            )

                            new_default_track_num -= (
                                len(tracks_info.get("audio", {}))
                                if track_type == "subtitles"
                                else 0
                            )
                            mkv_cmds += [
                                "--edit",
                                f"track:{track_type[0]}{new_default_track_num}",
                                "--set",
                                f"flag-default={flag}",
                            ]

            if mkv_cmds and not no_changes:
                mkvpropedit_path = os.path.join(
                    "mkvpropedit"
                    if not self.mkvpropedit_location
                    else Path(self.mkvpropedit_location)
                )

                full_cmd = [
                    mkvpropedit_path,
                    os.path.join(os.path.dirname(__file__), media_file),
                ] + mkv_cmds

                LOGGER.debug(f"Constructed CMD: {' '.join(full_cmd)}")

                if not self.dry_run:
                    # Windows and linux handle subporcess cmds differently, this should ensure each system performs the same
                    if sys.platform == "win32":
                        process = Popen(full_cmd, shell=True, stdout=PIPE, stderr=PIPE)
                        output, _ = process.communicate()
                    else:
                        process = subproc_run(full_cmd, capture_output=True, check=True)
                        output, _ = process.stdout, process.stderr

                    if process.returncode != 0:
                        try:
                            LOGGER.error(
                                "".join(
                                    error for error in json.loads(output.decode("utf8"))["errors"]
                                )
                            )
                        except json.decoder.JSONDecodeError:
                            LOGGER.error(output.decode("utf8"))
                        failed_count += 1
                    else:
                        LOGGER.info(f"Successfully Processed: {media_file}")
                        successful_count += 1
                else:
                    LOGGER.info(
                        f'"-dr/--dry-run" flag was used (No Changes) - Successfully Processed: {media_file}'
                    )
                    estimated_successful += 1
            elif no_changes:
                LOGGER.warning(
                    f'No changes were made because one or more tracks did not exist in "{media_file}"'
                )
            else:
                LOGGER.info("No media file changes were made")
                unchanged_count += 1

        return (
            (media_file_ext, 1),
            successful_count,
            estimated_successful,
            unchanged_count,
            miss_track_count,
            invalid_count,
            failed_count,
        )

    def change_default_tracks(self, media_files_info: dict) -> None:
        media_file_types = {}

        successful_count = 0
        estimated_successful = 0
        unchanged_count = 0
        miss_track_count = 0
        invalid_count = 0
        failed_count = 0

        with Pool(processes=self.pool_size) as pool:
            for counts in tqdm(
                pool.imap(self.process_media_file_tracks, media_files_info.items()),
                total=len(media_files_info),
                desc="Processing Media Files",
                unit="files",
            ):
                if counts[0][0] not in media_file_types:
                    media_file_types[counts[0][0]] = 0
                media_file_types[counts[0][0]] += counts[0][1]

                successful_count += counts[1]
                estimated_successful += counts[2]
                unchanged_count += counts[3]
                miss_track_count += counts[4]
                invalid_count += counts[5]
                failed_count += counts[6]

        print(
            "\n{} Total Files: {:,}\n".format(
                "(DRY RUN)" if self.dry_run else " " * 9, len(media_files_info)
            )
            + ("=" * 28)
        )

        for key, val in media_file_types.items():
            print("{:>21}: {:,}".format(key, val))
        print("-" * 28)

        if self.dry_run:
            print(" Estimated Successful: {:,}".format(estimated_successful))
        else:
            print("Successful Processing: {:,}".format(successful_count))

        print("  Unchanged/Untouched: {:,}".format(unchanged_count))
        print("     Missing Track(s): {:,}".format(miss_track_count))
        print("         Invalid File: {:,}".format(invalid_count))
        print("    Failed Processing: {:,}".format(failed_count))


def _runtime_output_str(total_seconds: float) -> None:
    runtime_str = ""

    days = int(total_seconds // 86400)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds // 60) % 60)
    seconds = round(total_seconds - minutes * 60, 2)

    if days > 0:
        runtime_str += f"{days} day(s) "
    if hours > 0 or days > 0:
        runtime_str += f"{hours} hr(s) "
    if minutes > 0 or hours > 0 or days > 0:
        runtime_str += f"{minutes} min(s) "
    if seconds > 0 or minutes > 0 or hours > 0 or days > 0:
        runtime_str += f"{seconds} sec(s) "

    print(f"\n[*] Total Runtime: {runtime_str}[*]")


def cmd_parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple python cli to set the default audio and/or subtitles of a single "
        "matroska (.mkv) file or a library of files WITHOUT having to remux the file.",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    file_or_library = parser.add_mutually_exclusive_group(required=False)
    misc_args = parser.add_mutually_exclusive_group(required=False)

    parser.add_argument(
        "-mkvpe-loc",
        "--mkvpropedit-location",
        required=False,
        type=str,
        help='Full path of "mkvpropedit" binary location (OPTIONAL if the binary is on system path).'
        '\nEX: "home/downloads/MKVToolNix/mmkvpropedit.exe"',
    )

    parser.add_argument(
        "-mkvm-loc",
        "--mkvmerge-location",
        required=False,
        type=str,
        help='Full path of "mkvmerge" binary location (OPTIONAL if the binary is on system path).'
        '\nEX: "home/downloads/MKVToolNix/mkvmerge.exe"',
    )

    file_or_library.add_argument(
        "-f", "--file", type=str, help="Full file path of desired .mkv file"
    )

    file_or_library.add_argument(
        "-lib",
        "--library",
        type=str,
        help="Full directory path of desired group of .mkv files",
    )

    parser.add_argument(
        "-a",
        "--audio",
        type=str,
        help="Desired audio language (refer to language codes (CANNOT be 'OFF'): -lc, --language-codes)",
    )

    parser.add_argument(
        "-s",
        "--subtitle",
        type=str,
        help="Desired subtitle language (refer to language codes (CAN be 'OFF'): -lc, --language-codes)",
    )

    parser.add_argument(
        "-dm",
        "--default-method",
        required=False,
        type=str,
        help=(
            "The method of changing the default audio and subtitle language tracks ('strict' or 'lazy')\n\n"
            '* "Strict" (default): The specified NEW media file language tracks for BOTH the audio\n  '
            "and subtitle tracks must exist in the track list (if ONE is missing, then no changes made to file)\n"
            "  * EX: If the audio language track is missing but not the subtitle track, then no changes\n    "
            "are made to the file (even thought the subtitle track exists)\n"
            '* "Lazy": The specified NEW media file language tracks for EITHER audio and/or subtitle\n  '
            "tracks must exist in the track list (if BOTH are missing, then no changes made to file)\n"
            "  * EX: If the audio track language is missing but not the subtitle track, then the audio\n    "
            "stays the same and the default subtitle track is changed (and vice verse)"
        ),
    )

    parser.add_argument(
        "-d",
        "--depth",
        required=False,
        type=int,
        help="When using the '-lib/--library' arg, specify how many directories deep to search\n"
        "within the specified library folder (Default: 0)",
    )

    parser.add_argument(
        "-ext",
        "--file-extensions",
        required=False,
        type=str,
        help="Specify media file extensions to search for in a comma separated list (Default: '.mkv'),\n"
        "EX: '.mkv,.mp4,.avi'",
    )

    parser.add_argument(
        "-plsz",
        "--pool-size",
        required=False,
        type=int,
        help="When using the '-lib/--library' arg, specify the size of the processing pool\n(number of concurrent "
        "processes) to speed up media file processing.\nDepending on your machine and size of your library, you "
        "should stay between 1-10 (Default: 1)",
    )

    parser.add_argument(
        "-regfil",
        "--regex-filter",
        required=False,
        type=str,
        help="When using the '-lib/--library' arg, specify a regex query to filter for specific\nmedia files (Default: None)",
    )

    parser.add_argument(
        "-dr",
        "--dry-run",
        action="store_true",
        required=False,
        help="Perform a dry run, no changes made to files but summary of predicted changes will be outputted",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        default=4,
        required=False,
        type=int,
        help="Adjust log level (0: NONE, 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR (default))",
    )

    misc_args.add_argument(
        "-lc",
        "--language-codes",
        action="store_true",
        help="Print language codes to console",
    )
    misc_args.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    misc_args.add_argument(
        "-h", "--help", action="help", help="Display argument descriptions and exit"
    )

    args = parser.parse_args()

    # Check for exclusive use of -lc/--language-codes
    if args.language_codes and len(sys.argv) >= 3:
        raise parser.error(
            "-lc/--language-codes can only be used by itself (no other args should be defined)"
        )

    # Check for valid values of -dm/--default-method
    if args.default_method and args.default_method not in ["strict", "lazy"]:
        raise parser.error(
            "-dm/--default-method can either be 'strict' or 'lazy', refer to -h/--help for more info"
        )

    # Check for required arguments when using -a/--audio or -s/--subtitle
    if args.audio or args.subtitle:
        if not args.file and not args.library:
            raise parser.error(
                "-f/--file or -lib/--library is required when using -a/--audio and/or -s/--subtitle"
            )

    # Check for required arguments when using -f/--file or -lib/--library
    if args.file or args.library:
        if not (args.audio or args.subtitle):
            raise parser.error(
                "-a/--audio or -s/--subtitle is required when using -f/--file or -lib/--library"
            )

    # Check for valid value of -a/--audio
    if args.audio and args.audio.lower() == "off":
        raise parser.error('-a/--audio option cannot be set to "off"')

    if not args.library:
        # Check for valid use of -d/--depth
        if args.depth:
            raise parser.error("-d/--depth can only be used with the -lib/--library arg")

        # Check for valid use of -plsz/--pool-size
        if args.pool_size:
            raise parser.error("-plsz/--pool-size can only be used with the -lib/--library arg")

        # Check for valid use of -regfil/--regex-filter
        if args.regex_filter:
            raise parser.error(
                "-regfil/--regex-filter can only be used with the -lib/--library arg"
            )

    # Convert file extensions to tuple if provided, otherwise set default
    args.file_extensions = tuple(
        str(args.file_extensions).split(",") if args.file_extensions else [".mkv"]
    )

    # Check for valid use of -v/--verbose
    if not args.language_codes and (args.verbose and not (args.file or args.library)):
        raise parser.error("'-v/--verbose' can only be used with -f/--file or -lib/--library")

    return args


def main():
    args = cmd_parse_args()

    mkv = MKVAudioSubsDefaulter(
        file_or_library_path=args.file or args.library,
        audio_lang_code=args.audio,
        subtitle_lang_code=args.subtitle,
        log_level=args.verbose,
        default_method=args.default_method if args.default_method else "strict",
        file_search_depth=args.depth if args.depth else 0,
        file_extensions=args.file_extensions,
        pool_size=args.pool_size if args.pool_size else 1,
        regex_filter=args.regex_filter,
        mkvpropedit_location=args.mkvpropedit_location,
        mkvmerge_location=args.mkvmerge_location,
        dry_run=args.dry_run,
    )

    # Set logging level
    mkv.set_log_level()

    if args.regex_filter:
        LOGGER.info(f'Using Regex Filter: "{args.regex_filter}"')

    if args.language_codes:
        mkv.get_language_codes(print_codes=True)

    if args.file or args.library:
        mkv.change_default_tracks(mkv.get_media_files_info())


if __name__ == "__main__":
    start = perf_counter()
    main()
    end = perf_counter()

    _runtime_output_str(end - start)
