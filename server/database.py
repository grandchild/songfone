import os
from glob import glob
import sqlite3
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from hashlib import sha256
from typing import List, Dict
from typing import Iterable, Mapping

from config import config
from dirs import list_files_relative
from conversion import mimes_to_codec

DB_LAYOUT = """
    SELECT * FROM song;
    
    DROP TABLE IF EXISTS audio_dir;
    DROP TABLE IF EXISTS song;
    DROP TABLE IF EXISTS tag;
    
    CREATE TABLE IF NOT EXISTS audio_dir (
        path_hash NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS song (
        audio_dir NOT NULL,
        path NOT NULL UNIQUE,
        codec,
        filesize,
        mtime
    );

    CREATE TABLE IF NOT EXISTS tag (
        song NOT NULL,
        field NOT NULL,
        value
    );
"""
DB_COMMANDS = {
    "new audio dir": "INSERT OR REPLACE INTO audio_dir VALUES (?)",
    "new song": "INSERT OR REPLACE INTO song VALUES (?, ?, ?, ?, ?)",
    "new tag": "INSERT OR REPLACE INTO tag VALUES (?, ?, ?)",
    "get song tags": "SELECT field, value FROM tag WHERE song in (SELECT rowid FROM song WHERE path = ?)",
}


def get_metadata(audio_path: str) -> List[Dict]:
    db_data = []
    for path, stat in list_files_relative(audio_path, extensions=config.extensions):
        abspath = os.path.join(audio_path, path)
        if path.endswith("mp3"):
            data = MP3(abspath, ID3=EasyID3)
        else:
            data = mutagen.File(abspath)
        if data is not None:
            codec = mimes_to_codec(data.mime)
            data = dict(data)
            data["path"] = path
            data["codec"] = codec
            data["filesize"] = stat.st_size
            data["mtime"] = stat.st_mtime
            db_data.append(data)
    return db_data


def save_metadata(db, audio_dir: str, db_data: Iterable[Mapping]) -> None:
    cursor = db.cursor()
    if len(db_data) == 0:
        return
    cursor.execute(DB_COMMANDS["new audio dir"], (path_hash(audio_dir),))
    audio_dir_id = cursor.lastrowid
    for song in db_data:
        cursor.execute(
            DB_COMMANDS["new song"],
            (
                audio_dir_id,
                song["path"],
                song["codec"],
                song["filesize"],
                song["mtime"],
            ),
        )
        song_id = cursor.lastrowid
        for tag, value in song.items():
            if tag in ["path", "codec", "filesize", "mtime"]:
                continue
            cursor.execute(DB_COMMANDS["new tag"], (song_id, tag, value[0]))
    db.commit()


def get_song_tags(path: str) -> dict:
    db = sqlite3.connect(config.database_file)
    cursor = db.cursor()
    tags = {}
    query = cursor.execute(DB_COMMANDS["get song tags"], (path,))
    for field, value in query.fetchall():
        tags[field] = value
    return tags


def update_database() -> None:
    db = sqlite3.connect(config.database_file)
    db.cursor().executescript(DB_LAYOUT)
    for audio_dir in config.audio:
        data = get_metadata(audio_dir)
        save_metadata(db, audio_dir, data)
    db.close()


def path_hash(path: str) -> str:
    """Return the first 10 digits of the sha256 hash of the utf8-encoded path string."""
    # *One* digit would probably be enough, but let's be generous :)
    return sha256(path.encode()).hexdigest()[:10]
