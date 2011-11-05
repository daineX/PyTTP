# -*- coding: utf-8 -*-
import urllib
import pyttp.wsgi
from pyttp.html import *
import pyttp.helpers
import pyttp.logger
import fileserve

class PostFileApp(object):

    def __init__(self, documentRoot):
        self.fileServer = fileserve.FileServe(documentRoot, True)
        self.documentRoot = documentRoot

    def __call__(self, environ, start_response):
        path = urllib.unquote(environ["PATH_INFO"][1:])

        if environ["REQUEST_METHOD"] == "POST":
            status = "200 OK"
            headers = [('Content-type', 'text/html; charset=UTF-8')]
            start_response(status, headers)

            ctype, boundary = pyttp.helpers.parseMultipartHeader(environ)
            atEnd = pyttp.helpers.jumpToNextMultipartBoundary(environ, boundary)
            
            inner = blank()
            
            nParts = 0
            while not atEnd:
                partInfo = pyttp.helpers.parseMultipartInfo(environ)
                contentDispo, attrs = partInfo['Content-Disposition']
                filename = attrs['filename'].decode("utf-8")
                atEnd, data = pyttp.helpers.readUntilNextMultipartBoundary(environ, boundary)
                print "Read %s Bytes of data" % len(data)
                
                f = open(os.path.join(self.documentRoot, os.path.basename(filename)), "w")
                f.write(data)
                f.close()
                inner.add("Written %s bytes of data to file %s\n" % (len(data), filename.encode("utf-8")), br())

            yield str(XHTML10DTD())          
            src = \
            html(
                body(
                    inner,
                    a(href="/")("Back"), br(),
                    a(href="/upload")("Upload")
                )
            )
            
            yield str(src)

        elif path == "upload":
            status = "200 OK"
            headers = [('Content-type', 'text/html; charset=UTF-8')]
            start_response(status, headers)
            
            yield str(XHTML10DTD())
            src = \
            html(
                body(
                    form(action="/", method="POST", enctype="multipart/form-data")(
                        input(type="file", size="50", name="Datei"),
                        input(type="submit")
                    )
                )
            )
            
            yield str(src)
        elif path.endswith("favicon.ico"):
            favicon = open(os.path.join(os.path.expanduser("~/.pyttp"), "favicon.ico"))
            status = "200 OK"
            headers = [('Content-type', 'image/x-icon')]
            start_response(status, headers)
            yield ''.join(favicon.readlines())
            favicon.close()
        else:
            yield ''.join(self.fileServer(environ, start_response))

if __name__ == "__main__":
    
    import sys
    import os
    port = int(sys.argv[1])
    
    postFileApp = PostFileApp(os.path.expanduser("~/.pyttp/uploadCache"))
    http = pyttp.wsgi.WSGIListener(postFileApp, port, logger=pyttp.logger.FileLogger("~/.pyttp/log"), debug=True)
    http.serve()