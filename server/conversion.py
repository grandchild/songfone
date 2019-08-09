from pydub import AudioSegment
import os
from typing import Iterable

from config import config


class Conversion:
    _codecs_ext_eq = ["mp3", "flac", "opus", "mp4", "m4a"]
    _codecs_ext_neq = {"vorbis": "ogg"}
    valid_codecs = _codecs_ext_eq + list(_codecs_ext_neq)

    def __init__(self, codec: str, quality: int):
        self.codec = codec.lower()
        if self.codec not in self.valid_codecs:
            raise NotImplementedError("Unknown audio codec")
        self.quality = quality

    def get_ext(self) -> str:
        if self.codec in self._codecs_ext_eq:
            return "." + self.codec
        elif self.codec in self._codecs_ext_neq:
            return "." + self._codecs_ext_neq[self.codec]
        else:
            raise NotImplementedError("Unknown audio codec")

    def do(self, want: "Want") -> bool:
        from database import get_song_tags

        src_file = os.path.join(config.audio, want.src_path)
        print(f"Converting {want.src_path} to {want.path}... ", end="")
        try:
            audio = AudioSegment.from_file(src_file)
            audio.export(
                os.path.join(config.output, want.path),
                format=self.codec,
                bitrate=f"{self.quality}k",
                tags=get_song_tags(src_file),
            )
        except Exception:
            print("failed")
            return False
        print("done")
        return True

    def __str__(self):
        return f"in {self.codec.upper()}@{self.quality}kbps"


def mimes_to_codec(mimes: Iterable[str]) -> str:
    """Utility function for turning mutagen's mime types into a single codec string."""
    if any(["codecs=opus" in m for m in mimes]):
        return "opus"
    else:
        return mimes[0].replace("audio/", "")
