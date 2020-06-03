import json
import os
import re
import sys
from typing import Union, Optional, List

MAX_CONVERT_THREADS = 512


class Config:
    """
    Loads a given config file for songfone.
    
    Expected settings are:
    * audio -- A directory containing audio files.
    
    Optional settings are
    * output -- A synced directory containing the songs to be uploaded, as well as the 
                database and control file.
    
    >>> c = Config("songfone.conf")
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
    cover_max_dimension: int = 1024
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
            print(f"Error, config file not loaded: {err}", file=sys.stderr)
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
                    self.max_conversion_threads = min(MAX_CONVERT_THREADS, cpus // val)
                else:
                    print(
                        "Error, you somehow exploited re.fullmatch and made it here, "
                        "congratulations. Have a cookie.",
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
                f"{self.max_conversion_threads!r}",
                file=sys.stderr,
            )

    def __getattribute__(self, key: str):
        err = super().__getattribute__("_error")
        if err is not None:
            raise RuntimeError(f"Config file could not be parsed: {err}")
        return super().__getattribute__(key)

    def make_output(self) -> bool:
        """Create the output dir, and return True on success, False otherwise."""
        try:
            os.makedirs(self.output, exist_ok=True)
            os.makedirs(os.path.dirname(self.wants_file), exist_ok=True)
            os.makedirs(os.path.dirname(self.database_file), exist_ok=True)
        except Exception as err:
            print(f"Error, cannot create output directory: {err}", file=sys.stderr)
            self._error = err
            return False
        return True


config = Config()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
