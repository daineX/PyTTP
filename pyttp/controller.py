import cgi
import string
import urlparse

from pyttp.template import Template

class Http404(Exception):
    pass

class ValidationException(Exception):
    pass

def expect_list(*list_params):
    def decorator(func):
        func.expect_list = list_params
        return func
    return decorator

def expose(func):
    func.exposed = True
    return func


def validate(**validator_mapping):
    def decorator(func):
        def inner(*args, **kwargs):
            for kwarg in kwargs:
                if kwarg in validator_mapping:
                    new_val = validator_mapping[kwarg](kwargs[kwarg])
                    if new_val is not None:
                            kwargs[kwarg] = new_val
            return func(*args, **kwargs)
        return inner
    return decorator


def inject_header(header):
    def decorator(func):
        def inner(*args, **kwargs):
            response = func(*args, **kwargs)
            response.headers.append(header)
            return response
        return inner
    return decorator


class ControllerResponse(object):
    """
    Response to be returned by actions as expected by the ControllerWSGIApp.
    """

    def __init__(self, payload, status="200 OK", headers=None):
        self.payload = payload
        self.status = status
        if headers:
            self.headers = headers
        else:
            self.headers = []


    def get_response(self):
        return self.status, self.headers


    def get_payload(self):
        return self.payload


class EmptyResponse(ControllerResponse):

    def __init__(self, status="200 OK", headers=None):
        super(EmptyResponse, self).__init__('', status, headers)


class RedirectionResponse(EmptyResponse):
    """
    Special redirection response.
    """

    def __init__(self, location):
        super(RedirectionResponse, self).__init__("302 Redirect", [('Location', location)])


class Redirection(Exception):
    """
    Raise this exception to trigger a redirect.
    The actual RedirectionResponse will be build in the WSGI app.
    """

    def __init__(self, location):
        self.location = location


def redirect_to(location):
    """
    Short-hand for triggering a redirection.
    """
    raise Redirection(location)


class TemplateResponse(ControllerResponse):

    def __init__(self, template, context=None, status="200 OK", headers=None, search_path=None):
        if not context:
            context = {}
        payload = ''.join(Template.load_and_render(template, context, search_path=search_path))
        super(TemplateResponse, self).__init__(payload, status, headers)


class Controller(object):

    """
    A controller parses URLs and treats the parts of the URL as arguments
    and keyword arguments for its exposed methods. Parts of the path will
    used as arguments while the query string will be used as keyword arguments.

    Other controller instances can be set as class attributes to trigger
    cascades.

    The exposed methods ("Actions") will have at least on parameter which
    is the WSGI environment (called `request` in the examples).

    Example:

        class SubController(Controller):
            @expose
            def action(self, request, id, param=None):
                return ControllerResponse("You called me with %s %s" % (id, param))

        class RootController(Controller):
            sub = SubController()

            @expose
            def index(self, request):
                return ControllerResponse("This is the index page.")

        Opening "/" on the ControllerWSGIApp will call RootController.index
        Opening "/sub/" will try to call SubController.index and fail and
            therefore show a 404 page.
        Opening "/sub/action/5/" will call SubController.action with parameters
            id = 5 and param = None.
        Opening "/sub/action/5/?param=foo" will call SubController.action with parameters
            id = 5 and param = foo.

    To expose a method, use the `expose` decorator.
    """


    def _dispatch(self, request, path, query_string):
        """
        Dispatches the request on a certain path to either a sub-controller
        or a method.
        """

        # get actio name
        path = path.strip("/")
        path_parts = path.split("/")
        action = path_parts[0]

        # the "index" method takes care of index pages
        if action == '':
            action = 'index'

        try:
            lookup = getattr(self, action)
        except AttributeError:
            raise Http404


        if isinstance(lookup, Controller):
            # dispatch to sub-controller
            path = path[len(action):]
            return lookup._dispatch(request, path, query_string)


        def query_values(meth, parsed_query_item):
            """
            By default only the first value of queries is given to the
            action. If the query key is in the "expect_list" a list is
            given instead. Query keys without value are treated as boolean.
            """
            key, value = parsed_query_item
            if hasattr(meth, "expect_list") and key in meth.expect_list:
                return key, [x.value for x in value]
            elif value[0]:
                return key, value[0]
            else:
                return key, True

        def process_field_storage(meth, field_storage):
            kwargs = {}
            for key in field_storage:
                mf = field_storage[key]
                if hasattr(meth, "expect_list") and key in meth.expect_list:
                    if isinstance(mf, list):
                        value = []
                        for m in mf:
                            val = m.value
                            if isinstance(val, str):
                                val = val.decode("utf-8")
                            value.append(val)
                    else:
                        value = [mf.value]
                    kwargs[key] = value
                else:
                    if isinstance(mf, list):
                        value = mf[0].value
                    else:
                        if mf.filename: # return files as-is
                            value = mf
                        else:
                            value = mf.value
                            if value == '':
                                value = True
                            if isinstance(value, str):
                                try:
                                    value = value.decode("utf-8")
                                except UnicodeDecodeError:
                                    pass
                    kwargs[key] = value
            return kwargs

        # delegate to method
        if callable(lookup) and hasattr(lookup, "exposed") and lookup.exposed:
            import cgi
            if request["REQUEST_METHOD"] == 'POST':
                fp = request["wsgi.input"]
            else:
                fp = None
            field_storage = cgi.FieldStorage(fp=fp,
                                             environ=request,
                                             keep_blank_values=True)


            args = path_parts[1:]
            kwargs = process_field_storage(lookup, field_storage)
            return lookup(request, *args, **kwargs)

        raise Http404


def defaulthandler404(request):

    path = request["PATH_INFO"]
    query_string = request["QUERY_STRING"]
    if query_string:
        query_string = "?" + query_string

    return ControllerResponse("URL %s%s not found!" % (path, query_string),
                              "404 Not Found",
                              [('Content-Type', 'text/plain')])

class ControllerWSGIApp(object):


    def __init__(self, root, handler404=defaulthandler404):
        self.root = root
        self.handler404 = handler404

    def __call__(self, environ, start_response):
        request = environ
        path = environ["PATH_INFO"]
        query_string = environ["QUERY_STRING"]
        try:
            response = self.root._dispatch(request, path, query_string)
        except Http404:
            response = self.handler404(request)

        except Redirection, redirect:
            response = RedirectionResponse(redirect.location)

        status, headers = response.get_response()
        start_response(status, headers)

        yield response.get_payload()


if __name__ == "__main__":

    import os

    def validate_style(style):
        if any(i not in string.digits for i in style):
            raise ValidationException("style has to be digits only")

    def are_int(the_list):
        try:
            return [int(x) for x in the_list]
        except:
            raise ValidationException("Expected list of integers")

    class SubController(Controller):

        @expose
        @expect_list("we_gunna_have_fun")
        @validate(we_gunna_have_fun=are_int)
        def usage(self, request, we_gunna_have_fun=None):
            if we_gunna_have_fun is None:
                we_gunna_have_fun = []
            assert isinstance(we_gunna_have_fun, list)
            return ControllerResponse(repr(("Use this:  .. ", we_gunna_have_fun)))


    class TestController(Controller):

        sub = SubController()

        @expose
        @validate(style=validate_style)
        def show(self, request, imageid, style=None, parent=None):
            return ControllerResponse(repr((imageid, style, parent)))


        @expose
        def redirected(self, request):
            redirect_to('/show/111/?style=666&parent=foo')

        @expose
        @inject_header(('Content-Type', 'text/plain'))
        def index(self, request, **kwargs):
            return ControllerResponse("<html>This is the index page.<html>")

    
        @expose
        def form(self, request, **kwargs):
            if request["REQUEST_METHOD"] == 'POST':
                return ControllerResponse(repr(kwargs))
            else:
                return TemplateResponse('form.pyml', search_path=os.path.join(os.path.dirname(__file__), "../examples/templates"))


if __name__ == "__main__":
    import network, wsgi, sys
    port = int(sys.argv[1])

    http = wsgi.WSGIListener(ControllerWSGIApp(TestController()), port, nThreads=4)
    http.serve()
