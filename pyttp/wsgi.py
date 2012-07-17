# -*- coding: utf-8 -*-

import os
import socket
import sys
from core import *
import network
import types
import ssl

class DummyLogger(object):

    def log(self, severity, message):
        if __debug__:
            print "%s: %s" % (severity, message)


class SocketExhausted(Exception):
    pass

class DefaultHandler(object):


    def __init__(self, *args):
        pass

    def readRequest(self, conn, addr):
        request = ''
        last4 = ''
        verb = conn.recv(4)
        request += verb
        ready = True
        if verb == "POST":
            while True:
                try:
                    data = conn.recv(1)
                except:
                    ready = False
                    break
                if len(last4) == 4:
                    last4 = last4[1:]
                last4 += data
                request += data
                if not data:
                    raise SocketExhausted
                if last4 == '\r\n\r\n':
                    break
        else:
            while True:
                try:
                    data = conn.recv(1024)
                except:
                    break
                request += data
                if not data:
                    raise SocketExhausted
                if data.endswith('\r\n\r\n'):
                    break
        return ready, RequestParser().parse(request)


    def buildEchoResponse(self, req, payload):
        status = Status("HTTP/1.1", "200", "OK")
        headers = []
        headers.append(Header("Server", "PyTTP/0.0.1 (Unix) (Sidux/Linux)"))
        headers.append(Header("Connection", "close"))
        import datetime
        headers.append(Header("Date", datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UTC")))

        payload = str(req) + payload

        resp = Response(status, headers, payload)
        return resp


    def __call__(self, conn, addr):
        req, payload = self.readRequest(conn, addr)
        resp = self.buildEchoResponse(req, payload)
        conn.send(str(resp))
        conn.close()



class SocketFileWrapper(object):
    """
    Wrap file around socket object.
    Useful for non-blocking sockets because operations
    like readline() forget incomplete lines when the
    socket is not ready to be read.
    """

    def __init__(self, sock):
        self.sock = sock
        self.buf = ""


    def read(self, n):
        while len(self.buf) < n:
            s = self.sock.recv(1024)
            self.buf += s
            if s == '':
                break
        if len(self.buf) < n:
            rBuf = self.buf
            self.buf = ''
            return rBuf
        rBuf = self.buf[:n]
        self.buf = self.buf[n:]
        return rBuf


    def readline(self, max_char=None):
        while not '\n' in self.buf:
            s = self.sock.recv(1024)
            self.buf += s
            if s == '':
                break
            if len(self.buf) >= max_char:
                rBuf = self.buf[:max_char]
                self.buf = self.buf[max_char:]
                return rBuf
        delim = self.buf.find('\n')+1
        if delim < 0:
            rBuf = self.buf
            self.buf = ''
            return rBuf
        rBuf = self.buf[:delim]
        self.buf = self.buf[delim:]
        return rBuf


    def readlines(self):
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines


    def __getattr__(self, value):
        fObj = self.sock.makefile()
        return getattr(fObj, value)

    def write(self, msg):
        self.sock.send(msg)


class WSGIHandler(DefaultHandler):

    """
    HTTP/1.1-compliant WSGI Handler
    Implements the minimum requirement for environment data.
    Supports chunked transfer encoding if WSGI application returns
    a generator. Otherwise all data is sent in one go.
    The connection is kept alive if no POST request is sent and the
    client requests such a connection.
    A hard-coded timeout of 5 secs is used for the socket connection.
    """

    def __init__(self, app, port, debug=None, logger=DummyLogger()):
        self.app = app
        self.port = port
        self.status = None
        self.headers = None
        self.logger = logger
        self.debug = debug
        self.prePayload = ""
        self.ready = True
        self.exc_info = None
        self.waitForResponse = True
        self.firstChunk = ""

    def start_response(self, status, headers, exc_info=None):
        """start_response callback as defined by WSGI (PEP 333)"""
        self.logger.log("INFO", "start_response called; status: %s, headers: %s" %
            (status, headers))
        self.status = status
        self.headers = headers
        if exc_info:
            self.exc_info = exc_info
        return self.write

    def write(self, msg):
        self.prePayload += msg


    def _chunkify(self, chunk):
        """Calculates chunk size and returns ready-to-send chunk.
        Arguments:
        chunk -- chunked data to chunkify;
        """
        try:
            chunk = chunk.encode("utf-8")
        except:
            pass
        chunkLength = len(chunk)
        chunkSize = hex(chunkLength)[2:]
        return "%s\r\n%s\r\n" % (chunkSize, chunk)


    def __call__(self, conn, addr):
        keepAliveCount = 0
        socketFileHandle = None
        while self.ready:
            try:
                #timeout of 5 secs
                conn.settimeout(5.0)
                headers = []
                #parse request
                self.ready, (req, reqBody) = self.readRequest(conn, addr)
                environ = {}
                for header in req.headers:
                    environ['HTTP_' + header.name.upper().replace("-", "_")] = header.value
                # setup general environment
                environ['REQUEST_METHOD'] = req.type.verb
                environ['SCRIPT_NAME'] = ''
                try:
                    path, query = req.type.resource.split('?')
                except:
                    path = req.type.resource
                    query = ''

                self.logger.log("INFO", "%s:%s requesting \"%s\"" % (addr[0], addr[1], req.type.resource))
                self.logger.log("INFO", "Headers: \n%s" % req.headers)
                environ['PATH_INFO'] = path
                environ['QUERY_STRING'] = query
                if 'HTTP_CONTENT_TYPE' in environ:
                    environ['CONTENT_TYPE'] = environ['HTTP_CONTENT_TYPE']
                if 'HTTP_CONTENT_LENGTH' in environ:
                    environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
                connectionSetting = environ.get("HTTP_CONNECTION", "keep-alive").lower()
                if connectionSetting != "keep-alive":
                    self.ready = False
                if req.type.verb == "POST":
                    self.ready = False
                    connectionSetting = "close"
                environ['SERVER_PORT'] = self.port
                if "HTTP_HOST" in environ:
                    environ['SERVER_NAME'] = environ['HTTP_HOST']
                else:
                    environ['SERVER_NAME'] = 'localhost'

                environ['SERVER_PROTOCOL'] = 'HTTP/' + req.type.version

                #setup special wsgi environment
                environ['wsgi.version'] = (1, 0)
                environ['wsgi.url_scheme'] = "http"
                if req.type.verb == "POST" and not socketFileHandle:
                    socketFileHandle = SocketFileWrapper(conn)
                    environ['wsgi.input'] = socketFileHandle
                environ['wsgi.errors'] = self.logger
                environ['wsgi.run_once'] = False
                environ['wsgi.multithread'] = True
                environ['wsgi.multiprocess'] = True

                payload = self.app(environ, self.start_response)
                if hasattr(payload, "__iter__"):
                    payload = iter(payload)
                    #payload is a generator, use chunked transfer encoding
                    chunkedEncoding = True
                    #get first chunk so that start_response will be called now
                    try:
                        self.firstChunk = payload.next()
                    except StopIteration:
                        self.firstChunk = ""
                else:
                    chunkedEncoding = False

                headers.append(Header("Server", "PyTTP/0.0.1"))
                headers.append(Header("Connection", connectionSetting))
                if chunkedEncoding:
                    headers.append(Header("Transfer-Encoding", "chunked"))
                try:
                    #add application supplied headers
                    for name, value in self.headers:
                        headers.append(Header(name, value))
                except:
                    pass

                try:
                    statusCode = int(self.status[:3])
                    statusString = self.status[3:]
                except Exception, e:
                    statusCode = '200'
                    statusString = 'OK'
                status = Status("HTTP/1.1", statusCode, statusString)

                #send headers
                resp = Response(status, headers, self.prePayload)
                conn.sendall(str(resp))

                if chunkedEncoding:
                    self.logger.log("INFO","Using chunked transfer encoding")
                    conn.sendall(self._chunkify(self.firstChunk))
                    for p in payload:
                        if p == "": continue
                        chunk = self._chunkify(p)
                        conn.sendall(chunk)
                    #No payload indicates end of transfer
                    conn.sendall(self._chunkify(""))
                else:
                    conn.sendall(str(payload))

                self.logger.log("INFO", "End of response")

                if self.exc_info:
                    type, value, traceback = self.exc_info
                    raise value

            except (socket.timeout, ssl.SSLError, SocketExhausted):
                try:
                    conn.close()
                    environ['wsgi.input'].close()
                except:
                    pass
                break

            except Exception, e:
                import traceback
                formatted_exception = ''.join(traceback.format_exception(*sys.exc_info()))
                if self.debug:
                    print "[DEBUG]:", formatted_exception
                if self.logger:
                    self.logger.log("EXC", formatted_exception)
                else:
                    traceback.print_exc(file=sys.stdout)

                self.exc_info = None
                resp = Response(Status("HTTP/1.1", "500", "Internal Error"), headers, formatted_exception)
                try:
                    conn.sendall(str(resp))
                    conn.close()
                    environ['wsgi.input'].close()
                except:
                    pass
                break


            keepAliveCount += 1
            self.status = None
            self.headers = None
            self.prePayload = ""
            self.firstChunk = ""
            chunkedEncoding = False

        try:
            environ['wsgi.input'].close()
            conn.close()
        except:
            pass



class WSGIHandlerDispatcher(object):

    def __init__(self, app, port, debug, logger):
        self.app = app
        self.port = port
        self.debug = debug
        self.logger = logger


    def __call__(self, conn, addr):
        handler = WSGIHandler(self.app, self.port, self.debug, self.logger)
        return handler(conn, addr)


class WSGIListener(network.ThreadedSocketListener):

    def __init__(self, app, port, timeout = None, nThreads = None, logger=DummyLogger(), debug=None):
        self.handler = WSGIHandlerDispatcher(app, port, debug, logger)
        network.ThreadedSocketListener.__init__(self, port, self.handler, timeout, nThreads)


class WSGISSLListener(network.ThreadedSSLListener):

    def __init__(self, certFile, keyFile, sslVersion, app, port, timeout = None, nThreads = None, logger=DummyLogger(), debug=None):
        self.handler = WSGIHandlerDispatcher(app, port, debug, logger)
        network.ThreadedSSLListener.__init__(self, certFile, keyFile, sslVersion, port, self.handler, timeout, nThreads)

