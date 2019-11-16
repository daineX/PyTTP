import re

from pyttp.html import html_escape

TAB_INDENT = 4

g = globals()

class Node(object):


    class ParseError(Exception):
        pass

    class Error(Exception):
        pass


    def __init__(self, line, parent=None):
        self.line = line
        self.parent = parent
        self.children = []
        if parent:
            parent.add_child(self)


    def add_child(self, child):
        self.children.append(child)


    def render(self, context, indent):
        return u''.join(x.render(context, indent) for x in self.children)

    @property
    def is_tag(self):
        return False

    @property
    def is_exec_node(self):
        return False

    def eval_code(self, context, markup, honor_autoescape=False):
        if markup in context:
            value = context[markup]
        else:
            value = eval(markup, g, context)
        if callable(value):
            value = value()
        if honor_autoescape:
            value = html_escape(value)
        return value

    def __repr__(self):
        return "Node(%s)" % (self.line,)


class CommentNode(Node):

    def render(self, context, indent):
        return ""


class TextNode(Node):

    def render(self, context, indent):
        return self.line


    def add_child(self, child):
        raise Node.Error("A TextNode may not have any children")



class EvalNode(TextNode):

    honor_autoescape = True
    prefix = 1

    def render(self, context, indent):
        res = self.eval_code(
            context,
            self.line[self.prefix:],
            honor_autoescape=self.honor_autoescape)
        return str(res)

class UnescapedEvalNode(EvalNode):

    honor_autoescape = False
    prefix = 2

class TagNode(Node):

    TAG_RE = r"(?P<shortcut>[%\.#])(?P<tag_name>\w[\w#\.\-]*)(\((?P<attrs>.+)\))?(?P<value_insert>=)?(?P<remainder>.+)?"
    TAG_CLASS_RE = r"\.(?P<class>\w[\w\-]*)"
    TAG_NAME_RE = r"(?P<name>\w+)"

    TAG_ID_RE = r"#(?P<id>\w[\w\-]*)"
    ATTR_RE = r"(?P<key>[\w\-\_]+):\s*'(?P<value>.*?)',?", r"(?P<key>[\w\-\_]+):\s*\"(?P<value>.*?)\",?"

    def __init__(self, line, parent=None):
        super(TagNode, self).__init__(line, parent)

        (self.shortcut, self.tag_name, self.attrs,
         self.is_value_insert, self.remainder) = self._parse_tag()

        self.attrs = self._parse_attrs(self.attrs)
        self.tag_name, self.attrs = self._handle_shortcuts(self.tag_name, self.attrs)


    @property
    def is_tag(self):
        return True


    def _parse_tag(self):
        m = re.match(TagNode.TAG_RE, self.line)
        shortcut = m.group('shortcut')
        tag_name = m.group('tag_name')
        if shortcut in "#.":
            tag_name = "div" + shortcut + tag_name
        attrs = m.group('attrs')
        is_value_insert = bool(m.group('value_insert'))
        remainder = m.group('remainder')
        if remainder:
            remainder = remainder.lstrip()
        if attrs:
            attrs = attrs.strip()
        return shortcut, tag_name, attrs, is_value_insert, remainder


    def _parse_attrs(self, attrs):
        parsed_attrs = []
        while attrs:
            for regex in TagNode.ATTR_RE:
                m = re.match(regex, attrs)
                if m:
                    break
            else:
                raise Node.ParseError("Failed to parse attributes, remainder was %s" % attrs)
            key, value = m.group('key'), m.group('value')
            parsed_attrs.append((key, value))
            attrs = attrs[m.end():].lstrip()

        return parsed_attrs


    def _handle_shortcuts(self, tag_string, attrs):
        original_string = tag_string
        m = re.match(TagNode.TAG_NAME_RE, tag_string)
        name = m.group("name")
        tag_string = tag_string[m.end():]

        classes = []
        tag_id = None
        while tag_string:
            m = re.match(TagNode.TAG_CLASS_RE, tag_string)
            if m:
                classes.append(m.group("class"))
                tag_string = tag_string[m.end():]
                continue
            m = re.match(TagNode.TAG_ID_RE, tag_string)
            if m:
                tag_id = m.group("id")
                tag_string = tag_string[m.end():]
                continue
            else:
                msg = ("Failed to parse special shortcuts; error in \"%s\" at %i."
                       % (original_string,
                         len(original_string) - len (tag_string),
                         )
                      )
                raise Node.ParseError(msg)
        if classes:
            attrs.append((u'class', u' '.join(classes)))
        if tag_id:
            attrs.append((u'id', tag_id))
        return name, attrs


    def render(self, context, indent):

        start = self._render_tag_start(context, indent, self.tag_name, self.attrs, self.remainder, self.is_value_insert)

        childs = u''
        close = u''
        if self.remainder and self.children:
            childs = u' '
        if self.children:
            childs += u' '.join(child.render(context, indent + 1) for child in self.children)
        new_line = any(x.is_tag or x.is_exec_node for x in self.children)
        if self.children or self.remainder:
            close = self._render_closing_tag(indent, self.tag_name, new_line=new_line)

        return start + childs + close


    def _render_tag_start(self, context, indent, tag_name, attrs, remainder, eval_remainder=False):
        html = [u'\n', u' ' * indent * TAB_INDENT]
        html.append(u'<%s' % tag_name)
        if attrs:
            html.append(' ')
            evaluated_attrs = []
            for key, value in attrs:
                if value.startswith("="):
                    value = self.eval_code(context, value[1:].lstrip(), honor_autoescape=True)
                evaluated_attrs.append(u'%s="%s"' % (key, value))
            html.append(u' '.join(evaluated_attrs))
        if eval_remainder and remainder:
            res = self.eval_code(context, remainder.lstrip(), honor_autoescape=True)
            try:
                remainder = res.decode("utf-8")
            except:
                remainder = str(res)
        if self.children or self.remainder:
            html.append(self._render_tag_end(one_line=False))
        else:
            html.append(self._render_tag_end(one_line=True))
        if remainder and remainder != "!":
            html.append(remainder)
        return u''.join(html)


    def _render_tag_end(self, one_line):
        if one_line:
            return u' />'
        else:
            return u'>'


    def _render_closing_tag(self, indent, tag_name, new_line=False):

        res = []
        if new_line:
            res += ['\n', ' '*(TAB_INDENT*indent)]
        res += [u'</',
                tag_name,
                u'>',
              ]

        return u''.join(res)

    def __repr__(self):

        return "<%s>" % self.tag_name
