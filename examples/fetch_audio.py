
import pyttp.database
from pyttp.database import (
    hasField,
    DataBaseObj,
    )

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3

import os



class AudioFile(DataBaseObj):

    hasField(unicode, "title")
    hasField(unicode, "artist")
    hasField(unicode, "path")


def fetch_metadata(top):

    for dirpath, dirnames, filenames in os.walk(top):
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            try:
                if filename.lower().endswith(".mp3"):
                    info = EasyID3(abs_path)
                else:
                    info = MutagenFile(abs_path)
            except:
                continue
            try:
                title = ''.join(info['title']).encode("utf-8")
            except:
                title = ''
            try:
                artist = ' '.join(info['artist']).encode("utf-8")
            except:
                artist = ''

            try:
                audio_file = AudioFile.select_cond("path = ?", (abs_path,))
                audio_file.title = title
                audio_file.artist = artist
                audio_file.path = abs_path
                audio_file.save()
            except:
                audio_file = AudioFile.new(title=title, artist=artist, path=abs_path)

            print filename

if __name__ == "__main__":

    import sqlite3
    conn = sqlite3.connect("audio_metadata.sql")
    pyttp.database.globalConnObj = conn
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    AudioFile.create()

    import sys

    fetch_metadata(sys.argv[1])
    conn.close()
    