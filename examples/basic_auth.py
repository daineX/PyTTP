# -*- coding: utf-8 -*-
class HTTPBasic(object):

    def __init__(self, app, user_database, realm='Website'):
        self.app = app
        self.user_database = user_database
        self.realm = realm

    def __call__(self, environ, start_response):
        def repl_start_response(status, headers, exc_info=None):
            if status.startswith('401'):
                remove_header(headers, 'WWW-Authenticate')
                headers.append(('WWW-Authenticate', 'Basic realm="%s"' % self.realm))
            return start_response(status, headers)
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)
            if self.user_database.get(username) != password:
                return self.bad_auth(environ, start_response)
            environ['REMOTE_USER'] = username
            del environ['HTTP_AUTHORIZATION']
        return self.app(environ, repl_start_response)

    def bad_auth(self, environ, start_response):
        body = 'Please authenticate'
        headers = [
            ('content-type', 'text/plain'),
            ('content-length', str(len(body))),
            ('WWW-Authenticate', 'Basic realm="%s"' % self.realm)]
        start_response('401 Unauthorized', headers)
        return [body]

def remove_header(headers, name):
    for header in headers:
        if header[0].lower() == name.lower():
            headers.remove(header)
            break


import hashlib

class HTTPMD5(HTTPBasic):
    
        
    def __call__(self, environ, start_response):
        def repl_start_response(status, headers, exc_info=None):
            if status.startswith('401'):
                remove_header(headers, 'WWW-Authenticate')
                headers.append(('WWW-Authenticate', 'Basic realm="%s"' % self.realm))
            return start_response(status, headers)
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)

            md5r = hashlib.md5()
            md5r.update(password)
            
            if self.user_database.get(username) != md5r.hexdigest():
                return self.bad_auth(environ, start_response)
            environ['REMOTE_USER'] = username
            del environ['HTTP_AUTHORIZATION']
        return self.app(environ, repl_start_response) 