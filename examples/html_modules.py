
from pyttp.html import *
import urllib
import os

class HTMLModule(object):

    def __init__(self):
        pass

    def html(self, environ):
        return blank()

    def css(self, environ):
        return ""
        
        


class Aggregator(HTMLModule):
    
    def __init__(self, *modules):
        self.modules = modules
    
    
    def registerModule(self, module):
        self.modules.append(module)
    
    def css(self, environ):
        return '\n'.join (module.css(environ) for module in self.modules)
        
    def html(self, environ):
        return blank(module.html(environ) for module in self.modules)
        
        

class ModuleApp(object):
    
     
    
    def __init__(self):
        self.modules = {}
        
    def pathToCssLink(self, path):
        return link(rel="stylesheet", type="text/css", href=os.path.join(path,"style.css"))

    def header(self, path):
        return head(self.pathToCssLink(path))
    
    def __call__(self, environ, start_response):
        path = urllib.unquote(environ["PATH_INFO"])
        dirname, basename = os.path.split(path)
        if dirname in self.modules:
            module = self.modules[dirname]
            if basename == "style.css":
                status = "200 OK"
                headers = [("Content-Type", "text/css")]
                start_response(status, headers)
                yield module.css(environ)  
            else:
                status = "200 OK"
                headers = [("Content-Type", "text/xml; charset=UTF-8")]
                yield str(XHTML10DTD())
                src = \
                html(
                    self.header(dirname),
                    body(
                        module.html(environ)
                    )
                )
                yield str(src)

        else:
            status = "404 Not found"
            headers = [("Content-Type", "text/plain")]
            start_response(status, headers)
            yield "Not found"
        
        
        
if __name__ == "__main__":
    
    
    class HelloWorldBox(HTMLModule):
        
        def html(self, env):
            src = \
            div(id="hwbox")(
                "Hello World")
            return src
        
        
        def css(self, env):
            return """
            #hwbox {
                text-align: right;
            }"""
            
    class H1(HTMLModule):
        
        def __init__(self, msg):
            self.msg = msg
            
        def html(self, env):
            return h1(id="h1box")(self.msg)
            
        def css(self, env):
            return """
            #h1box {
                font-size: 30px
            }"""
            

    hw = HelloWorldBox()
    h1box= H1("This is a test!")
    ag = Aggregator(h1box, hw)
    
    print ag.css({})
    print str(ag.html({}))
    
    
    def dummy_response(status, headers):
        pass
    
    class TestModuleApp(ModuleApp):
        
        def __init__(self):
            self.modules = {
                        '/': ag,
                        '/h1': h1}
                        
                        
    t1 = TestModuleApp()
    
    print ''.join(t1({"PATH_INFO": '/'}, dummy_response))
    print ''.join(t1({"PATH_INFO": '/style.css'}, dummy_response))
    
    
            