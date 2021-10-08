
import mimetypes
import os
import re


"""
Collection of useful WSGI apps.
"""

class Router(object):

    """
    Route request to other WSGI apps based on regex matches.

    Expects a list of mappings on creation.
    Mappings will be tested in the order they were passed to the Router.
    Each mapping is either a two- or three-tuple.
    In case of a 2-tuple the first parameter is the regex and the second
    is the WSGI app to route to in case of a match.
    In case of a 3-tuple the third parameter will specify how many path
    elements will be split from the original path before passing it to the
    app which is routed to.

    Example:
    router = Router([('/static/.+', FileServer(), 1), ('/.*', MyApp())])

    Everything under /static/ will be passed to FileServer, everything else
    to MyApp. When passing to FileServer, the original path will be shortened
    by one element, meaning the /static part of the path will be omitted.
    """

    def __init__(self, mapping):
        self.mapping = []
        for entry in mapping:
            if len(entry) == 3:
                expr, app, split = entry
            elif len(entry) == 2:
                expr, app = entry
                split = 0
            else:
                raise ValueError("Invalid mapping; expecting two-or three-tuple")
            self.mapping.append((expr, app, split))


    def get_mapping(self, path):
        for expression, app, split in self.mapping:
            if re.match(expression, path):
                return expression, app, split
        return None, None


    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        expr, app, split = self.get_mapping(path)
        if expr:
            if split:
                environ['PATH_INFO'] = '/'+'/'.join(path.split('/')[split+1:])
            return app(environ, start_response)
        else:
            status = "401 Access denied"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return ['401']



class FileServer(object):

    """
    Serve files.
    """


    def __init__(self, document_root, directory_listing=True, max_cache_age=3600000):
        """
        directory_listing: Allow directory listing if True.
        """
        self.document_root = os.path.normpath(document_root)
        self.directory_listing = directory_listing
        self.max_cache_age=max_cache_age


    def __call__(self, environ, start_response):
        import urllib
        path = urllib.parse.unquote(environ["PATH_INFO"][1:])
        filename = os.path.normpath(os.path.join(self.document_root, path))

        filename_valid = True
        if os.path.commonprefix([self.document_root, filename]) != self.document_root:
            filename_valid = False
        if not os.path.exists(filename):
            filename_valid = False
        if not filename_valid:
            status = "404 Not found"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            yield "File %s not found" % path

        elif os.path.isdir(filename):
            if not self.directory_listing:
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
            if parentDir == self.document_root:
                yield '<tr><td><a href="/">..</a></td><td></td></tr>'
            else:
                yield '<tr><td><a href="%s">..</a></td><td></td></tr>' % parentDir[len(self.document_root):]
            for entry in sorted(entries, key=lambda x: x.lower()):
                yield '<tr><td><a href="%s">%s</a></td><td>%sKB</td></tr>' % (entry[len(self.document_root):], os.path.basename(entry), os.path.getsize(entry) / 1024)
            yield "</body></html>"


        else:
            mime, enc = mimetypes.guess_type(filename)

            try:
                with open(filename,"rb") as filehandle:
                    status = "200 OK"
                    headers = [('Content-Type', mime),
                               ('Cache-Control', 'public, max-age=%s' % self.max_cache_age)]
                    start_response(status, headers)
                    while True:
                        data = filehandle.read(65536)
                        yield data
                        if len(data) < 65536:
                            break
            except Exception as e:
                status = "401 Access denied"
                headers = [('Content-type', 'text/plain')]
                start_response(status, headers)
                yield 'Unable to open file %s' % path

