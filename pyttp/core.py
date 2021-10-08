# -*- coding: utf-8 -*-
from __future__ import print_function

class PyTTPException(Exception):
    pass

class RequestParserException(PyTTPException):
    
    def __init__(self, msg, req):
        self.msg = msg
        self.req = req
        
    def __str__(self):
        return "RequestParser: %s %s" % (self.msg, self.req.encode("string_escape"))
        

class Header(object):
    
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def __str__(self):
        return "%s: %s\r\n" % (self.name, self.value)
        
    def __repr__(self):
        return "Header('%s', '%s')" % (self.name, self.value)
        
class Type(object):
    
    allowedVerbs = ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'TRACE', 'OPTIONS', 'CONNECT', 'PATCH']
    safeVerbs = ['HEAD', 'GET', 'OPTIONS', 'TRACE']
    
    def __init__(self, verb, resource, version):
        self.verb = verb.upper()
        if self.verb not in self.allowedVerbs:
            raise Exception("Invalid HTTP verb; got \"%s\"!" % verb)
        if self.verb in self.safeVerbs:
            self.safe = True
        else:
            self.safe = False
        self.resource = resource
        if version == 'HTTP/1.1':
            self.version = "1.1"
        else:
            self.version = "1.0"
        

    def __str__(self):
        return "%s %s HTTP/%s\r\n" % (self.verb, self.resource, self.version)
        
    def __repr__(self):
        return "Type('%s', '%s', 'HTTP/%s')" % (self.verb, self.resource, self.version)
        
        
        
class Request(object):
    
    def __init__(self, type, headers):
        
        self.type = type
        self.headers = headers
        
        
    def __str__(self):
        return "%s%s\r\n" % (self.type, ''.join(str(h) for h in self.headers))


    def __repr__(self):
        return "Request(%s, %s)" % (repr(self.type), repr(self.headers))


class RequestParser(object):
    
    def __init__(self):
        pass
    
    
    def parse(self, requestString):
        the_request = requestString.split(b'\r\n\r\n')
        requestHeaderString = the_request[0]
        try:
            payload = b'\r\n\r\n'.join(the_request[1:])
        except:
            raise RequestParserException("Malformed Request!", requestString)
        try:
            lines = requestHeaderString.split(b'\r\n')
        except AttributeError:
            raise RequestParserException("Expected string!", requestString)
        try:
            typeString = lines[0]
            verb, resource, version = typeString.decode().split(' ')
        except ValueError:
            raise RequestParserException("Malformed type!", requestString)
        type = Type(verb, resource, version)
        
        headers = []
        for headerString in lines[1:-1]:
            try:
                if not headerString:
                    continue
                fields = headerString.decode().split(':')
                name = fields[0]
                value = (':'.join(fields[1:])).strip(' ')
                headers.append(Header(name, value))
            except:
                raise RequestParserException("Malformed header!", requestString)

            
        return Request(type, headers), payload


class Status(object):
    
    def __init__(self, version, code, stringCode):
        
        if version == 'HTTP/1.1':
            self.version = "1.1"
        else:
            self.version = "1.0"
            
        try:
            self.code = int(code)
        except:
            raise PyTTPException("Invalid status code!")
        
        try:
            self.stringCode = str(stringCode)
        except:
            raise PyTTPException("Invalid status code string!")
        
    def __str__(self):
        return "HTTP/%s %s %s\r\n" % (self.version, self.code, self.stringCode)
        
    def __repr__(self):
        return "Status('HTTP/%s', %s, '%s')" % (self.version, self.code, self.stringCode)

        
class Response(object):    
    
    def __init__(self, status, headers, payload):
        
        self.status = status
        self.headers = headers
        self.payload = payload
        
    def __str__(self):
        return "%s%s\r\n%s" % (self.status, ''.join(str(h) for h in self.headers), self.payload)
        
    def __repr__(self):
        return "Response(%s, %s)" % (repr(self.status), repr(self.headers))
        
if __name__ == "__main__":
    
    
    import socket
    
    
    #t = Type("GET", "/", "HTTP/1.1")
    #h = [Header('Host', 'en.wikipedia.org')]
    
    #req = Request(t, h)
  
    #print req   
    
    #reqParse = RequestParser()
    #reqParsed, payload = reqParse.parse(str(req))
    #print reqParsed
    
    #invalidParse = reqParse.parse("GET_ / HTTP/1.1")
    
    s = socket.socket()
    
    import sys
    s.bind(('', int(sys.argv[1])))
    s.listen(1)
    (conn, addr) = s.accept()
    print("Connection from", addr)
    
    request = ''
    while True:
        data = conn.recv(1024)
        print(data)
        request += data
        if not data or data.endswith("\r\n\r\n"): break
    
    reqParsed, payload = RequestParser().parse(request)
    
    print(repr(reqParsed))
    
    payload = "Nichts zu sehen!"
    
    status = Status("HTTP/1.1", "404", "Not Found")
    headers = []
    headers.append(Header("Server", "PyTTP/0.0.1 (Unix) (Sidux/Linux)"))
    headers.append(Header("Connection", "close"))
    headers.append(Header("Content-Length", str(len(payload))))
    import datetime
    headers.append(Header("Date", datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UTC")))
    
    response = Response(status, headers, payload)
    print(response)
   
    
    conn.send(str(response))
    
    conn.close()
    s.close()
    
