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


def js_setup():

    def inputChange(elem):
        select(f".output[data-idx='{elem.dataset.idx}']").textContent = elem.value
    selectAll(".number").forEach(lambda el: el.on('change', inputChange).trigger('change'))

    reset: var = select("#reset")
    @reset.on("click")
    def resetAll():
        def reset(el):
            el.value = 0
            inputChange(el)
        selectAll(".number").forEach(reset)

js = toJS(js_setup)


pyml = """\
-!!!
%head
  %meta(charset: "UTF-8")
%html
  %body
    %div
      -for idx in groups
        %span.output(data-idx: "= idx")!
        %input.number(type: "number" data-idx: "= idx" value: "0")
        %br
    %input#reset(type: "button" value: "Reset")
    %script
      == js
    %script
      js_setup()
"""
markup = render_string(pyml, context=dict(groups=range(10), js=js))



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
