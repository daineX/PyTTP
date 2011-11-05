# -*- coding: utf-8 -*-


def parse_query_string(query_string):
    entries = [entry.split("=") for entry in query_string.split("&")]
    dictionary = dict()
    for pair in entries:
        if len(pair) == 2:
            entry, value = pair
            if entry in dictionary:
                dictionary[entry].append(value)
            else:
                dictionary[entry] = [value]
        else:
            if entry not in dictionary:
                dictionary[entry] = ""
    return dictionary
    
    
def parseURLEncoded(environ):
    
    import urlparse
    return urlparse.parse_qs(environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"])))
    
class MultipartException(Exception):
    pass
    
def parseMultipartHeader(environ):
    
    contentType = environ['CONTENT_TYPE']
    try:
        ctype, boundary = contentType.split(";")
    except:
        raise MultipartException("Expected boundary")
    if not ctype.startswith("multipart"):
        raise MultipartException("Invalid Content-Type")
    try:
        boundary = boundary.split('=')[1].strip('"')
    except:
        raise MultipartException("Boundary definition malformed")
    
    return ctype, boundary


def jumpToNextMultipartBoundary(environ, boundary):
    fileHandle = environ["wsgi.input"]
    read = 0
    atEnd = False
    while True:
        data = fileHandle.readline()
        read += len(data)
        if data == "--%s\r\n" % boundary:
            break
        if data == "--%s\r\n--" % boundary:
            atEnd = True
            break
    environ['HTTP_CONTENT_LENGTH'] = str(int(environ['HTTP_CONTENT_LENGTH']) - read)
    environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
    return atEnd

def parseMultipartInfo(environ):
    fileHandle = environ["wsgi.input"]
    last4 = ''
    request = ''
    read = 0
    while True:
        data = fileHandle.read(1)
        if len(last4) == 4:
            last4 = last4[1:]
        last4 += data
        request += data
        if not data:
            break
        read += 1
        if last4 == "\r\n\r\n":
            break
    
    partInfo = request.split('\r\n')
    
    
    environ['HTTP_CONTENT_LENGTH'] = str(int(environ['HTTP_CONTENT_LENGTH']) - read)
    environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
    
    partInfoMap = {}
    for infoName, infoValue in [(x.strip() for x in part.split(":")) for part in partInfo if part]:
        infoValues = infoValue.split(";")
        attrs = {}
        for value in infoValues:
            try:
                attr, attrV = value.split("=")
                attrs[attr.strip()] = attrV.strip('"')
            except:
                baseValue = value
        partInfoMap[infoName] = (baseValue, attrs)

    return partInfoMap
    
    
def safeReadline(fileHandle):
    import select, os
    data = ""
    p = select.poll()
    p.register(fileHandle)
    fno = fileHandle.fileno()
    while True:
       p.poll()
       ch = os.read(fno, 1)
       data += ch
       if ch == "\n":
           break
    return data
    
def readUntilNextMultipartBoundary(environ, boundary):
    fileHandle = environ["wsgi.input"]
    read = 0
    atEnd = False
    data = ""
    while True:
        try:
#            readData = safeReadline(fileHandle)
            readData = fileHandle.readline()
        except Exception, e:
            print e
#            atEnd = True
#            break
            break
#            continue
        if readData == "--%s\r\n" % boundary:
            break
        if readData == "--%s--\r\n" % boundary or readData == '':
            atEnd = True
            break
        data += readData
    read = len(data)
    data = data[:-2]
    environ['HTTP_CONTENT_LENGTH'] = str(int(environ['HTTP_CONTENT_LENGTH']) - read)
    environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
    return atEnd, data

def parseBytesRangeValue(bytesRange):
    if not bytesRange.startswith("bytes="):
        raise Exception("Invalid BytesRange: Expected bytes=")
    bytesRange = bytesRange[6:]
    bytesRanges = bytesRange.split(",")
    rBytes = []
    for bytesRange in bytesRanges:
        lower, upper = bytesRange.split("-")
        rBytes.append((lower, upper))
    return rBytes
        