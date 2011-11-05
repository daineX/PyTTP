
import pyttp.database as db
from pyttp.database import hasField
import sqlite3

class DownloadEntry(db.DataBaseObj):

    hasField(str, "url")           #URL to retrieve
    hasField(str, "destination")   #file destination
    hasField(int, "ratelimit")     #rate limit in Bytes
    hasField(int, "active")        #whether download is active at this moment
    hasField(int, "finished")      #whether download is finished
    hasField(str, "error")         #any error which happened while downloading
    


class Defaults(db.DataBaseObj):
    
    hasField(str, "destination")
    hasField(int, "ratelimit")
    
if __name__ == "__main__":
    
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.globalConnObj = conn

    DownloadEntry.create()
    
    dl = DownloadEntry.new(url="http://url.de/file", 
                       destination="/home/user/downloadFolder/file",
                       active=False,
                       finished=False,
                       error="")

    
    for entry in DownloadEntry.select_creation(cond="active=0"):
        print entry
