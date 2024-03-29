import os

from .settings import get_settings
settings = get_settings()

from .apps import FileServer, Router
from .controller import ControllerWSGIApp
from .wsgi import WSGIListener

def make_controller_root(
        controller,
        static_serve_url='/static/.+',
        static_serve_split=1,
        static_serve_dir=None):
    if static_serve_dir is None:
        static_serve_dir = os.path.join(settings.BASE_DIR, "static")
    fileserve_app = FileServer(static_serve_dir)
    controller_app = ControllerWSGIApp(controller)
    root_app = Router([(static_serve_url, fileserve_app, static_serve_split),
                       ('/.*', controller_app)])
    return root_app

def wrap_root(root_app, port=8080, nThreads=1, **kwargs):
    print(nThreads)
    return WSGIListener(root_app, port, nThreads=nThreads, **kwargs)

def make_controller_listener(controller,
                             port=8080,
                             static_serve_url='/static/.+',
                             static_serve_split=1,
                             static_serve_dir=None,
                             **kwargs
                             ):
    root_app = make_controller_root(
        controller,
        static_serve_url=static_serve_url,
        static_serve_split=static_serve_split,
        static_serve_dir=static_serve_dir,
    )
    return wrap_root(root_app, port, **kwargs)
