
import os
import urllib
import pyttp.wsgi as wsgi
from pyttp.html import *
from pyttp.helpers import parse_query_string, parseURLEncoded

class DataBaseTypesEditor(object):


    def __init__(self, dbTypes, displayValues = None):
        self.dbTypes = dict((dbType.__name__, dbType) for dbType in dbTypes)
        if displayValues:
            self.displayValues = displayValues
        
        
    def menu(self):
        return p(a(href="/"+name)(name) for name in self.dbTypes)


    def edit(self, dbType, environ):
        query = parse_query_string(environ['QUERY_STRING'])
        
        if "id" in query:
            dbid = query["id"][0]
            try:
                inst = dbType.select_id(int(dbid))
            except (IndexError, ValueError):
                return "Invalid ID"
            name = dbType.__name__            
            if environ["REQUEST_METHOD"] == "POST":
                pquery = parseURLEncoded(environ)
                for field in dbType.fieldTypes:
                    if field not in ("cdate", "id"):
                        if field in pquery:
                            value = pquery[field][0]
                            inst.__setattr__(field, value)
                inst.save()
                for ref in dbType.has_many:
                    refName = ref.__name__
                    if refName in pquery:
                        refIDs = [int(_) for _ in pquery[refName]]
                        if ref in dbType.singular_refs:
                            try:
                                refInst = list(inst.getRefs(ref))[0]
                                inst.deleteRef(refInst)
                            except:
                                pass
                            refID = int(pquery[refName][0])
                            if refID:
                                refInst = ref.select_id(refID)
                                inst.setRef(refInst)
                        else:
                            for refInst in inst.getRefs(ref):
                                    inst.deleteRef(refInst)
                            for refID in refIDs:
                                if not refID: continue
                                refInst = ref.select_id(refID)
                                inst.setRef(refInst)
                                print inst.getRefCount(ref)
                        

            
            inst = dbType.select_id(int(dbid))
            
            biggerScript = noEscapeBlank(
            """<script type="text/javascript">
               function bigger(id) {
                   document.getElementById(id).rows *= 2;
               }</script>""")

            f = form(action=os.path.join("/",name, "edit?id=%s" % inst.id), method="POST")
            f.add(biggerScript)
            t = table()
            for field in dbType.fieldTypes:
                if field not in ("cdate", "id"):
                    t.add(tr(td(field), td(textarea(id="text_%s" % field, rows="1", cols="80", name=field)(inst.__getattr__(field))), td(button(type="button", onmousedown="bigger('text_%s')" % field)("+")) ))
            for ref in dbType.has_many:
                refName = ref.__name__
                refIDs = [refInst.id for refInst in inst.getRefs(ref)]
                if ref not in dbType.singular_refs:
                    selection = select(name=refName, multiple="multiple")
                else:
                    selection = select(name=refName)
                selection.add(option(value=0)("--"))
                if ref in self.displayValues:
                    attr = self.displayValues[ref]
                else:
                    attr = "id"
                selection.add(option(value=refInst.id)(refInst.__getattr__(attr)) for refInst in ref if refInst.id not in refIDs)
                selection.add(option(value=refInst.id, selected="selected")(refInst.__getattr__(attr)) for refInst in ref if refInst.id in refIDs)
                t.add(tr(td(refName), td(selection)))
            f.add(t)
            f.add(input(type="submit"))
            return blank(h1(' '.join(("edit", name, unicode(inst.id)))), f)
        return blank()


    def new(self, dbType, environ):
        
        name = dbType.__name__            
        if environ["REQUEST_METHOD"] == "POST":
            pquery = parseURLEncoded(environ)
            inst = dbType.new()
            for field in dbType.fieldTypes:
                if field not in ("cdate", "id"):
                    if field in pquery:
                        value = pquery[field][0]
                        inst.__setattr__(field, value)
            inst.save()
            for ref in dbType.has_many:
                refName = ref.__name__
                if refName in pquery:
                    refIDs = [int(_) for _ in pquery[refName]]
                    print refName, refIDs
                    if ref in dbType.singular_refs:
                        refID = int(pquery[refName][0])
                        if refID:
                            refInst = ref.select_id(refID)
                            inst.setRef(refInst)
                    else:
                        for refID in refIDs:
                            if not refID: continue
                            refInst = ref.select_id(refID)
                            inst.setRef(refInst)
        
        biggerScript = noEscapeBlank(
            """<script type="text/javascript">
               function bigger(id) {
                   document.getElementById(id).rows *= 2;
               }</script>""")
        

        f = form(action=os.path.join("/",name, "new"), method="POST")
        f.add(biggerScript)
        t = table()
        for field in dbType.fieldTypes:
            if field not in ("cdate", "id"):
                t.add(tr(td(field), td(textarea(rows="1", cols="80", name=field, id="text_%s" % field)("")), td(button(type="button", onmousedown="bigger('text_%s')" % field)("+"))))
        for ref in dbType.has_many:
            refName = ref.__name__
            if ref not in dbType.singular_refs:
                selection = select(name=refName, multiple="multiple")
            else:
                selection = select(name=refName)
            selection.add(option(value=0)("--"))
            if ref in self.displayValues:
                attr = self.displayValues[ref]
            else:
                attr = "id"
            selection.add(option(value=refInst.id)(refInst.__getattr__(attr)) for refInst in ref)
            t.add(tr(td(refName), td(selection)))
        f.add(t)
        f.add(input(type="submit"))
        return blank(h1("new " + name), f)
        
    def delete(self, dbType, environ):
        query = parse_query_string(environ['QUERY_STRING'])
        name = dbType.__name__        
        if "id" in query and "doit" in query:
            dbid = query["id"][0]
            try:
                inst = dbType.select_id(int(dbid))
            except (IndexError, ValueError):
                return "Invalid ID"
            deleteRefs = []
            for ref in dbType.has_many:
                refName = ref.__name__
                if refName in query and query[refName][0] == "on":
                    deleteRefs.append(ref)
            dbType.delete(inst, deleteRefs)
            
            return h1("Deleted instance %s of %s" % (dbid, name))
        elif "id" in query:
            dbid = query["id"][0]
            f = form(action=os.path.join("/", name, "delete"))
            f.add(h1("Delete inst %s of %s" % (dbid, name)))
            if dbType.has_many:
                f.add(fieldset(legend("Delete references"),(blank(ref.__name__, input(type="checkbox", name=ref.__name__)) for ref in dbType.has_many)))
            f.add(input(type="hidden", name="id", value=dbid))
            f.add(br())
            f.add(input(type="submit", value="Really delete?"))
            f.add(input(type="hidden", name="doit", value="doit"))
            return f
        return blank()
        
        
    def showEntries(self, dbType):
        name = dbType.__name__

        t = table()
        t.add(tr((td(field) for field in dbType.fieldTypes), td(), td()))
        
        for inst in dbType:
            
            row = tr()
            for field in dbType.fieldTypes:
                value = unicode(inst.__getattr__(field))
                if len(value) > 50:
                    value = value[:47] + "..."
                row .add(td(value))
            row.add(td(a(href=os.path.join("/", name, "edit?id=%s" % inst.id))("Edit")))
            row.add(td(a(href=os.path.join("/", name, "delete?id=%s" % inst.id))("Delete")))
            t.add(row)
            
        return blank(h1(name), h2(a(href=os.path.join("/", name, "new"))("new")), t)
        
    def __call__(self, environ, start_response):
        path = urllib.unquote(environ["PATH_INFO"])
        dirname, basename = os.path.split(path)
        innerhtml = blank()
        if path == "/":
            pathValid = True
            innerhtml = ""
        elif basename in self.dbTypes:
            pathValid = True
            innerhtml = self.showEntries(self.dbTypes[basename])
        elif dirname[1:] in self.dbTypes:
            pathValid = True
            dbType = self.dbTypes[dirname[1:]]
            action = basename.split("?")[0]
            if action == "new":
                innerhtml = self.new(dbType, environ)
            elif action == "delete":
                innerhtml = self.delete(dbType, environ)
            elif action == "edit":
                innerhtml = self.edit(dbType, environ)
        else:
            pathValid = False
            status = "404 Not found"
            headers = [("Content-Type", "text/plain")]
            start_response(status, headers)
            yield status
            
        if pathValid:
            status = "200 OK"
            headers = [("Content-Type", "text/xml; charset=UTF-8")]
            yield unicode(XHTML10DTD())
            src = \
            html(
                head(
                    meta(charset="UTF-8")
                ),
                body(
                    self.menu(),
                    innerhtml
                )
            )
            yield src.toStr().decode("utf-8")
            
            


if __name__ == "__main__":
    
    import sqlite3
    import pyttp.database
    import blog

    
    conn = sqlite3.connect(os.path.expanduser("~/.pyttp/blogdb"), check_same_thread=False)
    pyttp.database.globalConnObj = conn
    conn.row_factory = sqlite3.Row
    
    blog.BlogEntry.create()
    blog.BlogAuthor.create()
    blog.BlogComment.create()
    
    http = wsgi.WSGIListener(DataBaseTypesEditor([blog.BlogEntry, blog.BlogAuthor, blog.BlogComment], {blog.BlogEntry: "title", blog.BlogAuthor: "name", blog.BlogComment:"author"}), 8080)
    http.serve()