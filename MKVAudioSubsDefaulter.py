import argparse
import json
import logging
import os
import sys
from subprocess import PIPE
from subprocess import Popen
from time import perf_counter

from tqdm import tqdm

__version__ = "1.0.0"
LOGGER = logging.getLogger(__name__)


def set_log_level(level: int) -> None:
    log_levels = {
        0: (None, "DISABLED"),
        1: (logging.INFO, "INFO"),
        2: (logging.DEBUG, "DEBUG"),
        3: (logging.WARNING, "WARNING"),
        4: (logging.ERROR, "ERROR"),
    }

    if log_levels[level][0] is not None:
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s: %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=log_levels[level][0],
        )
    else:
        LOGGER.disabled = True

    LOGGER.info(f"Log Level = {log_levels[level][1]}\n")


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


def get_language_codes(print_codes: bool = False) -> dict or None:
    with open("language_codes.txt", "r") as f:
        lines = f.readlines()

    if print_codes:
        # Get terminal size
        terminal_width = os.get_terminal_size().columns

        # Calculate the number of columns based on the terminal width
        max_column_width = max(len(line.strip()) for line in lines)
        num_columns = terminal_width // (
            max_column_width + 1
        )  # Add padding between columns

        # Calculate the number of lines per column
        num_lines_per_column = (len(lines) + num_columns - 1) // num_columns

        # Print the lines in dynamic number of columns
        for i in range(num_lines_per_column):
            columns = [
                lines[i + j * num_lines_per_column].strip()
                if i + j * num_lines_per_column < len(lines)
                else ""
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


def verify_language_code(lang_code: str, track_type: str):
    if lang_code not in [
        code.split(":")[0] for code in get_language_codes(print_codes=False)
    ]:
        raise Exception(
            f'[!] {track_type.capitalize()} language code ("{lang_code}") could not be found/verified, check code and try again [!]'
        )
    return True


def get_media_files_info(
    media_path: str,
    mkvmerge_location: str,
    media_file_types: tuple[str] = tuple(".mkv"),
    depth: int = 0,
) -> dict:
    def extract_track_info(track: dict) -> dict:
        track_prop = track["properties"]

        return {
            "language": track_prop.get("language"),
            "name": track_prop.get("track_name"),
            "default": track_prop.get("default_track"),
            "enabled": track_prop.get("enabled_track"),
            "forced": track_prop.get("forced_track"),
            "text_subtitles": track_prop.get("text_subtitles")
            if track["type"] == "subtitles"
            else None,
        }

    media_info = {}

    if os.path.isdir(media_path):
        media_dirs = list_directories(media_path, depth)
        media_file_paths = []

        for folder in media_dirs:
            _, _, media_paths = next(os.walk(folder))

            for path in media_paths:
                media_file_paths += [os.path.join(folder, path)]
    else:
        media_file_paths = [media_path]

    media_file_paths = list(
        filter(lambda f: f.endswith(media_file_types), media_file_paths)
    )

    for file_path in tqdm(
        media_file_paths, desc="Gathering Media Files Info", unit="files"
    ):
        mkvmerge_path = os.path.join(
            "mkvmerge" if not mkvmerge_location else mkvmerge_location
        )

        process = Popen(
            [mkvmerge_path, "-J", file_path], shell=True, stdout=PIPE, stderr=PIPE
        )
        output, errors = process.communicate()

        if process.returncode == 0:
            media_tracks_info = json.loads(output.decode("utf-8"))["tracks"]
            tracks_info = {"audio": {}, "subtitles": {}}

            for track in media_tracks_info:
                if track["type"] in ["audio", "subtitles"]:
                    tracks_info[track["type"]][track["id"]] = extract_track_info(track)

            media_info[file_path] = tracks_info
        else:
            raise Exception(errors)

    return media_info


# --set flag-default=<1_for_ENABLE_0_for_DISABLE>
def change_default_tracks(
    media_files_info: dict,
    audio_lang_code: str,
    sub_lang_code: str,
    default_method: str,
    dry_run: bool,
    mkvpropedit_location: str,
) -> None:
    # TODO: Output media files to log files depending on their status (see below for statuses)
    media_file_types = {}
    successful_count = 0
    estimated_successful = 0
    unchanged_count = 0
    pattern_mismatch_count = 0
    invalid_count = 0
    failed_count = 0

    for media_file, tracks_info in tqdm(
        media_files_info.items(), desc="Processing Media Files", unit="files"
    ):
        LOGGER.info("")
        LOGGER.info(f"Processing media file: {media_file}")

        media_file_ext = os.path.splitext(media_file.lower())[1]

        if media_file_ext not in media_file_types:
            media_file_types[media_file_ext] = 0
        media_file_types[media_file_ext] += 1

        if not media_file.lower().endswith(".mkv"):
            LOGGER.warning(
                f'Skipping File - "{media_file}" is NOT a matroska (.mkv) file'
            )
            invalid_count += 1
            continue

        mkv_cmds = []
        no_changes = False

        for code, track_type in [
            (audio_lang_code, "audio"),
            (sub_lang_code, "subtitles"),
        ]:
            code = code.lower() if code is not None else code

            if code is not None and verify_language_code(code, track_type):
                current_default_track_num = None
                new_default_track_num = None

                for track_num, track in tracks_info.get(track_type, {}).items():
                    if track["default"]:
                        current_default_track_num = track_num

                        if code not in [track["language"], "off"]:
                            track_num = (
                                (
                                    current_default_track_num
                                    - len(tracks_info.get("audio", {}))
                                )
                                if track_type == "subtitles"
                                else current_default_track_num
                            )

                            mkv_cmds += [
                                "--edit",
                                f"track:{track_type[0]}{track_num}",
                                "--set",
                                "flag-default=0",
                            ]
                        LOGGER.debug(
                            f"Current Default - File: {media_file}, Track: {track}"
                        )
                    elif (
                        track_type == "subtitles" and current_default_track_num is None
                    ):
                        current_default_track_num = "off"

                    if track["language"] == code:
                        new_default_track_num = track_num
                        LOGGER.debug(
                            f"New Default - File: {media_file}, Track: {track}"
                        )
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
                        if default_method == "strict":
                            if code != "off" or current_default_track_num is None:
                                LOGGER.error(
                                    f'"{track_type.capitalize()}" language ("{code}") track does not exist in media file: "{media_file}"'
                                )
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
                        elif default_method == "lazy":
                            LOGGER.warning(
                                f'"{default_method}" -dm/--default-method used, error ignored: "{track_type.capitalize()}" '
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
                "mkvpropedit" if not mkvpropedit_location else mkvpropedit_location
            )

            full_cmd = [
                mkvpropedit_path,
                os.path.join(os.path.dirname(__file__), media_file),
            ] + mkv_cmds

            LOGGER.debug(f'Constructed CMD: {" ".join(full_cmd)}')

            if not dry_run:
                process = Popen(full_cmd, shell=True, stdout=PIPE, stderr=PIPE)
                output, errors = process.communicate()

                if process.returncode != 0:
                    LOGGER.error(errors.decode("utf-8"))
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
            pattern_mismatch_count += 1
        else:
            LOGGER.info("No media file changes were made")
            unchanged_count += 1

    print(
        "\n{} Total Files: {:,}".format(
            "(DRY RUN)" if dry_run else " " * 9, len(media_files_info)
        )
    )
    print("=" * 28)

    for key, val in media_file_types.items():
        print("{:>21}: {:,}".format(key, val))
    print("-" * 28)

    if dry_run:
        print(" Estimated Successful: {:,}".format(estimated_successful))
    else:
        print("Successful Processing: {:,}".format(successful_count))

    print("     Pattern Mismatch: {:,}".format(pattern_mismatch_count))
    print("  Unchanged/Untouched: {:,}".format(unchanged_count))
    print("         Invalid File: {:,}".format(invalid_count))
    print("    Failed Processing: {:,}".format(failed_count))


def cmd_parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MKV Tool",
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
        help='Full path of "mkvpropedit" binary location (OPTIONAL if the binary is on system path).\nEX: "home/downloads/MKVToolNix/mmkvpropedit.exe"',
    )

    parser.add_argument(
        "-mkvm-loc",
        "--mkvmerge-location",
        required=False,
        type=str,
        help='Full path of "mkvmerge" binary location (OPTIONAL if the binary is on system path).\nEX: "home/downloads/MKVToolNix/mkvmerge.exe"',
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
        help="When using the '-lib' arg, how many directories deep to search within the specified library folder (Default: 0)",
    )

    parser.add_argument(
        "-ext",
        "--file-extensions",
        required=False,
        type=str,
        help="Specify media file extensions to search for in a comma separated list (default: .mkv), EX: .mkv,.mp4,.avi",
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
        default=0,
        required=False,
        type=int,
        help="Adjust log level (0: NONE (default), 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR)",
    )

    misc_args.add_argument(
        "-lc",
        "--language-codes",
        action="store_true",
        help="Print language codes to console",
    )
    misc_args.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    misc_args.add_argument(
        "-h", "--help", action="help", help="Display argument descriptions and exit"
    )

    args = parser.parse_args()

    if args.language_codes and len(sys.argv) >= 3:
        raise parser.error(
            "-lc/--language-codes can only be used by itself (no other args should be defined)"
        )

    if args.verbose and not (args.file or args.library):
        raise parser.error(
            "'-v/--verbose' can only be used with -f/--file or -l/--library"
        )

    if args.default_method and args.default_method not in ["strict", "lazy"]:
        raise parser.error(
            "-dm/--default-method can either be 'strict' or 'lazy', refer to -h/--help for more info"
        )

    if args.file or args.library:
        if not (args.audio or args.subtitle):
            raise parser.error(
                "-a/--audio or -s/--subtitle is required when using -f/--file or -l/--library"
            )

    if args.depth and not args.library:
        parser.error("-d/--depth can only be used with the -lib/--library arg")

    if args.audio and args.audio.lower() == "off":
        raise parser.error('-a/--audio option cannot be set to "off"')

    if args.file_extensions:
        args.file_extensions = tuple(str(args.file_extensions).split(","))
    else:
        args.file_extensions = tuple([".mkv"])

    return args


def main():
    args = cmd_parse_args()

    set_log_level(args.verbose)

    if args.language_codes:
        get_language_codes(print_codes=True)

    if args.file or args.library:
        media_files_info = get_media_files_info(
            args.file or args.library,
            args.mkvmerge_location,
            args.file_extensions,
            args.depth if args.depth else 0,
        )

        change_default_tracks(
            media_files_info,
            args.audio,
            args.subtitle,
            args.default_method if args.default_method else "strict",
            args.dry_run,
            args.mkvpropedit_location,
        )


if __name__ == "__main__":
    start = perf_counter()
    main()
    end = perf_counter()

    total_seconds = end - start

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds // 60) % 60)
    seconds = round(total_seconds - minutes * 60, 2)

    print(f"\n[*] Total Runtime: {hours} hr(s) {minutes} min(s) {seconds} sec(s) [*]")
