import json
import os
import sys


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

    _error = None
    audio = "~/Music"
    output = "~/.local/share/songfone/output"
    extensions = ["mp3", "flac", "mp4", "ogg", "opus"]
    wants = ".songfone/wants.json"
    database = ".songfone/songs.db"

    def load(self, file: str) -> None:
        self._load_from_file(file)
        self._set_file_paths()
        self._check_audio_dir()

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
        self.audio = os.path.expanduser(self.audio)
        self.output = os.path.expanduser(self.output)
        self.wants_file = os.path.join(self.output, self.wants)
        self.database_file = os.path.join(self.output, self.database)

    def _check_audio_dir(self):
        if not os.path.isdir(self.audio):
            raise FileNotFoundError("Error, audio directory does not exist")

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
