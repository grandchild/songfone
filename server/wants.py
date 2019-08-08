import json
import os
import sys

from typing import Iterable, Union, Tuple, Set

from config import config
from dirs import list_files_relative
from conversion import Conversion


class Want:
    def __init__(self, path: str, conversion: Conversion = None):
        self.conversion = conversion
        self.path = path
        if self.conversion is not None:
            self.src_path = self.path
            self.path = os.path.splitext(self.path)[0] + self.conversion.get_ext()
        self.have = False

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other: Union["Want", str, os.PathLike]) -> bool:
        """
        >>> w = Want("p")
        >>> w == "p"
        True
        >>> "p" == w
        True
        >>> "p" in set([w])
        True
        >>> w in set(["p"])
        True
        >>> set(["p", "q"]) - set([w])
        {'q'}
        >>> v = Want("s")
        >>> set([w, v]) - set(["p", "q"])
        {Want('s')}
        """
        if isinstance(other, Want):
            return self.path == other.path
        elif isinstance(other, str):
            return self.path == other
        elif isinstance(other, os.PathLike):
            return self.path == str(other)
        else:
            return NotImplemented

    def __str__(self) -> str:
        if self.conversion is None:
            return f"Want({self.path!r})"
        else:
            return f"Want({self.path!r}, {self.conversion})"

    def __repr__(self) -> str:
        return str(self)


def get_wants() -> list:
    """
    Wants-file format:
    
        {
            "wants": [
                "artist/album/01 - song.flac",
                "some_song.mp3",
                ...
            ],
            "wants_as": [
                {
                    "codec": "opus",
                    "quality": 320,
                    "files": [
                        "artist/album/02 - song2.flac",
                        ...
                    ]
                },
                {
                    "codec": "mp3",
                    "quality": "128",
                    "files": [
                        "audiobook/chapter01.flac",
                        "audiobook/chapter02.flac",
                        ...
                    ]
                }
            ]
        }
    """
    with open(config.wants_file) as wants_file:
        wants_data = json.load(wants_file)
    wants = []
    for want_path in wants_data["wants"]:
        wants.append(Want(want_path))
    for want_conversion in wants_data["wants_as"]:
        conversion = Conversion(want_conversion["codec"], want_conversion["quality"])
        for want_path in want_conversion["files"]:
            wants.append(Want(want_path, conversion))
    return wants


def get_want_diffs(wants: Iterable[Want]) -> Tuple[Set, Set]:
    have_paths = {
        f[0] for f in list_files_relative(config.output, extensions=config.extensions)
    }
    want_paths = set(wants)
    removed = have_paths - want_paths
    added = want_paths - have_paths
    return removed, added


def remove_unwanted(removed: Iterable[str]) -> None:
    for f in removed:
        target = os.path.join(config.output, f)
        if os.path.exists(target):
            os.remove(target)
        try:
            os.removedirs(os.path.dirname(target))
        except OSError:
            pass


def add_wanted(added: Iterable[Want]) -> None:
    for f in added:
        target = os.path.join(config.output, f.path)
        if os.path.exists(target):
            f.have = True
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if f.conversion is None:
            os.link(os.path.join(config.audio, f.path), target)
        else:
            if not f.conversion.do(f):
                print(f"Warning: Could not convert {f.path!r}", file=sys.stderr)


def fulfill_wants() -> None:
    removed, added = get_want_diffs(get_wants())
    remove_unwanted(removed)
    add_wanted([a for a in added if a.conversion is None])
    add_wanted([a for a in added if a.conversion is not None])


if __name__ == "__main__":
    import doctest

    doctest.testmod()
