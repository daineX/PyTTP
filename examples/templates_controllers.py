
import os
from datetime import datetime

from pyttp.controller import (
    expose,
    Controller,
    TemplateResponse,
    ControllerWSGIApp,
)
from pyttp.template import Template
import pyttp.config as pyttp_config


from redirector import RedirectorApp
from fileserve import FileServe

pyttp_config.global_config.setValue("TEMPLATE_SEARCH_PATH", os.path.join(os.path.dirname(__file__), "templates"))

class RootController(Controller):


    @expose
    def index(self, request, **kwargs):

        date = datetime.now().isoformat()
        return TemplateResponse("index.pyml", context=dict(date=date))



if __name__ == "__main__":

    import sys
    from pyttp.wsgi import WSGIListener

    port = int(sys.argv[1])

    fileserve_app = FileServe(os.path.join(os.path.dirname(__file__), "static"))
    controller_app = ControllerWSGIApp(RootController())

    root_app = RedirectorApp([('/static/.+', fileserve_app, 1), ('/.*',  controller_app)])
    httpd = WSGIListener(root_app, port, nThreads=4)
    httpd.serve()

