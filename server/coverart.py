from collections import OrderedDict
from io import BytesIO
import os
from PIL import Image  # type: ignore
import re
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
    >>> cover.get_png_data()
    b'\x01\x02...'
    """

    standard_names: List[str] = ["cover", "folder"]
    extensions: List[str] = ["png", "jpeg", "jpg", "bmp", "gif"]

    _cache = OrderedDict()
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
        image_path = cls._search(audio_path, hints)
        if image_path is None:
            raise CoverNotFoundError(f"No cover art for {audio_path!r}")
        if image_path not in cls._cache:
            cls._cache[image_path] = super().__new__(cls)
            cls._cache[image_path].image_path = image_path
        else:
            cls._cache.move_to_end(image_path)
        if len(cls._cache) > config.cover_scan_cache_size:
            oldest = next(iter(cls._cache))
            print(f"evicting {oldest}")
            del cls._cache[oldest]
        return cls._cache[image_path]

    def __init__(self, *args):
        self.image_mtime: Optional[int] = None
        self.image_data: Optional[BytesIO] = None

    @classmethod
    def _search(cls, audio_path: str, hints: Optional[Iterable[str]]) -> Optional[str]:
        """Search for coverart files and return the best candidate.
        Searches dir containing the file and, if no images were found among sibling
        files, the parent directory too.
        """
        file_dir = os.path.dirname(audio_path)
        parent_dir = os.path.dirname(file_dir)
        candidates = []
        for path in [file_dir, parent_dir]:
            for file in os.listdir(path):
                filepath = os.path.join(path, file)
                rating = cls._rate_as_cover_file(file, path, hints)
                if rating > 0:
                    candidates.append((rating, filepath))
            if candidates:
                break
        if candidates:
            candidates.sort(key=lambda c: c[0])
            return candidates[-1][1]
        return None

    @classmethod
    def _rate_as_cover_file(
        cls, filename: str, path: str, hints: Optional[Iterable[str]]
    ) -> float:
        filename_lower = filename.lower()
        rating = 0.0
        if not any([filename_lower.endswith(ext) for ext in cls.extensions]):
            return rating
        rating = 1.0
        if any([n in filename_lower for n in cls.standard_names]):
            rating += 0.3
        for hint in hints:
            if hint in filename_lower:
                rating += 0.3
        # TODO(jakob): Check & rate images by dimensions. Images >= than
        # config.cover_max_dimension should get a higher rating while smaller images
        # should get a penalty (but retain > 0, since they already matched).
        img = Image.open(os.path.join(path, filename))
        if any([s < config.cover_max_dimension for s in img.size]):
            rating *= 0.5
        return rating

    def get_png_data(self) -> Optional[BytesIO]:
        if self.image_data is not None:
            return self.image_data
        if self.image_path is None:
            return None
        image = Image.open(self.image_path)
        if any([s > config.cover_max_dimension for s in image.size]):
            scale = config.cover_max_dimension / max(image.size)
            image = image.rescale(
                (int(image.size[0] * scale), int(image.size[1] * scale)), Image.LANCZOS
            )
        self.image_data = BytesIO()
        image.save(self.image_data, "PNG")
        return self.image_data

    def __hash__(self) -> int:
        return hash(self.image_path)

    def __eq__(self, other) -> bool:
        try:
            if self.image_path is None or other.image_path is None:
                return False
            return self.image_path == other.image_path
        except AttributeError:
            return False
