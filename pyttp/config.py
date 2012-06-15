# -*- coding: utf-8 -*-

import os.path

class ConfigException(Exception):
    
    def __init__(self, value):
        self.value = "Config: " + repr(value)
        
    def __str__(self):
        return self.value

class Config(object):
    
    alphanumeric = 'abcdefghijklmnopqrstuvwxyz_'
    
    def __init__(self, filename = '~/.pyttp/config', empty=False):
        
        self.filename = filename
        self.configDict = {}
        if not empty:
            self.load()
        
        
    def itemValidate(self, item):
        for letter in item:
            if letter.lower() not in self.alphanumeric:
                raise ConfigException("Invalid symbol in item: %s" % letter.encode("string_escape"))
            
    def valueValidate(self, value):
        for letter in value:
            if letter == '\n':
                raise ConfigException("Found \\n in value.")
        
        
    def addItem(self, item, value):
        self.itemValidate(item)
        self.valueValidate(value)
        self.configDict[item] = value
        
    def delItem(self, item, value):
        try:
            del self.configDict[item]
        except:
            raise ConfigException("Failed to delete item %s" % item)
            
    def getValue(self, item):
        try:
            return self.configDict[item]
        except:
            raise ConfigException("No such item: %s" % item)
            
    def changeValue(self, item, value):
        self.addItem(item, value)
            
    def setValue(self, item, value):
        self.addItem(item, value)

    def dump(self):
        
        path = os.path.expanduser(self.filename)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception, e:
                raise ConfigException("Failed to create directory %s: %s" % (directory, repr(e)))
        
        try:
            f = open(path, 'w')
        except:
            raise ConfigException("Failed to open file %s" % self.filename)
        
        
        for item, value in self.configDict.items():
            self.itemValidate(item)
            self.valueValidate(item)
            
            f.write("%s = %s\n" % (item, value))
        
        f.flush()
        f.close()
        
    def load(self):
        try:
            with open(os.path.expanduser(self.filename), 'r') as f:
                for lineno, line in enumerate(f.readlines()):
                    if line.startswith("#"):
                        continue
                    try:
                        item, value = line.split("=", 1)
                    except ValueError:
                        raise ConfigException("Expected value in line %s:%s" % (self.filename, lineno + 1))
                    item = item.strip()
                    value = value.strip()
                    
                    try:
                        self.itemValidate(item)
                    except:
                        raise ConfigException("Invalid item in line %s:%s" % (self.filename, lineno + 1))
                        
                    try:
                        self.valueValidate(value)
                    except:
                        raise ConfigException("Invalid value in line %s:%s" % (self.filename, lineno + 1))
                        
                    self.addItem(item, value)
        except IOError:
            raise ConfigException("Failed to access file %s" % self.filename)            
            
try:
    global_config = Config()
except IOError:
    global_config = Config(empty=True)

if __name__ == "__main__":
    
    config = Config(empty=True)
    try:
        config.addItem("Version", "0.0.1")
        config.addItem("Name", "PyTTP=cool")
        config.addItem("()Hello", "World")
    except Exception, e:
        print e
    config.dump()
    
    loadConfig = Config()
    assert loadConfig.getValue("Version") == "0.0.1", loadConfig.getValue("Version")
    assert loadConfig.getValue("Name") == "PyTTP=cool", loadConfig.getValue("Name")
            