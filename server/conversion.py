import os
import sys
from typing import Iterable

PYDUB_AVAILABLE = True
try:
    from pydub import AudioSegment
except ImportError:
    PYDUB_AVAILABLE = FALSE

from config import config
from database import get_song_tags


class Conversion:
    """
    A desired conversion from one audio codec into another.

    Attributes:
        
        codec (`str`): A string identifier of the audio codec. Often identical
            to the file extension.
        quality (`int`): The codec sample rate in bits per second.
    """

    _codecs_ext_eq = ["mp3", "flac", "opus", "mp4", "m4a"]
    _codecs_ext_neq = {"ogg": "libvorbis"}
    valid_codecs = _codecs_ext_eq + list(_codecs_ext_neq.values())

    def __init__(self, codec: str, quality: int):
        self.codec = codec.lower()
        if self.codec not in self.valid_codecs:
            raise NotImplementedError("Unknown audio codec")
        self.pydub_codec = (
            self.codec
            if self.codec in self._codecs_ext_eq
            else self._codecs_ext_neq[self.codec]
        )

        self.quality = quality

    def get_ext(self) -> str:
        if self.codec in self._codecs_ext_eq:
            return "." + self.codec
        elif self.codec in self._codecs_ext_neq:
            return "." + self._codecs_ext_neq[self.codec]
        else:
            raise NotImplementedError("Unknown audio codec")

    def do(self, want: "Want") -> bool:
        if not PYDUB_AVAILABLE:
            print("pydub not available, conversions not possible", file=sys.stderr)
            return False
        src_file = os.path.join(want.audio_dir, want.src_path)
        print(f"Converting {want.path}... ", end="")
        try:
            audio = AudioSegment.from_file(src_file)
            audio.export(
                os.path.join(config.output, want.path),
                format=self.pydub_codec,
                bitrate=f"{self.quality}",
                tags=get_song_tags(want.src_path),
            )
        except Exception:
            print("failed")
            return False
        print("done")
        return True

    def __str__(self):
        return f"in {self.codec.upper()}@{self.quality}kbps"
