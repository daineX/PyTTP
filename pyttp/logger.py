# -*- coding: utf-8 -*-
import os
import datetime
import sys

class FileLogger(object):

    def __init__(self, filename):
        self.filename = filename
        try:
            self.filehandle = open(os.path.expanduser(self.filename), "aw")
        except:
            print "Failed to open log file \"%s\"!" % self.filename
            print "Logging to stdout"
            self.filehandle = sys.stdout

    def write(self, msg):
        self.filehandle.write("[UNKNOWN][%s]: %s\n" % (datetime.datetime.now(), msg))
        self.filehandle.flush()

    def log(self, severity, msg):
        self.filehandle.write("[%s][%s]: %s\n" % (datetime.datetime.now(), severity, msg))
        self.filehandle.flush()