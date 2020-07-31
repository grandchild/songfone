from collections import OrderedDict
from io import BytesIO
import os
from PIL import Image  # type: ignore
import re
import sys
from typing import Optional, Iterable, List

from config import config


class CoverNotFoundError(FileNotFoundError):
    pass


class CoverArt:
    """
    >>> cover = CoverArt(
    ...     "/path/to/artist/album/song.flac",
    ...     hints=["The Beatles", "White Album"]
    ... )
    >>> cover.get()
    "/path/to/artist/album/cover.jpg"
    >>> cover.get_data()
    b'\x01\x02...'
    """

    standard_names: List[str] = ["cover", "folder"]
    extensions: List[str] = ["png", "jpeg", "jpg", "bmp", "gif"]

    _cache: OrderedDict = OrderedDict()
    _cache_capacity = config.cover_scan_cache_size

    def __new__(
        cls, audio_dir: str, audio_relpath: str, hints: Optional[Iterable[str]] = None
    ):
        """A caching constructor for cover images for audio files.
        Searches for matching image files around the given audio file and selects one or
        none. Transparently returns a previous instance if the image path was already
        seen for another audio file. Images are evicted from the cache after
        a number (set in config.cover_scan_cache_size) of other images have been loaded.
        """
        audio_path = os.path.join(audio_dir, audio_relpath)
        if hints:
            hints = [hint.lower() for hint in hints]
        else:
            hints = []
        image_abspath = cls._search(audio_path, hints)
        if image_abspath is None:
            raise CoverNotFoundError(f"No cover art for {audio_path!r}")
        image_path = os.path.relpath(image_abspath, audio_dir)
        if image_path not in cls._cache:
            cls._cache[image_path] = super().__new__(cls)
            cls._cache[image_path].image_path = image_path
        else:
            cls._cache.move_to_end(image_path)
        if len(cls._cache) > config.cover_scan_cache_size:
            oldest = next(iter(cls._cache))
            del cls._cache[oldest]
        return cls._cache[image_path]

    def __init__(self, audio_dir: str, *args):
        self.audio_dir = audio_dir
        self.image_mtime: Optional[int] = None
        self.image_data: Optional[BytesIO] = None
        self.image_path: str  # set in __new__, declared here for typing

    @classmethod
    def _search(cls, audio_path: str, hints: Iterable[str]) -> Optional[str]:
        """Search for coverart files and return the best candidate.
        Searches dir containing the file and, if no images were found among sibling
        files, the parent directory too.
        """
        file_dir = os.path.dirname(audio_path)
        parent_dir = os.path.dirname(file_dir)
        candidates = []
        max_filesize: Optional[int] = None
        for path in [file_dir, parent_dir]:
            for file in os.listdir(path):
                filename_lower = file.lower()
                if not any([filename_lower.endswith(ext) for ext in cls.extensions]):
                    continue
                filepath = os.path.join(path, file)
                filesize = os.stat(filepath).st_size
                candidates.append((filepath, filename_lower, filesize))
                if max_filesize is None or filesize > max_filesize:
                    max_filesize = filesize
            if candidates:
                break
        if candidates and max_filesize:
            rating = lambda c: cls._rate_as_cover_file(c[1], hints, c[2], max_filesize)
            candidates.sort(key=rating, reverse=True)
            return candidates[0][0]
        return None

    @classmethod
    def _rate_as_cover_file(
        cls, filename_lower: str, hints: Iterable[str], filesize: int, max_filesize: int
    ) -> float:
        rating = 0.0
        if any([n in filename_lower for n in cls.standard_names]):
            rating += 0.6
        for hint in hints:
            if hint in filename_lower:
                rating += 0.3
        rating += (filesize / max_filesize) * 0.5
        ### Checking for image size is quite expensive. Turn it off, and rely on
        ### filesize as a rough gauge for image quality.
        # img = Image.open(os.path.join(path, filename))
        # if any([s < config.cover_max_dimension for s in img.size]):
        #     rating *= 0.5
        return rating

    def get_data(self, image_format="JPEG") -> Optional[bytes]:
        """Load (and possibly resize to fit cover_max_dimension) the cover image.
        Returns the bytes of the image file in the given *image_format*, or None on
        error.
        """
        if self.image_data is not None:
            return self.image_data.getvalue()
        self.image_data = BytesIO()
        try:
            image = Image.open(os.path.join(self.audio_dir, self.image_path))
            if any([s > config.cover_max_dimension for s in image.size]):
                scale = config.cover_max_dimension / max(image.size)
                image = image.resize(
                    (int(image.size[0] * scale), int(image.size[1] * scale)),
                    Image.LANCZOS,
                )
            image.save(self.image_data, image_format)
        except OSError as err:
            if "cannot write mode" in str(err):
                image.convert("RGB").save(self.image_data, image_format)
            else:
                # e.g. "image file is truncated", or other image loading/saving errors
                print(
                    f"Warning, image data load/save failed for {self.image_path}:",
                    err,
                    file=sys.stderr,
                )
                return None

        return self.image_data.getvalue()

    def __hash__(self) -> int:
        return hash(self.image_path)

    def __eq__(self, other) -> bool:
        try:
            if self.image_path is None or other.image_path is None:
                return False
            return self.image_path == other.image_path
        except AttributeError:
            return False
