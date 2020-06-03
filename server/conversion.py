import os
from shutil import which
from subprocess import run, PIPE, STDOUT
import sys
from typing import Iterable, List, Optional

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

    _codecs_ext_eq = ["mp3", "flac", "mp4", "m4a"]
    _codecs_ext_neq = {"ogg": "libvorbis", "opus": "libopus"}
    valid_codecs = _codecs_ext_eq + list(_codecs_ext_neq.keys())

    def __init__(self, ext: str, quality: int):
        self.ext = ext.lower()
        if self.ext not in self.valid_codecs:
            raise ValueError(f"Unknown audio extension {self.ext}")
        self.ffmpeg_codec = (
            self.ext
            if self.ext in self._codecs_ext_eq
            else self._codecs_ext_neq[self.ext]
        )
        self.quality = quality

    def ffmpeg(
        self,
        src: str,
        dest: str,
        codec: str = "libopus",
        bitrate: int = 128000,
        tags: Optional[dict] = None,
    ) -> bool:
        """Run the conversion. Return 0 on success."""
        cmd: List[str] = [
            config.ffmpeg_bin,
            "-y",
            "-i",
            src,
            "-c:a",
            codec,
            "-b:a",
            str(bitrate),
            dest,
        ]
        if tags is not None:
            for field, value in tags.items():
                cmd += ["-metadata", f'{field}="{value}"']
        conversion = run(cmd, stdout=PIPE, stderr=STDOUT)
        return conversion.returncode == 0

    @staticmethod
    def ffmpeg_available() -> bool:
        """Return True, if the ffmpeg command is available."""
        return which(config.ffmpeg_bin) is not None

    def do(self, want: "Want") -> bool:
        """Run the conversion. Return 0 on success."""
        if not self.ffmpeg_available():
            print("ffmpeg not available, conversions not possible", file=sys.stderr)
            return False
        src_file = os.path.join(want.audio_dir, want.src_path)
        print(f"Converting {want.path}")
        success: bool = self.ffmpeg(
            src=src_file,
            dest=os.path.join(config.output, want.path),
            codec=self.ffmpeg_codec,
            bitrate=self.quality,
            # tags=get_song_tags(want.src_path),
        )
        return success

    def __str__(self) -> str:
        return f"in {self.ext.upper()}@{self.quality//1024}kbps"
