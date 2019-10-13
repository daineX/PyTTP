# -*- coding: utf-8 -*-
from __future__ import print_function

import types

html_escape_table = {
    u"&": u"&amp;",
    u'"': u"&quot;",
    u"'": u"&apos;",
    u">": u"&gt;",
    u"<": u"&lt;",
    }

def html_escape(text):
    """Produce entities within text."""
    if isinstance(text, str) or isinstance(text, unicode):
        return u"".join(html_escape_table.get(c,c) for c in text)
    else:
        return str(text)



class Tag(object):
    
    name = u''
    ldel = u"<"
    rdel = u">"
    edel = u"/>"
    sdel = u"</"
    doEscape = True
    
    def __init__(self, *childs, **attributes):
        self.childs = []
        for item in childs:
            if isinstance(item, types.GeneratorType):
                self.childs += list(item)
            else:
                self.childs.append(item)
        self.attributes = attributes
       
    def __call__(self, *childs, **attributes):
        for item in childs:
            if isinstance(item, types.GeneratorType):
                self.childs += list(item)
            else:
                self.childs.append(item)
        for item, value in attributes.items():
            self.attributes[item] = value
        return self
        
    def setAttr(self, attr, value):
        self.attributes[attr] = value
        
    def add(self, *childs):
        for item in childs:
            if isinstance(item, types.GeneratorType):
                self.childs += list(item)
            else:
                self.childs.append(item)
        
    def __str__(self):
        return str(self.toStr())

    def __unicode__(self):
        return self.toStr()
        
    def toStr(self, depth=0):
        if len(self.attributes):
            attributeStr = []
            for attr, value in self.attributes.items():
                if value is not None:
                    attributeStr.append(u'%s="%s"' % (attr, value))
                else:
                    attributeStr.append(u'%s="%s"' % (attr, attr))
            attributeStr = self.ldel+self.name+" "+' '.join(attributeStr)
        else:
            attributeStr = self.ldel+self.name
        #self.attributes = {}
        lastIsTag = True
        childStr = u''
        if not len(self.childs):
            return (attributeStr+self.edel+u'\n')
        for x in self.childs:
            if not isinstance(x, Tag):
                if isinstance(x, str):
                    try:
                        x = x.decode("utf-8")
                    except:
                        pass
                else:
                    x = unicode(x)
                assert isinstance(x, unicode)
                if self.doEscape:
                    childStr += html_escape(x)
                else:
                    childStr += x
                lastIsTag = False
            else:
                if lastIsTag:
                    if isinstance(x, blank):
                        childStr += (u'  '*(depth+1))+x.toStr(depth+1)
                    else:
                        childStr += (u'\n'+u'  '*(depth+1))+x.toStr(depth+1)
                else:
                    childStr += x.toStr(depth+1)                    

                lastIsTag = True
        if lastIsTag:
            endStr = (u'  '*depth)+self.sdel+self.name+self.rdel+u'\n'
        else:
            endStr = self.sdel+self.name+self.rdel+u'\n'
        return (attributeStr +self.rdel+ childStr + endStr).replace(u"\n\n", u"\n")
        
    def copy(self):
        return self.__class__(*tuple(self.childs), **self.attributes)
                     

class Comment(object):
    def __init__(self, content):
        self.content = content
        
    def __call__(self):
        return str(self)
        
    def __str__(self):
        return u"<!-- %s -->" % (self.content,)
        
class DTD(object):

    def __init__(self, root, kind, fpi, uri=None):
        self.root = root
        if kind not in ("PUBLIC", "SYSTEM"):
            raise Exception("Invalid DTD kind!")
        self.kind = kind
        self.fpi = fpi
        self.uri = uri
   
    def __call__(self):
        return str(self)
        
    def __str__(self):
        if self.kind == "PUBLIC":
            if self.uri:
                return '<!DOCTYPE %s %s "%s" "%s">\n' % (self.root, self.kind, self.fpi, self.uri)
            else:
                return '<!DOCTYPE %s %s "%s" "%s">\n' % (self.root, self.kind, self.fpi)
        return '<!DOCTYPE %s %s "%s" "%s">\n' % (self.root, self.kind, self.uri)

class PublicDTD(DTD):
    def __init__(self, root, fpi, uri=None):
        DTD.__init__(self, root, "PUBLIC", fpi, uri)
        
class SystemDTD(DTD):
    def __init__(self, root, uri):
        DTD.__init__(self, root, "SYSTEM", "", uri)
        
class XHTML10DTD(PublicDTD):
    def __init__(self):
        PublicDTD.__init__(self, "html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")


__tags = ['a', 'abbr', 'acronym', 'address', 'applet', 'area', 
        'b', 'base', 'basefont', 'bdo', 'big', 'blockquote', 
        'body', 'br', 'button', 'caption', 'center', 'cite', 
        'code', 'col', 'colgroup', 'dd', 'del_', 'dfn', 'dir_', 
        'div', 'dl', 'dt', 'em', 'fieldset', 'font', 'form', 
        'frame', 'frameset', 'head', 'h1', 'h2', 'h3', 'h4', 
        'h5' 'h6', 'hr', 'html', 'i', 'iframe', 'img', 'input',
        'ins', 'kbd', 'label', 'legend', 'li', 'link', 'map',
        'menu', 'meta', 'noframes','noscript', 'object', 'ol',
        'optgroup', 'option', 'p', 'param', 'pre', 'q', 's',
        'samp', 'script', 'select', 'small', 'span', 'strike',
        'strong', 'style', 'sub', 'sup', 'table', 'tbody', 'td',
        'textarea', 'tfoot', 'th', 'thead', 'title', 'tr', 'tt', 
        'u', 'ul', 'var'] + ['audio', 'video']

for __tag in __tags:
    __ntag = __tag.strip("_")
    exec ("%s = type('%s', (Tag,), {'name': '%s'})" % (__tag, __ntag, __ntag))
blank = type('blank', (Tag,), {'name': '', 
                               'ldel': '',
                               'rdel': '',
                               'edel': '',
                               'sdel': ''})
noEscapeBlank = type('noescapeBlank', (Tag,), {'name': '', 
                               'ldel': '',
                               'rdel': '',
                               'edel': '',
                               'sdel': '',
                               'doEscape': False})


if __name__ == "__main__":
    print(str(html(head(title("This is a Test!")))(nonExistentAttr="bogusValue")))
    print(PublicDTD("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"))
    print(Comment("This is a comment!"))
    
    src = \
    html(
        head(
            title("This is a title")
        ),
        body(
            form(action="/", method="POST", enctype="multipart/form-data")(
                "Datei: ", input(type="file", size="50", name="Datei"),
                "Name: ", input(type="text", size="50", name="Name"),
                input(type="submit")
            )
        )
    )
    
    print(str(src))
    
    links = ['index.py', 'img.py', 'dem.py']
    
    
    inner = blank()
    src = \
    html(
        body(inner)
    )
    
    inner.add((a(href=link)(link) for link in links),(br() for i in range(10)), "demPuppies")
    
    print(str(src))
