# -*- coding: utf-8 -*-


def application(environ, start_response):
    status = '200 OK'
    output = 'Pong!'
 
    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)
    return [output]



import network, wsgi, sys

port = int(sys.argv[1])

app = wsgi.AppHandler(application, port, logger=None)
http = network.ThreadedSocketListener(handler = app, port = port, nThreads = 100)
http.serve()
