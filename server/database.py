import os
import sys
from glob import glob
import sqlite3
import mutagen  # type: ignore
from mutagen.mp3 import MP3  # type: ignore
from mutagen.easyid3 import EasyID3  # type: ignore
from hashlib import sha256
from typing import List, Dict
from typing import Iterable, MutableMapping, Any, Optional

from config import config
from coverart import CoverArt, CoverNotFoundError
from dirs import list_files_relative


DB_LAYOUT = """
    CREATE TABLE IF NOT EXISTS audio_dir (
        path_hash NOT NULL UNIQUE
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS song USING fts4 (
        audio_dir NOT NULL,
        path NOT NULL,
        codec,
        quality,
        length_sec,
        filesize,
        mtime,
        cover
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS tag USING fts4 (
        song NOT NULL,
        field NOT NULL,
        value
    );

    CREATE TABLE IF NOT EXISTS cover (
        audio_dir NOT NULL,
        file_path NOT NULL,
        data,
        UNIQUE(audio_dir, file_path) ON CONFLICT IGNORE
    );
"""

DB_COMMANDS = {
    "new tag": "INSERT INTO tag VALUES (?, ?, ?)",
    "new cover": "INSERT INTO cover VALUES (?, ?, ?)",
    "get audio dir id": "SELECT ROWID FROM audio_dir WHERE path_hash = ?",
    "get song": "SELECT ROWID, * FROM song WHERE audio_dir = ? AND `path` = ?",
    "get song tags": "SELECT field, value FROM tag WHERE song in (SELECT rowid FROM song WHERE `path` = ?)",
    "clear db": "DROP TABLE IF EXISTS audio_dir; DROP TABLE IF EXISTS song; DROP TABLE IF EXISTS tag",
    "clear song tags": "DELETE FROM tag WHERE song = ?",
}


def scan_audio_dir(audio_dir: str, db: sqlite3.Connection) -> None:
    cursor = db.cursor()
    audio_dir_hash = path_hash(audio_dir)
    audio_dir_id = _upsert(cursor, "audio_dir", {"path_hash": audio_dir_hash})
    last_prefix = ""
    commit_every = 800  # rows
    commit_cache_count = 0
    for path, stat in list_files_relative(
        audio_dir, extensions=config.extensions, ignore_empty=True
    ):
        db_song = cursor.execute(
            DB_COMMANDS["get song"], (audio_dir_id, path)
        ).fetchone()
        if (
            db_song is not None
            and db_song["mtime"] == int(stat.st_mtime)
            and db_song["filesize"] == stat.st_size
        ):
            continue
        abspath = os.path.join(audio_dir, path)
        prefix = path[: path.find("/")]
        if last_prefix != prefix:
            last_prefix = prefix
            print(f"scanning {prefix!r}")

        prev_song_id = db_song["ROWID"] if db_song is not None else None
        success = scan_song(
            cursor, audio_dir, audio_dir_id, path, stat, abspath, prev_song_id
        )
        if success:
            commit_cache_count += 1
            if commit_cache_count >= commit_every:
                commit_cache_count = 0
                db.commit()
    db.commit()


def scan_song(
    cursor: sqlite3.Cursor,
    audio_dir: str,
    audio_dir_id: int,
    path: str,
    stat: os.stat_result,
    abspath: str,
    prev_song_id: int = None,
) -> bool:
    try:
        if path.lower().endswith("mp3"):
            data = MP3(abspath, ID3=EasyID3)
        else:
            data = mutagen.File(abspath)
    except mutagen.MutagenError as err:
        print(f"Warning, could not scan metadata: {abspath!r}", file=sys.stderr)
        return False
    if data is not None:
        song_tags: MutableMapping[str, str] = {}
        cover_hints: List[str] = []
        for tag, values in data.items():
            # TODO(jakob): What should be done with multiple values for a tag?
            # Separated with comma? Slash? For now, only use the first value.
            clean_first_value = "".join([c for c in values[0] if ord(c) >= 0x20])
            if tag in ["path", "codec", "filesize", "mtime"]:
                continue
            if tag in ["artist", "album", "album_artist", "albumartist"]:
                cover_hints += values
            song_tags[tag] = clean_first_value
        cover_id = scan_song_coverart(cursor, audio_dir, path, cover_hints)
        codec = mimes_to_codec(data.mime)
        quality = data.info.bitrate if hasattr(data.info, "bitrate") else 0
        length = data.info.length
        song_id = _upsert(
            cursor,
            "song",
            {"audio_dir": audio_dir_id, "path": path},
            {
                "codec": codec,
                "quality": quality,
                "length_sec": length,
                "filesize": stat.st_size,
                "mtime": int(stat.st_mtime),
                "cover": cover_id,
            },
        )
        if prev_song_id is not None:
            cursor.execute(DB_COMMANDS["clear song tags"], (prev_song_id,))
        for tag, value in song_tags.items():
            cursor.execute(DB_COMMANDS["new tag"], (song_id, tag, value))
        return True
    return False


def scan_song_coverart(
    cursor: sqlite3.Cursor, audio_dir: str, path: str, cover_hints: Iterable[str]
):
    # Maybe cover image data should not actually be in DB but rather in actual
    # files?
    try:
        cover = CoverArt(audio_dir, path, cover_hints)
        image_data = cover.get_data()
        cover_id = _upsert(
            cursor,
            "cover",
            {"audio_dir": audio_dir, "file_path": cover.image_path},
            {"data": image_data},
        )
        # cursor.execute(
        #     DB_COMMANDS["new cover"], (audio_dir, cover.image_path, image_data),
        # )
        return cover_id
    except CoverNotFoundError:
        pass


def update_database() -> None:
    db = sqlite3.connect(config.database_file)
    db.row_factory = sqlite3.Row
    db.cursor().executescript(DB_LAYOUT)
    for audio_dir in config.audio:
        scan_audio_dir(audio_dir, db)
    db.close()


def get_song_tags(path: str) -> dict:
    db = sqlite3.connect(config.database_file)
    cursor = db.cursor()
    tags = {}
    cursor.execute(DB_COMMANDS["get song tags"], (path,))
    for field, value in cursor.fetchall():
        tags[field] = value
    return tags


def path_hash(path: str) -> str:
    """Return the first 10 digits of the sha256 hash of the utf8-encoded path string."""
    # *One* digit would probably be enough, but let's be generous :)
    return sha256(path.encode()).hexdigest()[:10]


def _upsert(
    cursor: sqlite3.Cursor,
    table: str,
    values: MutableMapping[str, Any],
    extra: Optional[MutableMapping[str, Any]] = None,
) -> int:
    """
    SQlite's INSERT OR REPLACE method creates a new rowid, even if the row existed
    before. To keep the rowid, one has to do the whole song-and-dance with select-then-
    update-or-insert, which is what this function does.

    Any values in the *values* dict will be matched in the SELECT query. Any other
    values, that (in the case of a new row) need to be filled, should be passed in the
    *extra* dict.

    >>> db = sqlite3.connect(":memory:")
    >>> cursor = db.cursor()
    >>> cursor.execute("CREATE TABLE fs(path, descr)")
    <sqlite3.Cursor object ...
    >>> _upsert(cursor, "fs", {"path": "/"}, {"descr": "root"})
    1
    >>> _upsert(cursor, "fs", {"path": "/etc"}, {"descr": "config"})
    2
    >>> _upsert(cursor, "fs", {"path": "/"}, {"descr": "root dir"})
    1
    >>> cursor.execute("SELECT descr FROM fs WHERE path = '/'").fetchone()[0]
    'root dir'
    >>> cursor.execute("SELECT descr FROM fs WHERE path = '/etc'").fetchone()[0]
    'config'
    """
    if extra is None:
        extra = {}
    select = f"SELECT ROWID FROM {table} WHERE " + " AND ".join(
        [f"`{k}`=:{k}" for k in values]
    )
    result = cursor.execute(select, values).fetchone()
    if result is not None:
        if extra:
            update = (
                f"UPDATE {table} SET "
                + ", ".join([f"`{k}` = :{k}" for k in extra])
                + " WHERE "
                + " AND ".join([f"`{k}` = :{k}" for k in values])
            )
            values.update(extra)
            cursor.execute(update, values)
        return result[0]
    else:
        values.update(extra)
        insert = (
            f"INSERT INTO {table} ("
            + ", ".join([f"`{k}`" for k in values])
            + ") VALUES ("
            + ", ".join([f":{k}" for k in values])
            + ")"
        )
        return cursor.execute(insert, values).lastrowid


def mimes_to_codec(mimes: List[str]) -> str:
    """Utility function for turning mutagen's mime types into a single codec string."""
    if any(["codecs=opus" in m for m in mimes]):
        return "opus"
    else:
        return mimes[0].replace("audio/", "")


if __name__ == "__main__":
    import doctest

    doctest.testmod(optionflags=doctest.ELLIPSIS)
