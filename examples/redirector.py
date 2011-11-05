# -*- coding: utf-8 -*-

import os
import re

class RedirectorApp(object):

    def __init__(self, mapping):
        self.mapping = []
        for entry in mapping:
            if len(entry) == 3:
                expr, app, split = entry
            else:
                expr, app = entry
                split = 0
            self.mapping.append((expr, app, split))

    def getMapping(self, path):
        for expression, app, split in self.mapping:
            if re.match(expression, path):
                return expression, app, split
        return None, None
        
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        expr, app, split = self.getMapping(path)
        if expr:
            print 'Path "%s" matched "%s" -> calling %s' % (path, expr,  repr(app))
            if split:
                print path
                environ['PATH_INFO'] = '/'+'/'.join(path.split('/')[split+1:])
                print environ['PATH_INFO']
            return app(environ, start_response)
        else:
            status = "401 Access denied"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return ['401']

if __name__ == "__main__":
    

    def theVideo(environ, start_response):
        status = "200 OK"
        headers = [('Content-type', 'text/html')]
        start_response(status, headers)
        src = """
                <html><title>Redirector-Test</title><body>
                <object classid="CLSID:D27CDB6E-AE6D-11cf-96B8-444553540000" width="600" height="400"
                codebase="http://active.macromedia.com/flash2/cabs/swflash.cab#version=4,0,0,0">
                <param name="movie" value="nibbles.swf">
                <param name="quality" value="high">
                <param name="scale" value="exactfit">
                <param name="menu" value="true">
                <param name="bgcolor" value="#000040">
                <embed src="data/ae1ab064ed4e18ef57bd5b19cf4c3ab7.swf" quality="high" scale="exactfit" menu="false"
                    bgcolor="#000000" width="600" height="400" swLiveConnect="false"
                    type="application/x-shockwave-flash"
                    pluginspage="http://www.macromedia.com/shockwave/download/download.cgi?P1_Prod_Version=ShockwaveFlash">
                </embed>
                </object>
        """
        for i in range(9):
             src += '<img src="data/Fotos/Batch1/dsc_000%s.jpg"><br/>\n' % (i+1)
        src += "<body><html>"
        return [src]
        
    def notFound(environ, start_response):
        status = "404 Not found"
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        yield ''

    import pyttp.network, pyttp.wsgi, fileserve, sys
    port = int(sys.argv[1])
      
    documentRoot = os.path.expanduser("~/Bilder")
    fileserve = fileserve.FileServe(documentRoot)
    redirect = RedirectorApp([('/data/.*\.swf', fileserve, 1), ('/.+', notFound), ('/', theVideo)])
    app = pyttp.wsgi.WSGIHandler (redirect, port)
    
#    http = network.ParallelSocketListener(handler = app, port = port, nProcesses=10)
    http = pyttp.network.ThreadedSocketListener(port = port, handler = app, nThreads=40)
#    http = network.HTTPListener(handler = app, port = port)
    http.serve()