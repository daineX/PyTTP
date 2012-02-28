import os
import time
from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3

import pyttp.database
from pyttp.database import (
    hasField,
    DataBaseObj,
    )


class AudioFile(DataBaseObj):

    hasField(unicode, "title")
    hasField(unicode, "artist")
    hasField(unicode, "path")
    hasField(float,   "modtime")


def fetch_metadata(top):

    for dirpath, dirnames, filenames in os.walk(top):
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)

            if filename.lower().endswith(".mp3"):
                info = EasyID3(abs_path)
            else:
                info = MutagenFile(abs_path)
            if info is None:
                continue

            title = ''.join(info.get('title', '')).encode("utf-8")
            artist = ''.join(info.get('artist', '')).encode("utf-8")

            try:
                unicode_abs_path = unicode(abs_path.decode("utf-8"))
                audio_file = AudioFile.select_cond("path = ?", (unicode_abs_path,)).next()
                if os.stat(abs_path).st_mtime > audio_file.modtime:
                    audio_file.title = title
                    audio_file.artist = artist
                    audio_file.path = abs_path
                    audio_file.modtime = time.time()
                    print "Updated %s" % abs_path
            except StopIteration:
                audio_file = AudioFile.new(title=title, artist=artist, path=abs_path, modtime=time.time())
                print "Added %s to database" % abs_path

if __name__ == "__main__":
    import sys, sqlite3
    conn = sqlite3.connect("audio_metadata.sql")
    pyttp.database.globalConnObj = conn
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    AudioFile.create()

    fetch_metadata(sys.argv[1])
    conn.close()
