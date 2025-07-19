<div align="center">
  <h1 style="font-size: 3em; margin-bottom: 0.1em;">MKVAudioSubsDefaulter</h1>
</div>

<p align="center">
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/releases"><img class="shield" src="https://img.shields.io/github/v/release/Robert-Zacchigna/MKVAudioSubsDefaulter" alt="GitHub Release"></a>
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/blob/main/LICENSE"><img class="shield" src="https://img.shields.io/github/license/Robert-Zacchigna/MKVAudioSubsDefaulter%20" alt="GitHub License"></a>
    <a href="https://www.python.org/downloads/"><img class="shield" src="https://img.shields.io/badge/python->=3.9-blue" alt="GitHub Pipenv locked Python version"></a>
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/commits/main"><img class="shield" src="https://img.shields.io/github/commits-since/Robert-Zacchigna/MKVAudioSubsDefaulter/latest" alt="GitHub commits since latest release"></a>
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/issues"><img class="shield" src="https://img.shields.io/github/issues/Robert-Zacchigna/MKVAudioSubsDefaulter" alt="GitHub Issues or Pull Requests"></a>
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/releases"><img class="shield" src="https://img.shields.io/github/downloads/Robert-Zacchigna/MKVAudioSubsDefaulter/total" alt="GitHub Downloads (all assets, all releases)"></a>
    <a href="https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/releases/latest"><img class="shield" src="https://img.shields.io/github/downloads/Robert-Zacchigna/MKVAudioSubsDefaulter/latest/total" alt="GitHub Downloads (all assets, latest release)"></a>
</p>

Simple multi-processing python cli to set the default audio and/or subtitles of a single matroska (.mkv) file or a
library of files WITHOUT having to remux the file.

The main use case for this cli was being able to set the default tracks of matroska media files without having to remux
the file.

Matroska media files have the unique makeup of being able to edit parts of the metadata of the file (like the default
tracks) _without_ having to remux the whole file (which this cli aims to make as easy as possible).

> [!NOTE]
> To be extra clear, this cli only works on `.mkv` files and will filter out all other file types.

![](https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/blob/main/example.gif)

## Contents

* [Dependencies](#dependencies)
* [Future Improvements](#future-improvements)
* [Usage](#usage)
  * [Quick Start Examples](#quick-start-examples)
  * [MKVToolNix (mkvpropedit and mkvmerge)](#mkvtoolnix-mkvpropedit-and-mkvmerge)
  * [Dry Run](#dry-run)
  * [Language Codes (Audio and Subtitles)](#language-codes-audio-and-subtitles)
  * [File vs. Library](#file-vs-library)
  * [Default Method: Strict vs. Lazy](#default-method-strict-vs-lazy)
  * [Regex Filtering](#regex-filtering)
  * [Depth](#depth)
  * [Multi-Processing](#multi-processing)
  * [Verbosity](#verbosity)
* [Advanced Usage (Orchestration)](#advanced-usage-orchestration)
  * [Cron Schedule](#cron-schedule)
  * [DAG (Directed Acyclic Graph)](#dag-directed-acyclic-graph)
* [CLI Parameters](#cli-parameters)
* [Issues](#issues)
* [Suggestions](#suggestions)
* [Contributions](#contributions)
  * [Development Setup](#development-setup)

## Dependencies

* Python **3.9+** ([python.org](https://www.python.org/downloads/))
  * External Python Modules
    * [tqdm](https://github.com/tqdm/tqdm) (for the progress bar)
      * `pip install -r requirements.txt`
* [MKVToolNix](https://mkvtoolnix.download/downloads.html) (Download for your OS)
  * You specifically need the following binaries from `MKVToolNix` added to your system `path`
    * [mkvmerge](https://mkvtoolnix.download/doc/mkvmerge.html)
    * [mkvpropedit](https://mkvtoolnix.download/doc/mkvpropedit.html)

## Future Improvements

Future possible improvements and/or additions (in no particular order):

- [ ] Add Unit Tests
- [ ] Rework cli to be a bit more modernized using [rich-click](https://github.com/ewels/rich-click)
- [ ] Output media file statuses to log files depending on their status (see top of `change_default_tracks()`
      for statuses)
- [x] (**COMPLETED:** `05/03/2024`) Add `-regfil, --regex-filter` arg to filter for specific media files based on a
      `regex` query
- [x] (**COMPLETED:** `05/10/2024`) Implement **multi-processing** for faster media file processing
  - [x] Add `-plsz, --pool-size` arg to specify size of processing pool

## Usage

```
[-mkvpe-loc MKVPROPEDIT_LOCATION] [-mkvm-loc MKVMERGE_LOCATION] [-f FILE | -lib LIBRARY] [-a AUDIO] [-s SUBTITLE] [-dm DEFAULT_METHOD] [-d DEPTH] [-ext FILE_EXTENSIONS] [-plsz POOL_SIZE] [-regfil REGEX_FILTER] [-dr] [-v VERBOSE] [-lc | -V | -h]
```

### Quick Start Examples

* HELP: `python MKVAudioSubsDefaulter.py -h`
* LANGUAGE-CODES: `python MKVAudioSubsDefaulter.py -lc`
* BASIC: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off`
* VERBOSE: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off -v 1`
* LAZY: `python MKVAudioSubsDefaulter.py -f "path/to/your/file" -a eng -s off -v 1 -dm lazy`
* DEPTH: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s eng -v 1 -d 1 -dm lazy`
* REGEX-FILTER: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s eng -v 1 -d 1 -dm lazy -regfil (The|Good|Knight)`
* MULTI-PROCESS: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s eng -v 1 -d 1 -dm lazy -regfil (The|Good|Knight) -plsz 2`
* DRY-RUN: `python MKVAudioSubsDefaulter.py -lib "path/to/your/library" -a eng -s spa -v 1 -d 1 -dr`

### MKVToolNix (mkvpropedit and mkvmerge)

In order to use this cli you will need to have downloaded [MKVToolNix](https://mkvtoolnix.download/downloads.html) and either have added
[mkvmerge](https://mkvtoolnix.download/doc/mkvmerge.html) and [mkvpropedit](https://mkvtoolnix.download/doc/mkvpropedit.html)
to your system `path` OR specify the full path of those binaries using these cli args:

* `-mkvm-loc, --mkvmerge-location`
* `-mkvpe-loc, --mkvpropedit-location`

### Dry Run

It is HIGHLY recommended to use the `-dr, --dr-run` arg when first using the cli to make sure of the changes you want it
to make. This arg will let the cli know to run through the file(s) BUT MAKE NO CHANGES TO THE FILE(S). It will output an
estimate change count of how many files WOULD HAVE BEEN changed by the cli if it was not a dry run.

> [!NOTE]
> It is better to try the cli on a smaller subset of files from your library FIRST and then move onto the full library
> of files after you are confident in the changes it will make.

### Language Codes (Audio and Subtitles)

Language codes are the codes in the track metadata that specify what language a specific track is (i.e. "eng" = English).

You can list out all valid language codes using language code cli arg: `-lc, --language-codes`

> [!NOTE]
> The language code metadata is the basis of how this cli functions. Without language codes in the track
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
> [!NOTE]
> This only applies if you are trying to change **audio** AND **subtitles** at the SAME TIME

* **"Strict"** (default): The specified NEW media file language tracks for BOTH the `audio`
and `subtitle` tracks must exist in the track list (if ONE is missing, then no changes made to file).
  * EX: If the audio language track is missing but not the subtitle track, then no changes
  are made to the file even though the subtitle track exists.
* **"Lazy"**: The specified NEW media file language tracks for EITHER `audio` and/or `subtitle`
tracks must exist in the track list (if BOTH are missing, then no changes made to file).
  * EX: If the audio language track is missing but NOT the subtitle track, then the audio
  stays the same and the default subtitle track is changed (and vice verse).

### Regex Filtering

The regex filtering arg (`-regfil, --regex-filter`) can only be used with the library arg (`-lib, --library`) and it
allows for the specification of a [regex query](https://en.wikipedia.org/wiki/Regular_expression) to be applied as a
filter when searching through a media library for specific media files to apply defaults to.

**For example**, this query `(The|Good|Knight)`, will only pick out media files that have names that start with either
"The", "Good", or "Knight" (all other names will be ignored).

> [!NOTE]
> This is a very simple example but any valid regex will work. If you want to play around with python regex,
> I've found this site to be helpful when developing regex query strings: [Pythex](https://pythex.org/)

### Depth

The depth arg (`-d, --depth`) specifies how many directories deep to search for media files within a given root directory.
Meaning if you have a root directory _Movies_ but each movie is in its own folder within the root directory, specifying
`--depth 1` will instruct the cli to additionally search (it will still search for media files at the root level),
at a maximum, one directory deeper for media files.

> [!NOTE]
> There is currently **no upper max limit** of how many directories deep to search. You can put 1000 if you really
> wanted to, but it would take a considerable amount of time to complete the search through all of them (if it were
> really 1000 directories deep).

### Multi-Processing

The pool-size arg (`-plsz, --pool-size`) uses the built-in python [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) module and can be used to
specify how big the processing pool should be. The bigger the pool, the faster media files will be processed.

EX: `-plsz 2` creates a processing pool of 2

> [!NOTE]
> Too large of a pool can have the adverse effect of slowing down the processing. Thus, depending on your
> machine and size of your library, it is recommended stay between 1-5 (Default: 1).

### Verbosity

The default log level is `ERROR` but it can easily be changed using the `-v, --verbose` cli arg using the corresponding
level you desire, like so: `--verbose 0` or `-v 1`, etc...

* Logging levels implemented in this cli
  * `0 = NONE`: No logs will be generated/outputted
  * `1 = INFO`: General info along with other logging level outputs (**EXCEPT** `DEBUG`)
  * `2 = DEBUG`: Debug output used for troubleshooting and development (all other log levels also outputted)
  * `3 = WARNING`: Only warnings will be outputted
  * `4 = ERROR (Default)`: Only errors will be outputted (**default log level**)

## Advanced Usage (Orchestration)

The next logical step for this cli once you've gotten comfortable with how it works, is to get it to automagically run
as new media files get added to your library (so you don't have to worry about your file defaults ever again).

There are TONS of different ways to do this, see below for some examples.

### Cron Schedule

Simple enough, just create a cron that runs the cli with your desired args on a set schedule and forget about it.

Possible [FOSS](https://en.wikipedia.org/wiki/Free_and_open-source_software) web-app to manage crons: [Cronicle](https://github.com/jhuckaby/Cronicle)

* The downside to the above is that as your library gets bigger, the processing time will continuously get longer
  as your library grows because the cli is not smart enough to know what files it has already processed.
  * A simple solution to this is creating a second script/process that loads incoming files into a
    separate directory first (where the cli can then process the files) and then move the processed files into your
    final storage location for your media library.

### DAG (Directed Acyclic Graph)

A Very popular way to conduct orchestration is through using a [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph)
style of running tasks. There are tons of [FOSS](https://en.wikipedia.org/wiki/Free_and_open-source_software) tools that
facilitate this, they all have their pros and cons (I'll let you decide which is the best for you).

These tools offer you greater control on how you would like to process your media files (or anything else for that matter).
The main advantage is to create a DAG with logic that only processes new media files added your library and not reprocess
those that have already been processed.

You could go even further add more logic to set different defaults depending on the specific media file. For example, if
you like to watch certain media that you always want to consume in a specific language. There are tons of possibilities here.

Here are few FOSS applications (that I'm aware of) listed in alphabetical order: [Airflow](https://github.com/apache/airflow), [dagster](https://github.com/dagster-io/dagster),
[flyte](https://github.com/flyteorg/flyte), [luigi](https://github.com/spotify/luigi), [mage-ai](https://github.com/mage-ai/mage-ai), [Prefect](https://github.com/PrefectHQ/prefect).

## CLI Parameters

CLI help output: `python MKVAudioSubsDefaulter.py -h `

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

-d, --depth                         When using the '-lib/--library' arg, specify how many directories deep to search
                                    within the specified library folder (Default: 0)

-ext, --file-extensions             Specify media file extensions to search for in a comma separated list (Default: '.mkv'),
                                    EX: '.mkv,.mp4,.avi'

-plsz, --pool-size                  When using the '-lib/--library' arg, specify the size of the processing pool
                                    (number of concurrent processes) to speed up media file processing.
                                    Depending on your machine and size of your library, you should stay between 1-10 (Default: 1)

-regfil, --regex-filter             When using the '-lib/--library' arg, specify a regex query to filter for specific
                                    media files (Default: None)

-dr, --dry-run                      Perform a dry run, no changes made to files but summary of predicted changes will be outputted

-v, --verbose                       Adjust log level (0: NONE, 1: INFO, 2: DEBUG, 3: WARNING, 4: ERROR (Default))

-lc, --language-codes               Print language codes to console

-V, --version                       Show program's version number and exit

-h, --help                          Display argument descriptions and exit
```

## Issues

If you have any issues with the cli, please do the following:

* Open an [Issue](https://github.com/Robert-Zacchigna/MKVAudioSubsDefaulter/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=)
  * Describe what happened.
  * Describe what you expected to happen.
  * Include any and all relevant log output.

This should ensure a quick/speedy debugging process and issue remediation.

## Suggestions

If you have any suggestions for additions and/or improvements to the cli, please open a feature request detailing what you
would like to have added.

## Contributions

If you would like to make a contribution, please first open an issue or feature request detailing why these changes
should be added to the cli and then link your PR to the issue for tracking purposes. Your PR should detail all changes
made to the cli in a clear and concise manner.

### Development Setup

1. Fork **MKVAudioSubsDefaulter**
2. Setup development environment

    ```bash
    make devel
    ```
    OR
    ```bash
    pip install -r requirements.txt
    pip install -r requirements_dev.txt
    pip install -e .
    pre-commit install --hook-type pre-commit --hook-type pre-push
    ```

    * Lint (Run analysis - pre-commit-config)

      ```bash
      make analysis
      ```

3. Push Changes
   * Push changes to a branch on your forked repo


4. Create pull request
   * Open a pull request on **MKVAudioSubsDefaulter** and put your fork as the source of your changes


5. Wait for review approval
   * Once you have created your PR, I will do my best to review it as soon as possible
> [!NOTE]
> I am only one person, so please have patience if I don't get to the PR right away. Thank you.


6. Thank you for your contribution to **MKVAudioSubsDefaulter**!
