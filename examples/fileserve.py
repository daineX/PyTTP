# -*- coding: utf-8 -*-
import os, mimetypes

class FileServe(object):


    def __init__(self, documentRoot, directoryListing = False):
        self.documentRoot = os.path.normpath(documentRoot)
        self.directoryListing = directoryListing


    def __call__(self, environ, start_response):
        import urllib
        path = urllib.unquote(environ["PATH_INFO"][1:])
        filename = os.path.normpath(os.path.join(self.documentRoot, path))

        filenameValid = True
        if os.path.commonprefix([self.documentRoot, filename]) != self.documentRoot:
            filenameValid = False
        if not os.path.exists(filename):
            filenameValid = False
        if not filenameValid:
            print "Invalid File: %s" % filename
            status = "404 Not found"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            yield "File %s not found" % path

        elif os.path.isdir(filename):
            if not self.directoryListing:
                status = "401 Access denied"
                headers = [('Content-type', 'text/html; charset=UTF-8')]
                start_response(status, headers)
                yield 'Unable to open file %s' % path
            status = "200 OK"
            headers = [('Content-type', 'text/html; charset=UTF-8')]
            start_response(status, headers)
            yield "<html><head><title>%s</title></head><body>" % path
            import glob
            entries = glob.glob("%s/*" % filename)
            yield "<table>"
            parentDir, _ = os.path.split(filename)
            if parentDir == self.documentRoot:
                yield '<tr><td><a href="/">..</a></td><td></td></tr>'
            else:
                yield '<tr><td><a href="%s">..</a></td><td></td></tr>' % parentDir[len(self.documentRoot):]
            for entry in sorted(entries, cmp=lambda x,y: cmp(x.lower(), y.lower())):
                yield '<tr><td><a href="%s">%s</a></td><td>%sKB</td></tr>' % (entry[len(self.documentRoot):], os.path.basename(entry), os.path.getsize(entry) / 1024)
            yield "</body></html>"
            

        else:
            mime, enc = mimetypes.guess_type(filename)

            try:
                with open(filename) as filehandle:
                    status = "200 OK"
                    headers = [('Content-type', mime)]
                    start_response(status, headers)
                    while True:
                        data = filehandle.read(65536)
                        yield data
                        if len(data) < 65536:
                            break
            except Exception, e:
                print e
                status = "401 Access denied"
                headers = [('Content-type', 'text/plain')]
                start_response(status, headers)
                yield 'Unable to open file %s' % path


if __name__ == "__main__":

    import network
    import sys

    port = int(sys.argv[1])
    documentRoot = sys.argv[2]

    web = network.AppHandler(FileServe(documentRoot), port)

    http = network.ParallelSocketListener(port = port, handler = web)
    http.serve()

