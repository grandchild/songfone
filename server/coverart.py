from io import BytesIO
import os
import re
from dataclasses import dataclass
from PIL import Image
from typing import Union, Optional, Iterable, List

from config import config


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

    def __init__(self, audio_path: str, hints: Optional[Iterable[str]] = None):
        self.audio_path = audio_path
        self.hints = hints or []
        self.hints = [h.lower() for h in self.hints]
        self.image_path = None

    def get(self) -> Union[str, None]:
        """
        """
        # search dir containing the file...
        file_dir = os.path.dirname(self.audio_path)
        # ...and optionally search parent dir
        parent_dir = os.path.dirname(file_dir)
        candidates = []
        for path in [file_dir, parent_dir]:
            for file in os.listdir(path):
                filepath = os.path.join(path, file)
                rating = self._rate_as_cover_file(file, path)
                if rating > 0:
                    print(rating)
                    candidates.append((rating, filepath))
            if candidates:
                break  # stop searching after first dir level that contains images
        if candidates:
            candidates.sort(key=lambda c: c[0])
            return candidates[-1][1]
        return None

    def _rate_as_cover_file(self, filename, path) -> float:
        filename_lower = filename.lower()
        rating = 0.0
        if not any([filename_lower.endswith(ext) for ext in self.extensions]):
            return rating
        print(f"rating {path}/{filename}...")
        rating = 1.0
        if any([n in filename_lower for n in self.standard_names]):
            rating += 0.3
        for hint in self.hints:
            if hint in filename_lower:
                rating += 0.3
        # TODO(jakob): Check & rate images by dimensions. Images >= than
        # config.cover_max_dimension should get a higher rating while smaller images
        # should get a penalty (but retain > 0, since they already matched).
        img = Image.open(os.path.join(path, filename))
        if any([s < config.cover_max_dimension for s in img.size]):
            rating *= 0.5
        return rating

    def get_png_data(self) -> Union[BytesIO, None]:
        if self.image_path is None:
            return None
        img = Image.open(self.image_path)
        if any([s > config.cover_max_dimension for s in img.size]):
            scale = config.cover_max_dimension / max(img.size)
            img = img.rescale((img.size[0] * scale, img.size[1] * scale), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, "PNG")
        return buf

    def __hash__(self) -> str:
        return hash(self.image_path)

    def __eq__(self, other) -> bool:
        try:
            return self.image_path == other.image_path
        except AttributeError:
            return False
