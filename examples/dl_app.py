#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import pyttp.database as db
from dl_types import DownloadEntry, Defaults
from pyttp.wsgi import WSGIListener
from pyttp.html import *
import pyttp.helpers as helpers
import multiprocessing
from throttled_download import ThrottledDownloader
import time
import urllib
import urlparse
import argparse
import os

def elapsed_time(seconds, suffixes=['y','w','d','h','m','s'], add_s=False, separator=' '):
    """
    Takes an amount of seconds and turns it into a human-readable amount of time.
    """
    # the formatted time string to be returned
    timevalue = []
    
    # the pieces of time to iterate over (days, hours, minutes, etc)
    # - the first piece in each tuple is the suffix (d, h, w)
    # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
    parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
        (suffixes[1], 60 * 60 * 24 * 7),
        (suffixes[2], 60 * 60 * 24),
        (suffixes[3], 60 * 60),
        (suffixes[4], 60),
        (suffixes[5], 1)]
    
    # for each time piece, grab the value and remaining seconds, and add it to
    # the time string
    for suffix, length in parts:
        value = seconds / length
        if value > 0:
            seconds = seconds % length
            timevalue.append('%s%s' % (str(value),
                        (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
        if seconds < 1:
            break
    
    return separator.join(timevalue)

def bytePrefix(bytes):
    prefixes = ['','K','M','G','T','P','E']
    count = 0
    bytes = float(bytes)
    while bytes > 1023:
        count += 1
        bytes /= 1024
    return "%.2f %sB" % (bytes, prefixes[count])


class DownloadProcess(multiprocessing.Process):

    def __init__(self, infoDict):
        multiprocessing.Process.__init__(self)
        self.normal = False #normal operation started?
        self.infoDict = infoDict
        
    def selectEntry(self):
        #for entry in DownloadEntry:
            #print entry.show()
        if not self.normal:
            for entry in DownloadEntry.select(active=1):
                self.normal = True
                return entry
        self.normal = True
        for entry in DownloadEntry.select_creation(cond="finished=0 AND error=''"):
            return entry
        return None
        
    def hook(self, timeLeft, averageDownloadRate, downloadRate, totalSize, transferedBytes):
        self.infoDict['timeLeft'] = timeLeft
        self.infoDict['averageDownloadRate'] = averageDownloadRate
        self.infoDict['downloadRate'] = downloadRate
        self.infoDict['totalSize'] = totalSize
        self.infoDict['transferedBytes'] = transferedBytes

    def run(self):
        while True:
            entry = self.selectEntry()
            if entry:
                entry.active = 1
                entry.error = ''
                t = ThrottledDownloader(entry.ratelimit)
                t.setDisplayHook(self.hook)
                if os.path.isdir(entry.destination):
                    parsedUrl = urlparse.urlparse(entry.url)
                    path = parsedUrl.path
                    filename = os.path.basename(path)
                    if not filename:
                        filename = "%s.%s" % (parsedUrl.netloc,
                                              parsedUrl.path.replace("/", "."))
                    destination = os.path.join(entry.destination, filename)
                else:
                    destination = entry.destination
                try:
                    t.download(entry.url, destination)
                    entry.finished = 1
                except Exception, e:
                    entry.error = str(e)
                finally:
                    entry.active = 0
            else:
                time.sleep(1)



class DownloadApplication(object):
    
    
    def __init__(self, infoDict):
        self.infoDict = infoDict
    
    
    def downloadList(self):
        
        t = table()
        t.add(tr(td(colspan=6)(b("Entries"))))
        t.add(tr(td("URL"), 
                 td("Destination"),
                 td("Rate Limit"),
                 td("Info"),
                 td("Error")))
        for entry in DownloadEntry:
            if entry.active:
                line = tr(style="background-color:#FFFF00")
            elif entry.error:
                line = tr(style="background-color:#FF0000")
            elif entry.finished:
                line = tr(style="background-color:#00FF00")
            else:
                line = tr()
            line.add(td(entry.url))
            line.add(td(entry.destination))
            if entry.ratelimit:
                line.add(td("%s/s" % bytePrefix(entry.ratelimit)))
            else:
                line.add(td("No Limit"))
            if entry.active:
                timeLeft = self.infoDict['timeLeft']
                avDlRate = self.infoDict['averageDownloadRate']
                dlRate = self.infoDict['downloadRate']
                totalSize = self.infoDict['totalSize']
                transferedBytes = self.infoDict['transferedBytes']
                line.add(td(
                        "TX: %s/%s\n" % (bytePrefix(transferedBytes), bytePrefix(totalSize)), br(),
                        "DL: %s/s, Av: %s/s\n" % (bytePrefix(dlRate), bytePrefix(avDlRate)), br(),
                        "Tleft: %s" % elapsed_time(int(timeLeft))
                        ))
            else:
                line.add(td())
            line.add(td(entry.error))
            if entry.active:
                line.add(td())
            else:
                if entry.error:    
                    retryButton = form(action="/list")(
                    input(type="submit", value="Retry"), 
                    input(type="hidden", name="retryid", value=entry.id))
                    editButton = form(action="/create", method="POST")(
                    input(type="submit", value="Edit"),
                    input(type="hidden", name="url", value=entry.url),
                    input(type="hidden", name="destination", value=entry.destination),
                    input(type="hidden", name="ratelimit", value=entry.ratelimit),
                    input(type="hidden", name="edit", value="doit")
                    )
                else:
                    retryButton = blank()
                    editButton = blank()
                deleteButton = form(action="/list")(
                    input(type="submit", value="Clear"), 
                    input(type="hidden", name="delid", value=entry.id))
                line.add(td(editButton, retryButton, deleteButton))
            t.add(line)
            
        return t
    
    
    def menu(self):
        return blank(
            p(a(href="/list")("List")),
            p(a(href="/create")("Create")),
            p(a(href="/config")("Config")),
        )
    
    
    def creationForm(self, url=None, destination=None, ratelimit=None):

        print url, destination, ratelimit
        defaults = Defaults.select_id(1)
        if not url:
            url = ""
        if not destination:
            destination = defaults.destination
        if not ratelimit:
            ratelimit = defaults.ratelimit
        

        
        f = form(action="/create", method="POST")(
                table(
                    tr(td("URL"), td(input(type="text", name="url", value=url))),
                    tr(td("Destination"), td(input(type="text", name="destination", value=destination))),
                    tr(td("Rate Limit"), td(input(type="text", name="ratelimit", value=ratelimit))),
                    tr(td(input(type="submit")), td())
                )
            )
            
        return f
    
    
    def __call__(self, environ, start_response):
      
        path = urllib.unquote(environ["PATH_INFO"])
        
        innerhtml = blank()
        status = "200 OK"
        headers = headers = [('Content-type', 'text/html; charset=UTF-8')]
        if path == "/" or path == "/list":
            query = helpers.parse_query_string(environ['QUERY_STRING'])
            if "delid" in query:
                try:
                    delid = int(query.get("delid")[0])
                    inst = DownloadEntry.select_id(delid)
                    DownloadEntry.delete(inst)
                except:
                    pass
            if "retryid" in query:
                try:
                    retryid = int(query.get("retryid")[0])
                    inst = DownloadEntry.select_id(retryid)
                    inst.error=''
                except:
                    pass       
            if "clearErrors" in query:
                for entry in DownloadEntry.select_cond(cond="NOT error=''"):
                    DownloadEntry.delete(entry)
            if "clearFinished" in query:
                for entry in DownloadEntry.select(finished=1):
                    DownloadEntry.delete(entry)
                    
           
            errorButton = form(action="/list")(input(type="submit", value="Clear errors"), input(type="hidden", name="clearErrors"))
            finishButton = form(action="/list?clearFinished")(input(type="submit", value="Clear finished downloads"), input(type="hidden", name="clearFinished"))
            
            dlist = self.downloadList()
            dlist.add(tr(td(finishButton), td(colspan="5")(errorButton)))
            innerhtml = dlist

        elif path == "/create":
            if environ["REQUEST_METHOD"] == "POST":
                msg = blank()
                query = helpers.parseURLEncoded(environ)
                print query
                url = query.get("url")
                destination = query.get("destination")
                ratelimit = query.get("ratelimit")
                if not "edit" in query:
                    if not url:
                        msg = b("No URL given!")
                    else:
                        if not destination:
                            msg = b("No destination given!")
                        else:
                            if not ratelimit:
                                ratelimit = 0
                            else:
                                ratelimit = ratelimit[0]
                            url = url[0]
                            destination = destination[0]
                            
                            if not url.startswith("http://"):
                                url = "http://"+url                       
                            dl = DownloadEntry.new(url=url,
                                                    destination=destination,
                                                    ratelimit=ratelimit,
                                                    active=0,
                                                    finished=0,
                                                    error='')
                            msg = "Added Entry"
                    innerhtml = blank(p(msg), self.creationForm())
                else:
                    innerhtml = self.creationForm(url[0], destination[0], ratelimit[0])
            else:
                innerhtml = self.creationForm()
                
        elif path == "/config":
            defaults = Defaults.select_id(1)
            msg = blank()
            if environ["REQUEST_METHOD"] == "POST":
                query = helpers.parseURLEncoded(environ)
                print query

                destination = query.get("destination")
                if not destination:
                    msg = b("Destination not given!")
                else:
                    ratelimit = query.get("ratelimit")
                    if ratelimit is None:
                        msg = b("Rate Limit not given!")
                    else:
                        destination = destination[0]
                        try:
                            ratelimit = int(ratelimit[0])
                            defaults.ratelimit = ratelimit
                        except ValueError:
                            msg = b("Rate Limit must be a number!")
                            ratelimit = defaults.ratelimit
                        if not os.path.isdir(destination):
                            try:
                                os.makedirs(destination)
                                defaults.destination = destination
                            except OSError:
                                msg = b("Invalid destination!")
                        else:
                            defaults.destination = destination
                               
            innerhtml = blank(
            h1("Defaults"), msg,
            form(action="/config", method="POST")(
                table(
                    tr(
                        td("Destination"), td(input(type="text", name="destination", value=defaults.destination))
                    ), 
                    tr(
                        td("Rate Limit (in B)"), td(input(type="text", name="ratelimit", value=defaults.ratelimit))
                    ),
                    tr(
                        td(input(type="submit"))
                    )
                )
            ))
        else:
            status = "404 Not found"
            headers = [('Content-type', 'text/html; charset=UTF-8')]
            innerhtml= b("404 File not found.")
        yield str(XHTML10DTD())
        src = \
            html(
                noEscapeBlank('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'),
                body(
                    table(
                        tr(
                            td(self.menu()), td(innerhtml)
                        )
                    )
                )
            )
        yield str(src)
        
class DatabaseManager(object):
    
    def __init__(self, databaseLocation):
        self.databaseLocation = databaseLocation
        db.globalConnObj = self.connObj()
        DownloadEntry.create()
        Defaults.create()
        try:
            defaults = Defaults.select_id(1)
        except IndexError:
            defaults = Defaults.new(
                    destination=os.path.expanduser("~/Downloads"),
                    ratelimit=0)

        print "Defaults: "
        print "\t Destination: \"%s\" Rate Limit: %s" % (defaults.destination,
                                                         defaults.ratelimit)
        
    def connObj(self):
        conn = sqlite3.connect(self.databaseLocation, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
        


def buildArgumentParser():
    
    parser = argparse.ArgumentParser(description="Web Application for Download Management")
    parser.add_argument("-p", "--port", type=int, help="listen port", default=80)
    parser.add_argument("-d", "--database", default="~/.dldb", help="database file, defaults to ~/.dldb")
    return parser


if __name__ == "__main__":
    
    #conn = sqlite3.connect("/home/inex/dldb", check_same_thread=False)
    #conn.row_factory = sqlite3.Row
    #db.globalConnObj = conn
    
    parser = buildArgumentParser()
    args = parser.parse_args()
    
    DatabaseManager(os.path.expanduser(args.database))
    
    manager = multiprocessing.Manager()
    infoDict = manager.dict()
        
    infoDict['timeLeft'] = 0
    infoDict['downloadRate'] = 0
    infoDict['averageDownloadRate'] = 0
    infoDict['totalSize'] = 0
    infoDict['transferedBytes'] = 0
    
    dl = DownloadProcess(infoDict)
    dl.start()
    print "Background process started ... "
    print "Starting Web Server ... "
    http = WSGIListener(DownloadApplication(infoDict), args.port)
    http.serve()
    dl.join()