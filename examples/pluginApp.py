# -*- coding: utf-8 -*-
import pyttp.wsgi
import pyttp.config
import pyttp.plugin
import pyttp.logger
from pyttp.html import *
import os, glob
import sys
import imp
import re
import urllib
import traceback

class PluginApp(object):


    def __init__(self, configDir = None):
        if configDir is None:
            configDir = os.path.expanduser("~/.pyttp/plugins")
        self.configObj = pyttp.config.Config(os.path.join(configDir, "config"))
        try:
            self.configObj.load()
        except pyttp.config.ConfigException, e:
            print "Error loading config:", e
            print "Assuming empty config"
        try:
            self.enabled = [x.strip() for x in (self.configObj.getValue("enabled")).split(",")]
        except:
            self.enabled = []
        try:
            self.pluginPath = self.configObj.getValue("pluginPath")
        except:
            self.pluginPath = os.path.expanduser("~/.pyttp/plugins")
            
        try:
            self.interfacePath = self.configObj.getValue("interfacePath")
        except:
            self.interfacePath = "/__config"
        
        self._plugins = {}
        self._pluginCfg = {}
        self._paths = {}
        self._splits = {}
        print "Enabled:", self.enabled
        print "PluginPath:", self.pluginPath
        
        self._rescan()

        self._loadPluginConfig()
        
        self.insts = {}
        for name in self._plugins:
            self._buildInst(name)

        print "Plugin Config:", self._pluginCfg
        print "Plugin Paths:", self._paths

    def _buildInst(self, name):
        cls = self._plugins[name]
        if name in self.enabled:
            try:
                inst = cls(*self._pluginCfg[name])
                self.insts[name] = inst 
            except:
                self.enabled = [x for x in self.enabled if x != name]
                tb = traceback.format_exc(sys.exc_info())
                raise Exception("Failed to start service %s:\n%s" % (name, tb))

    def _rescan(self):
        sys.path.insert(0, self.pluginPath)
        try:
            pathnames = glob.glob(os.path.join(self.pluginPath, '[!_]*.py'))
        except OSError: return
        for pathname in pathnames:
            name = os.path.basename(pathname)
            name = name[:name.rfind(".")]
           
            try:
                modinfo = imp.find_module(name)
            except Exception, e: 
                print e
                continue
            try:
                mod = imp.load_module(name, *modinfo)
            except Exception, e:
                    print e
                    try:
                        del sys.modules[name]
                    except Exception, e:
                        print e
                        pass 
                    continue
            self._load(mod)
            
        del sys.path[0:1]


    def _load(self, module):
        try: objs = [getattr(module, attr) for attr in module.__all__]
        except AttributeError:
            objs = [getattr(module, attr) for attr in vars(module)
                    if not attr.startswith("_")]
        objs = filter(lambda x: isinstance(x, type), objs)
        objs = filter(lambda x: issubclass(x, pyttp.plugin.PyTTPPlugin) 
                and x is not pyttp.plugin.PyTTPPlugin, objs)
        for obj in objs:
            try:
                name = obj.__name__
                self._plugins[name] = obj
            except: pass
        
    def _loadPluginConfig(self):
        for name, cls in self._plugins.items():
            cfgs = cls._config()
            args = []
            for cfg in cfgs:
                if isinstance(cfg, pyttp.plugin.PluginParameter):
                    _cfg = cfg
                else:
                    _cfg = pyttp.plugin.StringParameter(cfg, "")
                try:
                    value = self.configObj.getValue("%s_%s" % (name, _cfg.description))
                except:
                    value = _cfg.default
                value = _cfg.fromString(value)
                args.append(value)
            try:
                path = self.configObj.getValue("%s_%s" % (name, "_path"))
            except:
                path = "/"+name
            try:
                split = int(self.configObj.getValue("%s_%s" % (name, "_split")))
            except:
                split = 0
            self._paths[name] = path
            self._pluginCfg[name] = args
            self._splits[name] = split

    def _saveAll(self):
        self.configObj.setValue("enabled", ','.join(self.enabled))
        for name in self._plugins:
            self._savePluginConfig(name)
        self.configObj.dump()

    def _savePluginConfig(self, name):
        cls = self._plugins[name]
        cfgs = cls._config()
        for cfg, arg in zip(cfgs, self._pluginCfg[name]):
            descr = cfg.description
            try:
                self.configObj.setValue("%s_%s" % (name, descr), str(arg))
            except pyttp.config.ConfigException, e:
                print "Error saving plugin config:", e
        try:
            self.configObj.setValue("%s_%s" % (name, "_path"), self._paths[name])
        except pyttp.config.ConfigException, e:
            print "Error saving plugin config:", e
        try:
            self.configObj.setValue("%s_%s" % (name, "_split"), str(self._splits[name]))
        except pyttp.config.ConfigException, e:
            print "Error saving plugin config:", e            
            
                        
    def getMapping(self, path):
        longestMatch = ""
        longestMatchName = ""
        for name, expression in self._paths.items():
            if name not in self.enabled:
                continue
            if re.match(expression, path) or re.match(expression, path+"/"):
                if len(expression) > len(longestMatch):
                    longestMatch = expression
                    longestMatchName = name
        if longestMatch:
            return longestMatch, longestMatchName
        else:
            return None, None
        
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if path == self.interfacePath:
            return self.webInterface(environ, start_response)
        
        expr, name = self.getMapping(path)
        if expr:
            print 'Path "%s" matched "%s" -> calling %s' % (path, expr,  name)
            split = self._splits[name]
            environ['ORIG_PATH_INFO'] = environ['PATH_INFO']
            if split:
                environ['PATH_INFO'] = '/'+'/'.join(path.split('/')[split+1:])
            try:
                return self.insts[name](environ, start_response)
            except:
                return ["Failed to run service %s" % name]
        else:
            status = "401 Access denied"
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return ['401']
            
    def webInterface(self, environ, start_response):
        try:
            status = "200 OK"
            headers = [("Content-Type", "text/html")]
            start_response(status, headers)
            
            inner = blank()
            css = style("""
            table, td {
                vertical-align: top;
            }
            """
            )
            
            src = \
            html(
                head(
                    title("Webinterface"),
                    css
                ),
                body(
                    h1("Webinterface"),
                    inner
                )
            )
            
            import urlparse
            query = urlparse.parse_qs(environ["QUERY_STRING"])


            for name, cls in self._plugins.items():
                disableStr = "disable_%s" % name
                enableStr = "enable_%s" % name
                if disableStr in query:
                    self.enabled = [n for n in self.enabled[:] if n != name]
                if enableStr in query:
                    if name not in self.enabled:
                        self.enabled += [name]
                        self._buildInst(name)
                cfg = cls._config()
                args = self._pluginCfg[name]
                configChanged = False
                for idx, arg in enumerate(args):
                    cfgname = cfg[idx].description
                    opt = "%s_%s" % (name, cfgname)
                    if opt in query:
                        try:
                            value = cfg[idx].fromString(urllib.unquote(query[opt][0]))
                        except: continue
                        if arg != value:
                            self._pluginCfg[name][idx] = value
                            configChanged = True
                            
                if configChanged:
                    self._buildInst(name)
                    
                pathVar = "%s__path" % name
                if pathVar in query:
                    newPath = urllib.unquote(query[pathVar][0])
                    if newPath:
                        self._paths[name] = newPath
                        
                splitVar = "%s__split" % name
                if splitVar in query:
                    newSplit = urllib.unquote(query[splitVar][0])
                    try:
                        newSplit = int(newSplit)
                        self._splits[name] = newSplit
                    except:
                        pass

            if "save" in query:
                print "Saving configuration .. ",
                self._saveAll()
                print "done."
                                

            enableForm = form(action=self.interfacePath)
            pluginList = table()
            pluginList.add(tr(td("Service"), td("Enable/Disable"), td("RequestPath"), td("Split"), td("Config")))
            
            for name, cls in self._plugins.items():
                if name in self.enabled:
                    checkbox = input(type="submit", name="disable_%s" % name, value="Disable")
                else:
                    checkbox = input(type="submit", name="enable_%s" % name, value="Enable")
                
                cfg = cls._config()
                args = self._pluginCfg[name]
                if len(args):
                    argsCont = table()
                    for idx, arg in enumerate(args):
                        cfgname = cfg[idx].description
                        argsCont.add(tr(td(cfgname), td(input(name="%s_%s" % (name, cfgname), type="text", value=str(arg)))))
                else:
                    argsCont = blank()
                pathname = td(input(name="%s__path" % name, type="text", value=self._paths[name]))
                splitVar = td(input(name="%s__split" % name, type="text", value=str(self._splits[name]), size=2))
                pluginList.add(tr(td(name), td(checkbox), pathname, splitVar, td(argsCont)))
            enableForm.add(pluginList, br())
    #        enableForm.add(input(type="submit", value="Refresh"))
            enableForm.add(input(type="submit", name="save", value="Save config"))
            refreshForm = form(action=self.interfacePath)
            refreshForm.add(input(type="submit", value="Refresh"))
            inner.add(enableForm, br(), refreshForm)
            
            return [str(XHTML10DTD()), str(src)]
        except Exception, e:
            status = "500 Internal Error"
            headers = [("Content-Type", "text/plain")]
            start_response(status, headers, sys.exc_info())
#            import traceback
            return ["An Error occured: %s" % traceback.format_exc(sys.exc_info())]
        
        
if __name__ == "__main__":
    
    p = PluginApp(configDir="plugins")
    
    httpd = pyttp.wsgi.WSGIListener(p, 8080, logger=pyttp.logger.FileLogger("~/.pyttp/log"), debug=True)
    httpd.serve()