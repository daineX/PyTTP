# -*- coding: utf-8 -*-
from pyttp import wsgi
from pyttp import helpers
from pyttp.html import *
import pyttp.database
from pyttp.database import hasField, hasA, hasMany

from basic_auth import HTTPMD5

import os
import sqlite3
import datetime
import urllib
import urlparse
import re

css = style("""

body {
    text-align:center;
    background:#aaa;
}

#frame {
    width:850px;
    margin-right:auto;
    margin-left:auto;
    margin-top:10px;
    padding:0px;
    text-align:left;
}

#menu {
    width:140px;
    padding:0px;
    float:left;
    background:#fff;
}

#menu table tr  {
    border: 1px solid #f00;
    background: #333;
}

#menu table tr td {
    padding: 3px;
    color: #fff;
}

#menu table tr td a {
    color: #fff;
    text-decoration: none
}

#menu table tr td a:hover {
    color: #fff;
}

#content {
    width:700px;
    padding:0px;
    float:left;
    margin-left:10px;
    background:#eee;
}

#empty{
    width:175px;
    padding:0px;
    float:left;
    background:#fff;
}

#kopf {
    background:#fff
}


""", type="text/css")


class BlogAuthor(pyttp.database.DataBaseObj):
    
    hasField(unicode, "name")
    hasField(unicode, "website")

class BlogComment(pyttp.database.DataBaseObj):
    
    hasField(unicode, "text")
    hasField(unicode, "author")
    hasField(str, "email")

    SIMPLE_BBCODES = ["b", "i", "u", "center", "li", "ul", "ol"]
    ADV_BBCODES = [("url", "a", "href")]
    SINGLE_BBCODES = [("img", "img", "src")]
    
    def text2format(self):
        textCopy = noEscapeBlank()
        lines = self.text.split("\n")
        for line in lines:
            line = html_escape(line)
            for bbcode in self.SIMPLE_BBCODES:
                line = re.sub(r"\[%s\](.*?)\[\/%s\]" % (bbcode, bbcode), r"<%s>\1</%s>" % (bbcode, bbcode), line)
            for bbcode, htmlTag, defaultAttr in self.ADV_BBCODES:
                line = re.sub(r"\[%s\=(.*?)](.*?)\[\/%s\]" % (bbcode, bbcode), r"<%s %s=\1>\2</%s>" % (htmlTag, defaultAttr, htmlTag), line)
            for bbcode, htmlTag, defaultAttr in self.SINGLE_BBCODES:
                line = re.sub(r"\[%s\](.*?)\[\/%s\]" % (bbcode, bbcode), r"<%s %s=\1/>" % (htmlTag, defaultAttr), line)
            textCopy.add(line)
            textCopy.add(br())
        return textCopy

class BlogEntry(pyttp.database.DataBaseObj):

    hasField(unicode, "title")
    hasField(unicode, "text")
    hasA(BlogAuthor, "author")
    hasMany(BlogComment, "comments")


    def text2format(self):
        textCopy = noEscapeBlank()
        for line in self.text.split("\n"):
            textCopy.add(line)
            textCopy.add(br())
        return textCopy
        
        
class Administration(object):
    
    
    def __call__(self, environ, start_response):
        if not environ.has_key('REMOTE_USER'):
            status = '401 Unauthorized'
            headers = [('Content-type', 'text/html'), ('WWW-Authenticate', 'Basic realm="Administration"')]
            start_response(status, headers)
        else:
            status = "200 OK"
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            start_response(status, headers)

            try:
                payloadLength = int(environ['CONTENT_LENGTH'])
                pquery = urlparse.parse_qs(environ['wsgi.input'].read(payloadLength))
            except KeyError:
                pquery = {}
            query = urlparse.parse_qs(environ["QUERY_STRING"])
            path = urllib.unquote(environ["PATH_INFO"][1:])
            
            yield str(XHTML10DTD())
            base = lambda *childs, **attrs: html(xmlns="http://www.w3.org/1999/xhtml")(head(title("The pythonic way of life"), css, link(rel="icon", href="/data/favicon.ico", type="image/x-icon")), body(*childs, **attrs))
            cell = lambda *childs, **attrs: tr(td(*childs, **attrs))
        
        
            menu = div(id="menu")
            menuTable = table()
            menuTable.add(cell("Menu"))
            menuTable.add(cell(a("Authors", href="/admin/authors")))
            menuTable.add(cell(a("Entries", href="/admin/entries")))
            menuTable.add(cell(a("Comments", href="/admin/comments")))
            menu.add(menuTable)
            
            wrap = div(id="frame")

            header = div(img(src="/data/header.png", alt="Ich bin ein Platzhalter!"), id="kopf")

            content = div(id="content")
            
            if path == "admin/entries":
                content.add(
                    a(href="/admin/entries/new")("New Entry"), br(), br()
                )
            
                for entry in BlogEntry.select_creation(asc=False):
                    
                    dateString = datetime.datetime.fromtimestamp(entry.cdate).strftime("%d.%m.%Y %H:%M")
                    
                    if entry.title:
                        content.add( a(href="/admin/entries/edit?eid=%s" % entry.id)(entry.title) )
                    else:
                        content.add( a(href="/admin/entries/edit?eid=%s" % entry.id)("<ID: %s>" % entry.id) )
                    content.add(" %s written by %s" % (dateString, entry.author.name))
                    content.add(br(),
                        a(href="/admin/entries/delete?eid=%s" % entry.id, onClick="return confirm('Delete entry?')")("Delete Entry"), br(), br()
                    )
            elif path == "admin/entries/new":
                
                theAuthors = select (name="author", size="1")
                for author in BlogAuthor:
                    theAuthors.add(
                        option(value=(author.id))(author.name)
                    )
                submit = \
                form(action="/admin/entries/submit", method="post")(
                    "Author: ", theAuthors, br(),
                    "Title: ", input(name="title"), br(),
                    "Text: ", textarea("",name="text", cols="50", rows="10"), br(),
                    input(type="submit", value="submit")
                )
                content.add(submit)

            elif path == "admin/entries/edit":
                try:
                    eid = int(query["eid"][0])
                    entry = BlogEntry.select_id(eid)
                except:
                    content.add(b("Invalid entry id!"))
                    eid = None
                if eid is not None:
                    
                    authorID = entry.author.id
                    theAuthors = select (name="author", size="1")
                    for author in BlogAuthor:
                        if author.id == authorID:
                            theAuthors.add(
                                option(value=(author.id), selected=None)(author.name)
                            )
                        else:
                            theAuthors.add(
                                option(value=(author.id))(author.name)
                            )                            
                    
                    submit = \
                    form(action="/admin/entries/change", method="post")(
                        "Author: ", theAuthors, br(),
                        "Title: ", input(name="title", value=entry.title), br(),
                        "Text: ", textarea(entry.text,name="text", cols="50", rows="10"), br(),
                        input(type="submit", value="submit"),
                        input(type="hidden", name="eid", value=str(eid))
                    )
                    
                    content.add(submit)
                    
                    if entry.getRefCount("comments"):
                        content.add(br(), "Comments:", br())
                        for comment in entry.comments:
                            content.add(comment.author, br())
                            content.add(datetime.datetime.fromtimestamp(comment.cdate).strftime("%d.%m.%Y %H:%M"), br())
                            content.add(comment.email, br())
                            content.add(a(href="/admin/comments/delete?eid=%s&cid=%s" % (eid, comment.id), onClick="return confirm('Delete comment?')")("Delete comment"))
                            content.add(br(), br())
                
            elif path == "admin/comments/delete":
                try:
                    cid = int(query["cid"][0])
                    comment = BlogComment.select_id(cid)
                except:
                    content.add(b("Invalid comment id!"), br())
                    cid = None
                if cid is not None:
                    BlogComment.delete(comment)
                    content.add("Deleted comment. ID: %s" % cid)
                    
                    try:
                        eid = int(query["eid"][0])
                        content.add(br(), a(href="/admin/entries/edit?eid=%s" % eid)("Back"))
                    except:
                        pass
                    
                    
            elif path == "admin/entries/delete":
                try:
                    eid = int(query["eid"][0])
                    entry = BlogEntry.select_id(eid)
                except:
                    content.add(b("Invalid entry id!"), br())
                    eid = None
                if eid is not None:
                    BlogEntry.delete(entry)
                    
                    content.add("Deleted entry. ID: %s" % eid)
                

            elif path == "admin/entries/submit":
                try:
                    _title = pquery['title'][0]
                except:
                    content.add(b("WARNING: No title given!"), br())
                    _title = ""
                try:
                    author = int(pquery['author'][0])                    
                    theAuthor = BlogAuthor.select_id(author)
                except:
                    content.add(b("Error: No author given!"), br())
                    author = None
                try:
                    text = pquery['text'][0]
                except:
                    text = ""
                
                if author is not None:
                    entry = BlogEntry.new(text=text, title=_title)
                    entry.setRef(theAuthor)
                    
                    content.add("Added entry. ID: %s" % entry.id)
                
            elif path == "admin/entries/change":
                try:
                    _title = pquery['title'][0]
                except:
                    content.add(b("WARNING: No title given!"), br())
                    _title = ""
                try:
                    author = int(pquery['author'][0])                    
                    theAuthor = BlogAuthor.select_id(author)
                except:
                    content.add(b("Error: No author given!"), br())
                    author = None
                try:
                    text = pquery['text'][0]
                except:
                    text = ""
                try:
                    eid = int(pquery["eid"][0])
                    entry = BlogEntry.select_id(eid)
                except:
                    content.add(b("Invalid entry id!"))
                    eid = None
                if eid is not None:
                    
                    entry.text = text
                    entry.title = _title
                    
                    try:
                        entry.deleteRef(entry.author)
                    except:
                        pass
                    entry.setRef(theAuthor)
                    
                    content.add("Changed entry. ID: %s" % entry.id)
                    
                    
            elif path == "admin/authors":
                
                content.add(a(href="/admin/authors/new")("New author"), br(), br())
                
                for author in BlogAuthor:
                    content.add(a(href="/admin/authors/edit?aid=%s" % author.id)(author.name), br())                  

            elif path == "admin/authors/new":
                
                submit = \
                form(action="/admin/authors/submit", method="post")(
                    "Name", input(name="name"), br(),
                    "Website", input(name="website"), br(),
                    input(type="submit", value="submit")
                )
                
                content.add(submit)
                
            elif path == "admin/authors/submit":
                
                try:
                    name = pquery["name"][0]
                except:
                    content.add(b("WARNING: No name given!"), br())
                    name = ""
                try:
                    website = pquery["website"][0]
                except:
                    content.add(b("WARNING: No website given!"), br())
                    website = ""
                
                author = BlogAuthor.new(name=name, website=website)
                content.add("Added author. ID: %s" % author.id)

            elif path == "admin/authors/edit":
                
                try:
                    aid = int(query["aid"][0])
                    theAuthor = BlogAuthor.select_id(aid)
                except:
                    content.add(b("Invalid author id!"))
                    aid = None
                    
                if aid is not None:
                    submit = \
                    form(action="/admin/authors/change", method="post")(
                        "Name", input(name="name", value=theAuthor.name), br(),
                        "Website", input(name="website", value=theAuthor.website), br(),
                        input(type="submit", value="submit"),
                        input(type="hidden", name="aid", value=str(aid))
                    )
                    content.add(submit)          

            elif path == "admin/authors/change":
                try:
                    aid = int(pquery["aid"][0])
                    theAuthor = BlogAuthor.select_id(aid)
                except:
                    content.add(b("Invalid author id!"))
                    aid = None
                if aid is not None:
                    try:
                        name = pquery["name"][0]
                    except:
                        content.add(b("WARNING: No name given!"), br())
                        name = ""
                    try:
                        website = pquery["website"][0]
                    except:
                        content.add(b("WARNING: No website given!"), br())
                        website = ""
                    
                    theAuthor.name = name
                    theAuthor.website = website
                    content.add("Changed author. ID: %s" % theAuthor.id)                  

            yield str(base(wrap(header, menu, content)))


class Blog(object):

    def __init__(self, database=None):
        if not database:
            self.database = os.path.expanduser("~/.pyttp/blogdb")
        else:
            self.database = database
            
        conn = sqlite3.connect(self.database, check_same_thread=False)
        pyttp.database.globalConnObj = conn
        conn.row_factory = sqlite3.Row
        
        BlogComment.create()
        BlogAuthor.create()
        BlogEntry.create()
            
    def __call__(self, environ, start_response):
        status = "200 OK"
        headers = [('Content-Type', 'text/html; charset=UTF-8')]
        start_response(status, headers)

        try:
            payloadLength = int(environ['CONTENT_LENGTH'])
            pquery = urlparse.parse_qs(environ['wsgi.input'].read(payloadLength))
        except KeyError:
            pquery = {}
        query = urlparse.parse_qs(environ["QUERY_STRING"])
        path = urllib.unquote(environ["PATH_INFO"][1:])

        
        
        yield str(XHTML10DTD())
        base = lambda *childs, **attrs: html(xmlns="http://www.w3.org/1999/xhtml")(head(title("The pythonic way of life"), css, link(rel="icon", href="/data/favicon.ico", type="image/x-icon")), body(*childs, **attrs))
        cell = lambda *childs, **attrs: tr(td(*childs, **attrs))
        

        wrap = div(id="frame")

        header = div(img(src="/data/header.png", alt="Ich bin ein Platzhalter!"), id="kopf")

        content = div(id="content")
        
        ctext = ""
        cemail = ""
        cauthor = ""
        
        if path == "submitComment" and "eid" in query:
            try:
                submitFailed = False
                eid = int(query['eid'][0])
                entry = BlogEntry.select_id(eid)
                try:
                    ctext = pquery['text'][0]
                except:
                    ctext = ""
                    content.add(b("Text missing!"))
                    submitFailed = True
                try:
                    cauthor = pquery['author'][0]
                except:
                    cauthor = ""
                    content.add(b("Author missing!"))
                    submitFailed = True
                try:
                    cemail = pquery['email'][0]
                    mailExp = re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)",re.IGNORECASE)
                    if cemail != re.match(mailExp, cemail).group(0):
                        submitFailed = True
                        content.add(b("Invalid email address!"))
                except:
                    cemail = ""
                    content.add(b("Invalid email address!"))
                    submitFailed = True
                if not submitFailed:
                    theComment = BlogComment.new(author=cauthor, text=ctext, email=cemail)
                    entry.setRef(theComment)
            except Exception, e:
                print e
                submitFailed = True

            if not submitFailed:
                ctext = ""
                cemail = ""
                cauthor = ""


        page = None
        
        nEntries = BlogEntry.count()
        maxPages = nEntries / 10 if nEntries % 10 == 0 else nEntries / 10 + 1
        
        singleEntry = False
        try:
            eid = int(query['eid'][0])
            entries = [BlogEntry.select_id(eid)]
            singleEntry = True
        except:
            try:
                page = int(query['page'][0])
                if page > maxPages:
                    page = 1
                entries = BlogEntry.select_creation(asc=False, limit=10, offset=(10 * (page-1))) 
            except:
                #page = 1
                entries = BlogEntry.select_creation(asc=False, limit=10)

        for entry in entries:
            eid = entry.id
            date = entry.cdate
            try:
                author = entry.author.name
            except:
                author = "Unknown"
            _title = entry.title
            text = entry.text
            t = table(style="width:680px; margin:10px;")
            
            dateString = datetime.datetime.fromtimestamp(date).strftime("%d.%m.%Y %H:%M")

            t = \
            table(style="width:680px; margin:10px;")(
                tr(style="background:#aaa; font-size:x-large; font-weight:bold")(
                    td(colspan="2")(
                        a(href="entry?eid=%s" % eid)(
                        _title)
                    )
                ),
                tr(
                    td(colspan="2")(
                        entry.text2format()
                    )
                ),
                tr(style="background:#aaa")(
                    td(
                        a(href="entry?eid=%s" % eid)(
                            "Comments[%s]" % entry.getRefCount("comments")
                        )
                    ),
                    td(style="text-align:right")(
                        " ", dateString, " by ", author)
                    )
            )

            content.add(t)
            
            if singleEntry:
            
                for comment in entry.comments:
                    text = comment.text2format()
                    date = datetime.datetime.fromtimestamp(comment.cdate).strftime("%d.%m.%Y %H:%M")
                    author = comment.author
                    email = comment.email
                    
                    content.add(author, " ", email, " ", date,  br(), text)
                    content.add(br(), br())

                content.add(b("New Comment"))
                submit = \
                form(action="submitComment?eid=%s" % eid, method="post")(
                    table(style="margin: 10px")(
                        tr(td("Author: "), td(input(name="author", value=cauthor))),
                        tr(td("Email: ") , td(input(name="email", value=cemail))),
                        tr(td("Text: ")  , td(textarea(ctext, name="text", cols="50", rows="10"))),
                        tr(td(),td(input(type="submit", value="submit")))
                    )
                )
                
                content.add(submit)
                
        footer = div(style="text-align:center;")
        if page:
            if page == 1:
                footer.add(span("<<"))
            else:
                footer.add(a("<<", href="/?page=%s" % (page - 1)))
            if page == maxPages:
                footer.add(span(">>"))
            else:
                footer.add(a(">>", href="/?page=%s" % (page + 1)))
            content.add(footer)


        menu = div(id="menu")
        menuTable = table()
        menuTable.add(cell("Menu"))
        menuTable.add(cell(a("Recent Entries", href="/recent")))
        menuTable.add(cell(a("Archive", href="/archive")))
        menuTable.add(cell(a("About", href="/about")))
        menu.add(menuTable)
                    
        yield str(base(wrap(header, menu, content)))
            

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1])
    try:
        action = sys.argv[2]
    except:
        action = ""
    if action == "recreate":
        conn = sqlite3.connect(os.path.expanduser("~/.pyttp/blogdb"))
        c = conn.cursor()
        try:
            c.execute('''drop table BlogEntry''') 
            c.execute('''drop table BlogAuthor''')
            c.execute('''drop table BlogComment''')
            c.execute('''drop table BlogEntry_to_BlogAuthor''')
            c.execute('''drop table BlogEntry_to_BlogComment''')
        except Exception, e:
            print e
        conn.commit()
        conn.close()
        
    import redirector
    import fileserve
    
    fServe = fileserve.FileServe(os.path.expanduser("~/.pyttp/blogdata"))
    redirect = redirector.RedirectorApp([("/data/.*", fServe, 1), (".*/favicon.ico", fServe), ("/admin/.*", HTTPBasic(Administration(), {"adminr": "admin"}, "Administration")), ("/.*", Blog())])
        
    http = wsgi.WSGIListener(redirect, port)
    http.serve()
