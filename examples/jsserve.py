from pyttp.controller import (
    Controller,
    ControllerResponse,
    ControllerWSGIApp,
    expose,
    inject_header,
)
from pyttp.js import toJS
from pyttp.template import render_string
from pyttp.wsgi import WSGIListener


pyml = """\
-!!!
%head
  %meta(charset: "UTF-8")
%html
  %body
    %div
      -for idx in groups
        %span.output(data-idx: "= idx")!
        %input.input(type: "number" data-idx: "= idx" value: "0")
        %br
    %script(src: "/jssrc")!
    %script
      js_setup()
"""
markup = render_string(pyml, context=dict(groups=range(10)))


def js_setup():

    def inputChange(elem):
        idx = elem.dataset.idx
        select(".output[data-idx='" + idx + "']").textContent = elem.value
    selectAll(".input").forEach(lambda el: el.on('change', inputChange).trigger('change'))

js = toJS(js_setup)


class JSController(Controller):

    @expose
    @inject_header(("Content-Type", "application/javascript"))
    def jssrc(self, request):
        return ControllerResponse(js)

    @expose
    def index(self, request):
        return ControllerResponse(markup)


if __name__ == "__main__":
    app = ControllerWSGIApp(JSController())
    httpd = WSGIListener(app, 8080, nThreads=4)
    httpd.serve()
