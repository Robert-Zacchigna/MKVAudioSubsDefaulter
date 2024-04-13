# MKVAudioSubsDefaulter

Simple python cli to set the default audio and/or subtitles of a single matroska (.mkv) file or a library of files
WITHOUT having to remux the file.

The main use case for this cli was being able to set the default tracks of matroska media files without having to remux the file.

Matroska media files have the unique makeup of being to edit parts of the metadata of the file (like the default tracks)
_without_ having to remux the whole file (which this cli aims to make as easy as possible).

> **NOTE:** To be extra clear, this cli only works on `.mkv` files and will filter out all other file types.

![](https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/blob/main/example.gif)

## Contents

* [Dependencies](#dependencies)
* [Usage](#usage)
  * [Quick Start Examples](#quick-start-examples)
  * [MKVToolNix  (mkvpropedit and mkvmerge)](#mkvtoolnix-mkvpropedit-and-mkvmerge)
  * [Dry Run](#dry-run)
  * [Language Codes (Audio and Subtitles)](#language-codes-audio-and-subtitles)
  * [File vs. Library](#file-vs-library)
  * [Default Method: Strict vs. Lazy](#default-method-strict-vs-lazy)
  * [Depth](#depth)
  * [Verbosity](#verbosity)
* [CLI Parameters](#cli-parameters)
* [Issues](#issues)
* [Suggestions](#suggestions)
* [Contributions](#contributions)
* [Future Improvements](#future-improvements)

## Dependencies

* Python **3.9+** ([python.org](https://www.python.org/downloads/))
  * External Python Modules
    * [tqdm](https://github.com/tqdm/tqdm) (for the progress bar)
* [MKVToolNix](https://mkvtoolnix.download/downloads.html) (Download for your OS)
  * You specifically need the following binaries from `MKVToolNix` added to your system `path`
    * [mkvmerge](https://mkvtoolnix.download/doc/mkvmerge.html)
    * [mkvpropedit](https://mkvtoolnix.download/doc/mkvpropedit.html)

## Usage

```
usage: MKVAudioSubsDefaulter.py [-mkve-loc MKVPROPEDIT_LOCATION] [-mkvpe-loc MKVMERGE_LOCATION] [-f FILE | -lib LIBRARY] [-a AUDIO] [-s SUBTITLE] [-dm DEFAULT_METHOD] [-d DEPTH] [-ext FILE_EXTENSIONS] [-dr] [-v VERBOSE] [-lc | -V | -h]
```

### Quick Start Examples

* HELP: `python MKVAudioSubsDefaulter.py -h`
* LANGUAGE-CODES: `python MKVAudioSubsDefaulter.py -lc`
* BASIC: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off`
* VERBOSE: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off -v 1`
* LAZY: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off -v 1 -dm lazy`
* DEPTH: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s eng -v 1 -d 1 -dm lazy`
* DRY-RUN: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s spa -v 1 -d 1 -dr`

### MKVToolNix (mkvpropedit and mkvmerge)

In order to use this cli you will need to have downloaded [MKVToolNix](https://mkvtoolnix.download/downloads.html) and either have added
[mkvmerge](https://mkvtoolnix.download/doc/mkvmerge.html) and [mkvpropedit](https://mkvtoolnix.download/doc/mkvpropedit.html)
to your system `path` OR specify the full path of those binaries using these cli args:

* `-mkvm-loc, mkvmerge-location`
* `-mkvpe-loc, mkvpropedit-location`

### Dry Run

It is HIGHLY recommended to use the `-dr, --dr-run` arg when first using the cli to make sure of the changes you want it
to make. This arg will let the cli know to run through the file(s) BUT MAKE NO CHANGES TO THE FILE(S). It will output an
estimate change count of how many files WOULD HAVE BEEN changed by the cli if it was not a dry run.

> **NOTE:** It is better to try the cli on a smaller subset of files from your library FIRST and then move onto the full library
> of files after you are confident in the changes it will make.

### Language Codes (Audio and Subtitles)

Language codes are the codes in the track metadata that specify what language a specific track is (i.e. "eng" = English).

You can list out all valid language codes using language code cli arg: `-lc, --language-codes`

> **NOTE:** The language code metadata is the basis of how this cli functions. Without language codes in the track
> metadata this cli will not be able to function. Thus, you (the user) are dependent on the creator of the media file
> and/or tracks for proper track labeling.
>
> **Unlabeled tracks will not be matched correctly with this cli.**

### File vs. Library

The cli can be used two different ways:

* Specify the full path of a **single** matroska file (.mkv) to be modified (`-f, --file`)
* Specify the full path of a **collection** of matroska files (.mkv) to be modified (`-lib, --library`)

From there you can choose to change the default audio (`-a, --audio`) and/or subtitle (`-s, --subtitle`) of the media file.

### Default Method: Strict vs. Lazy

The default methodologies for changing the track defaults is as follows (`-dm, --default-method`):
> **NOTE:** This only applies if you are trying to change **audio** AND **subtitles** at the SAME TIME

* **"Strict"** (default): The specified NEW media file language tracks for BOTH the audio
and subtitle tracks must exist in the track list (if ONE is missing, then no changes made to file)
  * EX: If the audio language track is missing but not the subtitle track, then no changes
  are made to the file even though the subtitle track exists
* **"Lazy"**: The specified NEW media file language tracks for EITHER audio and/or subtitle
tracks must exist in the track list (if BOTH are missing, then no changes made to file)
  * EX: If the audio language track is missing but not the subtitle track, then the audio
  stays the same and the default subtitle track is changed (and vice verse)

### Depth

The depth arg (`-d, --depth`) specifies how many directories deep to search for media files within a given root directory.
Meaning if you have a root directory _Movies_ but each movie is in its own folder within the root directory, specifying
`--depth 1` will instruct the cli to additionally search (it will still search for media files at the root level),
at a maximum, one directory deeper for media files.

> **NOTE:** There is currently **no upper max limit** of how many directories deep to search. You can put 1000 if you really
> wanted to, but it would take a considerable amount of time to complete the search through all of them (if it were
> really 1000 directories deep).

### Verbosity

There are various logging levels implemented in this cli: `0: NONE (Default), 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR`.
By default, no logs are produced but the log level can easily be changed using the `-v, --verbose` cli arg.

## CLI Parameters

```
-mkvpe-loc, --mkvpropedit-location  Full path of "mkvpropedit" binary location (OPTIONAL if the binary is on system path).
                                    EX: "home/downloads/MKVToolNix/mmkvpropedit.exe"
-mkvm-loc, --mkvmerge-location      Full path of "mkvmerge" binary location (OPTIONAL if the binary is on system path).
                                    EX: "home/downloads/MKVToolNix/mkvmerge.exe"
-f, --file                          Full file path of desired .mkv file
-lib, --library                     Full directory path of desired group of .mkv files
-a, --audio                         Desired audio language (refer to language codes (CANNOT be 'OFF'): -lc, --language-codes)
-s, --subtitle                      Desired subtitle language (refer to language codes (CAN be 'OFF'): -lc, --language-codes)

-dm, --default-method               The method of changing the default audio and subtitle language tracks ('strict' or 'lazy')
                                    * "Strict" (default): The specified NEW media file language tracks for BOTH the audio
                                      and subtitle tracks must exist in the track list (if ONE is missing, then no changes made to file)
                                      * EX: If the audio language track is missing but not the subtitle track, then no changes
                                        are made to the file (even thought the subtitle track exists)
                                    * "Lazy": The specified NEW media file language tracks for EITHER audio and/or subtitle
                                      tracks must exist in the track list (if BOTH are missing, then no changes made to file)
                                      * EX: If the audio language track is missing but not the subtitle track, then the audio
                                        stays the same and the default subtitle track is changed (and vice verse)

-d, --depth                         When using the '-lib' arg, how many directories deep to search within the specified library folder (Default: 0)
-ext, --file-extensions             Specify media file extensions to search for in a comma separated list, EX: .mkv,.mp4,.avi
-dr, --dry-run                      Perform a dry run, no changes made to files but summary of predicted changes will be outputted
-v, --verbose                       Adjust log level (0: NONE (Default), 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR)
-lc, --language-codes               Print language codes to console
-V, --version                       Show program's version number and exit
-h, --help                          Display argument descriptions and exit
```

## Issues

If you have any issues with the cli: please open an issue about what happened, what you expect should have happened and
include all relevant log output. This should ensure a quick and speedy debugging process and issue remediation.

## Suggestions

If you have any suggestions for additions and/or improvements to the cli, please open a feature request detailing what you
would like to have added.

## Contributions

If you would like to make a contribution, please first open an issue or feature request detailing why these changes
should be added to the cli and then link your PR to the issue for tracking purposes. Your PR should detail all changes
made to the cli in a clear and concise manner.

## Future Improvements

Future possible improvements and/or additions:

* Add Unit Tests
* Rework cli to be a bit more modernized using [rich-click](https://github.com/ewels/rich-click)
