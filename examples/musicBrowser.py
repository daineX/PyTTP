# -*- coding: utf-8 -*-


import mutagen
from mutagen.easyid3 import EasyID3
import os
import glob
import mimetypes

from pyttp.html import *
import pyttp.logger
import pyttp.wsgi
from pyttp.helpers import parse_query_string



class MusicBrowser(object):
    
    def __init__(self, root):
        self.documentRoot = documentRoot
        
        
    def __call__(self, environ, start_response):
        query = parse_query_string(environ['QUERY_STRING'])

        import urllib
        path = urllib.unquote(environ["PATH_INFO"][1:])
        filename = os.path.normpath(os.path.join(self.documentRoot, path))

        filenameValid = True
        if os.path.commonprefix([self.documentRoot, filename]) != self.documentRoot:
            filenameValid = False
        if not os.path.exists(filename):
            filenameValid = False
        if not filenameValid:
            status = "404 Not found"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            yield 'File '
            yield path
            yield ' not found'
        else:
            if os.path.isdir(filename):
                status = "200 OK"
                headers = [('Content-type', 'text/html; charset=UTF-8')]
                start_response(status, headers)
                
                yield PublicDTD("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")()
                
                entries = glob.glob("%s/*" % filename)
                
                parentDir = os.path.split(filename)[0]
                if (parentDir == self.documentRoot) or os.path.commonprefix([self.documentRoot, parentDir]) == parentDir:
                    back = "/"
                else:
                    back = parentDir[len(self.documentRoot):]
                src = \
                html(
                    head(
                        title("MusicBrowser")
                    ),
                    body(
                        h1(os.path.basename(filename)),
                        a("..", href=back),
                        br(),
                        blank(*(blank(a(os.path.basename(entry), href=entry[len(self.documentRoot):]), br()) for entry in sorted(entries, cmp=lambda x,y: cmp(x.lower(), y.lower()))))
                    )
                )
                
                yield str(src)        
            else:

                if "play" in query:
                    status = "200 OK"
                    mimetype, _ = mimetypes.guess_type(filename)
                    headers = [('Content-type', mimetype)]
                    start_response(status, headers)
                    with open(filename) as f:
                        while True:
                            data = f.read(65536)
                            yield data
                            if len(data) < 65536:
                                break
                            
                    
                else:
                    status = "200 OK"
                    headers = [('Content-type', 'text/html; charset=UTF-8')]
                    start_response(status, headers)
                    yield PublicDTD("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")()

                    try:
                        if filename.lower().endswith(".mp3"):
                            info = EasyID3(filename)
                        else:
                            info = mutagen.File(filename)
                    except:
                        info = {}
                    try:
                        trackTitle = ''.join(info['title']).encode("utf-8")
                    except:
                        trackTitle = ''
                    try:
                        trackArtist = ' '.join(info['artist']).encode("utf-8")
                    except:
                        trackArtist = ''

                    if info:
                        src = \
                        html(xmnls="http://www.w3.org/1999/xhtml")(
                            head(
                                title("%s - %s" % (trackArtist, trackTitle))
                            ),
                            body(
                                table(*(tr(td(key.capitalize()), td(' '.join(info[key]).encode("utf-8"))) for key in info.keys())),
                                a("back", href="/"+os.path.split(path)[0]),
                                br(),
                                audio("Your browser does not support the audio tag!", src="/"+path+"?play", controls="controls", autoplay="autoplay", preload="preload")
                            ),
                        )
                        yield str(src)
                    else:
                        yield "No Info"


            
if __name__ == "__main__":

    import sys
    port = int(sys.argv[1])
    documentRoot = os.path.expanduser(sys.argv[2])
    
    http = pyttp.wsgi.WSGIListener(MusicBrowser(documentRoot), port, logger=pyttp.logger.FileLogger("~/.pyttp/log"), debug=True, nThreads=40)

    http.serve()
    

    #Un-comment for SSL support and comment above WSGIListener code
    #import ssl
    #CERTFILE="PATH TO CERTIFICATE FILE"
    #KEYFILE="PATH TO KEY FILE" # should be password-less
    #SSL_VERSION=ssl.PROTOCOL_SSLv23

    #httpsd = pyttp.wsgi.WSGISSLListener(CERTFILE, KEYFILE, SSL_VERSION, MusicBrowser(documentRoot), port, logger=pyttp.logger.FileLogger("~/.pyttp/log"), debug=True, nThreads=40)

    #httpsd.serve()
