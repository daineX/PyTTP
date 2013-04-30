class Settings(object):

    def __init__(self, module='settings'):
        self.module = __import__(module)
        type(self).inst = self

    def __getattr__(self, name):
        return getattr(self.module, name)

load = Settings

def get_settings():
    return Settings.inst
