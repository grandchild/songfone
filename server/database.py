import os
from glob import glob
import sqlite3
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from config import config
from dirs import list_files_absolute
from conversion import mimes_to_codec

DB_LAYOUT = """
    SELECT * FROM song;
    
    DROP TABLE IF EXISTS song;
    DROP TABLE IF EXISTS tag;

    CREATE TABLE IF NOT EXISTS song (
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
    "new song": "INSERT OR REPLACE INTO song VALUES (?, ?, ?, ?)",
    "new tag": "INSERT OR REPLACE INTO tag VALUES (?, ?, ?)",
    "get song tags": "SELECT field, value FROM tag WHERE song in (SELECT rowid FROM song WHERE path = ?)",
}


def get_metadata(audio_path: str):
    db_data = []
    for path, stat in list_files_absolute(audio_path, extensions=config.extensions):
        if path.endswith("mp3"):
            data = MP3(path, ID3=EasyID3)
        else:
            data = mutagen.File(path)
        if data is not None:
            codec = mimes_to_codec(data.mime)
            data = dict(data)
            data["path"] = path
            data["codec"] = codec
            data["filesize"] = stat.st_size
            data["mtime"] = stat.st_mtime
            db_data.append(data)
    return db_data


def save_metadata(db, db_data: list):
    cursor = db.cursor()
    for song in db_data:
        cursor.execute(
            DB_COMMANDS["new song"],
            (song["path"], song["codec"], song["filesize"], song["mtime"]),
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


def update_database():
    db = sqlite3.connect(config.database_file)
    db.cursor().executescript(DB_LAYOUT)
    data = get_metadata(config.audio)
    save_metadata(db, data)
    db.close()
