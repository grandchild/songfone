import json
import os
import re
import sys
from typing import Union, Optional, List

MAX_CONVERT_THREADS = 512  # Just an upper bound for max_conversion_threads sanity.


class Config:
    """
    Loads a given config file for songfone.
    
    Expected settings are:
    * audio         One or more directories containing audio files.
    
    Optional settings are:
    * output        A synced directory containing the songs to be uploaded, as well as
                    the database and control file.
    * extensions    List of audio file extensions to expect. Defaults to
                    ["mp3", "flac", "mp4", "ogg", "opus"]
    * wants         The name of the JSON wants file. Defaults to
                    ".songfone/songs.wants".
    * database      The name of the SQLite database file. Defaults to
                    ".songfone/songs.db".
    * ffmpeg_bin    The ffmpeg binary to use for conversion. Defaults to "ffmpeg".
    * max_conversion_threads
                    A number or expression that sets the maximum number of threads to
                    use for converting audio files.
    * scan_for_covers
                    Whether to look for image files with cover art for each audio file.
    * cover_max_dimension
                    The largest dimension in pixels for cover images. Images larger than
                    this will be downscaled to match.
    * cover_scan_cache_size
                    The number of cover art image data to keep in the cache for
                    subsequent audio files (so songs in an album don't all fetch the
                    image each time).
                    Can be used to tune scan RAM usage for cover art data. Lower values
                    mean less cached images, but if the same cover file matches again
                    later on, the image will be loaded (and possibly resized) twice or
                    more. Assuming a somewhat sane directory structure, it's safe to
                    keep this fairly low. Defaults to 5. Should be insignificant.

    >>> c = Config()
    >>> c.database
    '.songfone/songs.db'
    """

    audio: Union[str, List[str]] = "~/Music"
    output: str = "~/.local/share/songfone"
    extensions: List[str] = ["mp3", "flac", "mp4", "ogg", "opus"]
    wants: str = ".songfone/songs.wants"
    database: str = ".songfone/songs.db"
    ffmpeg_bin: str = "ffmpeg"  # default: ffmpeg is in $PATH
    max_conversion_threads: int = 2
    scan_for_covers: bool = True
    cover_max_dimension: int = 512
    cover_scan_cache_size: int = 5
    _error: Optional[Exception] = None

    def load(self, file: str) -> None:
        self._load_from_file(file)
        self._set_file_paths()
        self._check_audio_dir()
        self._eval_max_threads_expr()

    def _load_from_file(self, file):
        try:
            with open(file) as config_file:
                config = json.load(config_file)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as err:
            self._error = err
            raise err
        for key, value in config.items():
            setattr(self, key.replace(" ", "_"), value)

    def _set_file_paths(self):
        if isinstance(self.audio, str):
            self.audio = [os.path.expanduser(self.audio)]
        elif isinstance(self.audio, list):
            self.audio = [os.path.expanduser(a) for a in self.audio]
        self.output = os.path.expanduser(self.output)
        self.wants_file = os.path.join(self.output, self.wants)
        self.database_file = os.path.join(self.output, self.database)

    def _check_audio_dir(self):
        for a in self.audio:
            if not os.path.isdir(a):
                raise FileNotFoundError(f"Error, audio directory {a!r} does not exist")

    def _eval_max_threads_expr(self):
        if isinstance(self.max_conversion_threads, str):
            config_str_value = self.max_conversion_threads.lower()
            match = re.fullmatch(
                r"(?:\d+)|(?:cpus *(?:([+\-*/]) *(\d)+)?)", config_str_value
            )
            if match is not None:
                if "cpus" not in config_str_value:
                    self.max_conversion_threads = int(config_str_value)
                    return
                cpus = os.cpu_count()
                if match.lastindex is None:
                    self.max_conversion_threads = cpus
                    return
                op = match.group(1)
                val = int(match.group(2))
                if op == "+":
                    self.max_conversion_threads = min(MAX_CONVERT_THREADS, cpus + val)
                elif op == "-":
                    self.max_conversion_threads = min(MAX_CONVERT_THREADS, cpus - val)
                elif op == "*":
                    self.max_conversion_threads = min(MAX_CONVERT_THREADS, cpus * val)
                elif op == "/":
                    try:
                        self.max_conversion_threads = min(
                            MAX_CONVERT_THREADS, cpus // val
                        )
                    except ZeroDivisionError:
                        print(
                            f"Error, division by zero: {cpus} / {val}"
                            " - Conversions will run in a single thread.",
                            file=sys.stderr,
                        )
                        self.max_conversion_threads = 1
                else:
                    print(
                        "Error, you somehow exploited re.fullmatch and made it here."
                        " Congratulations. Have a cookie.",
                        file=sys.stderr,
                    )
                    sys.exit(-1337)
            else:
                print(
                    "Error, max_conversion_threads expression is invalid: "
                    f"{self.max_conversion_threads!r}\n"
                    "Use only 'cpus [+|-|*|/ <number>]', "
                    "e.g.: 'cpus - 2', 'CPUs/4', 'cpus'.",
                    file=sys.stderr,
                )
        elif isinstance(self.max_conversion_threads, int):
            pass
        else:
            print(
                "Error, max_conversion_threads is invalid: "
                f"{self.max_conversion_threads!r}"
                " - Conversions will run in a single thread.",
                file=sys.stderr,
            )
            self.max_conversion_threads = 1

    def __getattribute__(self, key: str):
        err = super().__getattribute__("_error")
        if err is not None:
            raise RuntimeError(f"Config file could not be parsed: {err}")
        return super().__getattribute__(key)

    def make_output(self):
        """Create the output dir, and return True on success, False otherwise."""
        try:
            try:
                os.mkdir(self.output)
            except FileExistsError:
                pass
            os.makedirs(os.path.dirname(self.wants_file), exist_ok=True)
            os.makedirs(os.path.dirname(self.database_file), exist_ok=True)
            if not os.path.exists(self.wants_file):
                with open(self.wants_file, "a") as new_wants:
                    print("{}", file=new_wants)
        except Exception as err:
            self._error = err
            raise err


config = Config()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
