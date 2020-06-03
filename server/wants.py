from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import shutil
import sys
from typing import Iterable, Union, Tuple, List, Set, Optional

from config import config
from dirs import list_files_relative
from conversion import Conversion
from database import path_hash


class Want:
    def __init__(self, audio_dir: str, path: str, conversion: Conversion = None):
        self.conversion = conversion
        self.audio_dir = audio_dir
        self.path = path
        if self.conversion is not None:
            self.src_path = self.path
            self.path = os.path.splitext(self.path)[0] + "." + self.conversion.ext
        self.have = False

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        """
        >>> w = Want("", "p")
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
        >>> v = Want("", "s")
        >>> set([w, v]) - set(["p", "q"])
        {Want('', 's')}
        """
        if isinstance(other, Want):
            return self.path == other.path and self.audio_dir == self.audio_dir
        elif isinstance(other, str):
            return self.path == other
        elif isinstance(other, os.PathLike):
            return self.path == str(other)
        else:
            return NotImplemented

    def __str__(self) -> str:
        if self.conversion is None:
            return f"Want({self.audio_dir!r}, {self.path!r})"
        else:
            return f"Want({self.audio_dir!r}, {self.path!r}, {self.conversion})"

    def __repr__(self) -> str:
        return str(self)


def get_wants() -> List[Want]:
    """
    Wants-file format (where a0af9f865b are the first 10 digits of the sha256 hash of
    the utf8-encoded audio dir path):
    
        {
            "wants": [
                "a0af9f865b:artist/album/01 - song.flac",
                "a0af9f865b:some_song.mp3",
                ...
            ],
            "wants_as": [
                {
                    "codec": "opus",
                    "quality": 128,
                    "files": [
                        "a0af9f865b:artist/album/02 - song2.flac",
                        ...
                    ]
                },
                {
                    "codec": "mp3",
                    "quality": "320",
                    "files": [
                        "a0af9f865b:audiobook/chapter01.flac",
                        "a0af9f865b:audiobook/chapter02.flac",
                        ...
                    ]
                }
            ]
        }
    """
    try:
        with open(config.wants_file) as wants_file:
            if wants_file.read().strip() == "":
                raise json.JSONDecodeError("Empty file, expecting at least '{}'", "", 0)
            wants_file.seek(0)
            wants_data = json.load(wants_file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as err:
        print(f"Warning, error parsing wants file: {err}", file=sys.stderr)
        return []
    wants = []
    wants_data_wants = wants_data["wants"] if "wants" in wants_data else []
    wants_data_wants_as = wants_data["wants_as"] if "wants_as" in wants_data else []
    for json_want in wants_data_wants:
        want_dir, want_path = _split_json_want(json_want)
        if want_dir is None:
            continue
        wants.append(Want(want_dir, want_path))
    for want_conversion in wants_data_wants_as:
        conversion = Conversion(
            want_conversion["codec"], want_conversion["quality"] * 1000
        )
        for json_want in want_conversion["files"]:
            want_dir, want_path = _split_json_want(json_want)
            if want_dir is None:
                continue
            wants.append(Want(want_dir, want_path, conversion))
    return wants


def get_want_diffs(wants: Iterable[Want]) -> Tuple[List[str], List[Want]]:
    have_paths = {
        f[0]
        for f in list_files_relative(
            config.output, extensions=config.extensions, ignore_empty=True
        )
    }
    want_paths = set(wants)
    removed = have_paths - want_paths
    added = want_paths - have_paths
    sort_by_path = lambda w: w.path if isinstance(w, Want) else w
    return sorted(removed, key=sort_by_path), sorted(added, key=sort_by_path)


def remove_unwanted(removed: Iterable[str]) -> None:
    for f in removed:
        target = os.path.join(config.output, f)
        try:
            os.remove(target)
        except FileNotFoundError:
            pass
        try:
            os.removedirs(os.path.dirname(target))
        except OSError:
            pass


def add_wanted(added: Iterable[Want]) -> None:
    for f in added:
        target = os.path.join(config.output, f.path)
        os.makedirs(os.path.dirname(target), exist_ok=True)

    for f in [a for a in added if a.conversion is None]:
        target = os.path.join(config.output, f.path)
        shutil.copy2(os.path.join(f.audio_dir, f.path), target)

    with ThreadPoolExecutor(config.max_conversion_threads) as pool:
        conversion_path = {
            pool.submit(fc.conversion.do, fc): fc.path
            for fc in added
            if fc.conversion is not None
        }
        for future in as_completed(conversion_path):
            if not future.result():
                print(
                    f"Warning: Could not convert {conversion_path[future]!r}",
                    file=sys.stderr,
                )


def fulfill_wants() -> None:
    removed, added = get_want_diffs(get_wants())
    remove_unwanted(removed)
    add_wanted([a for a in added if a.conversion is None])
    add_wanted([a for a in added if a.conversion is not None])


def _split_json_want(json_want: str) -> Tuple[Optional[str], str]:
    want_dir_hash, want_path = json_want.split(":", 1)
    for audio_dir in config.audio:
        if path_hash(audio_dir) == want_dir_hash:
            return audio_dir, want_path
    return None, ""


if __name__ == "__main__":
    import doctest

    doctest.testmod()
