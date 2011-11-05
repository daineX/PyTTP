# -*- coding: utf-8 -*-


class PyTTPPlugin(object):

    __name__ = "PyTTPPlugin"

    def __init__(self):
        pass

    def getPrefix(self, environ):
        import urllib
        path = urllib.unquote(environ["PATH_INFO"][1:])
        origPath = urllib.unquote(environ["ORIG_PATH_INFO"][1:])
        if path == '':
            prefix = origPath
        else:
            prefix = "/"+origPath[:-len(path)][:-1]
        return prefix

    def __call__(self, environ, start_response):
        status = "200 OK"
        headers = [("Content-Type", "text/plain")]
        start_response(status, headers)
        yield "Hello World"

    @classmethod
    def _config(self):
        return ()

class PluginParameter(object):
    def __init__(self, description, default=None):
        self.description = description
        self.default = default

    def fromString(self, value):
        return str(value)
        

class BoolParameter(PluginParameter):
    def __init__(self, description, default=False):
        PluginParameter.__init__(self, description, default)
        
    def fromString(self, value):
        value = value.lower()
        if value in ["true", "1", "t", "w"]:
            return True
        else:
            return False
        
class StringParameter(PluginParameter):
    def __init__(self, description, default=""):
        PluginParameter.__init__(self, description, default)
        
class IntegerParameter(PluginParameter):
    def __init__(self, description, default=0):
        PluginParameter.__init__(self, description, default)

    def fromString(self, value):
        return int(value)
                
class FloatParameter(PluginParameter):
    def __init__(self, description, default=0.):
        PluginParameter.__init__(self, description, default)
        
        def fromString(self, value):
            return float(value)
            
            
 
