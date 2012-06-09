
import re


class Template(object):

    class ParseError(Exception):
        pass

    TAB_INDENT = 4

    tag_re = r"%(?P<tag_name>\w[\w#\.]*)(\((?P<attrs>.+)\))?(?P<value_insert>=)?(?P<remainder>.+)?"
    tag_name_re = r"(?P<name>\w+)"
    tag_class_re = r"\.(?P<class>\w+)"
    tag_id_re = r"#(?P<id>\w+)"
    attr_re = r"(?P<key>\w+):\s*'(?P<value>.+?)',?", r"(?P<key>\w+):\s*\"(?P<value>.+?)\",?"

    def is_comment(self, line):
        return line.strip().startswith('#')


    def is_tag(self, line):
        return line.strip().startswith('%')


    def is_value_insert(self, line):
        return line.startswith('=')


    def indentation_depth(self, line):
        indent = 0
        for char in line:
            if char == ' ':
                indent += 1
            elif char == '\t':
                indent += Template.TAB_INDENT
            else:
                break
        return line.lstrip(), indent


    def parse_tag(self, stripped_line):

        m = re.match(Template.tag_re, stripped_line)
        tag_name = m.group('tag_name')
        attrs = m.group('attrs')
        is_value_insert = bool(m.group('value_insert'))
        remainder = m.group('remainder')
        if remainder:
            remainder = remainder.lstrip()
        if attrs:
            attrs = attrs.strip()
        return tag_name, attrs, is_value_insert, remainder


    def parse_attrs(self, attrs):
        parsed_attrs = []
        while attrs:
            for regex in Template.attr_re:
                m = re.match(regex, attrs)
                if m:
                    break
            else:
                raise Template.ParseError("Failed to parse attributes, remainder was %s" % attrs)
            key, value = m.group('key'), m.group('value')
            parsed_attrs.append((key, value))
            attrs = attrs[m.end():].lstrip()

        return parsed_attrs

    def handle_shortcuts(self, tag_string, attrs):
        original_string = tag_string
        m = re.match(Template.tag_name_re, tag_string)
        name = m.group("name")
        tag_string = tag_string[m.end():]

        classes = []
        tag_id = None
        while tag_string:
            m = re.match(Template.tag_class_re, tag_string)
            if m:
                classes.append(m.group("class"))
                tag_string = tag_string[m.end():]
                continue
            m = re.match(Template.tag_id_re, tag_string)
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
                raise Template.ParseError(msg)
        if classes:
            attrs.append(('class', ' '.join(classes)))
        if tag_id:
            attrs.append(('id', tag_id))
        return name, attrs


    def eval_code(self, context, markup):
        return context[markup]


    def render_tag_start(self, context, indent, tag_name, attrs, remainder, eval_remainder=False):
        html = ['\n', ' ' * indent]
        html.append('<%s' % tag_name)
        if attrs:
            html.append(' ')
            evaluated_attrs = []
            for key, value in attrs:
                if value.startswith("="):
                    value = self.eval_code(context, value[1:].lstrip())
                evaluated_attrs.append('%s="%s"' % (key, value))
            html.append(' '.join(evaluated_attrs))
        if eval_remainder and remainder:
            remainder = self.eval_code(context, remainder.lstrip())
        if remainder:
            html.append(self.render_tag_end(one_line=False))
            html.append('\n')
            html.append(' ' * (indent + Template.TAB_INDENT))
            html.append(remainder)
        return ''.join(html)


    def render_tag_end(self, one_line):
        if one_line:
            return ' />'
        else:
            return '>'


    def render_closing_tag(self, indent, tag_name):
        return ''.join(['\n',
                    ' '*indent,
                    '</',
                    tag_name,
                    '>'
                ])


    def render(self, context, markup):
        tag_stack = []
        old_indent = None
        old_tag_name = None
        last_line_had_tag = False
        last_line_had_remainder = False
        for line in markup.split("\n"):
            if not line:
                continue
            if self.is_comment(line):
                continue

            stripped_line, indent = self.indentation_depth(line)

            if (last_line_had_tag
                and old_tag_name is not None
                and not last_line_had_remainder):
                    yield self.render_tag_end(one_line=False)


            if indent > old_indent:
                if last_line_had_tag:
                    tag_stack.append((old_tag_name, old_indent))

            else:
                if last_line_had_tag and last_line_had_remainder:
                    yield self.render_closing_tag(old_indent, old_tag_name)
                for closing_tag, closing_indent in reversed(tag_stack):
                    if closing_indent >= indent:
                        yield self.render_closing_tag(closing_indent, closing_tag)
                        tag_stack.pop()

            if self.is_tag(stripped_line):
                tag_name, attrs, is_value_insert, remainder = self.parse_tag(stripped_line)
                parsed_attrs = self.parse_attrs(attrs)
                tag_name, parsed_attrs = self.handle_shortcuts(tag_name, parsed_attrs)

                yield self.render_tag_start(context,
                                            indent,
                                            tag_name,
                                            parsed_attrs,
                                            remainder,
                                            eval_remainder=is_value_insert)
                old_tag_name = tag_name
                last_line_had_tag = True
                if remainder:
                    last_line_had_remainder = True
                else:
                    last_line_had_remainder = False
                old_indent = indent

            else:
                if last_line_had_remainder:
                    yield ' '
                    yield line.lstrip()
                elif last_line_had_tag:
                    yield '\n'
                    yield line
                else:
                    yield ' '
                    yield line.lstrip()
                last_line_had_tag = False
                last_line_had_remainder = False
        if last_line_had_tag:
            if last_line_had_remainder:
                yield self.render_closing_tag(old_indent, old_tag_name)
            else:
                yield self.render_tag_end(one_line=True)
        for closing_tag, closing_indent in reversed(tag_stack):
            yield self.render_closing_tag(closing_indent, closing_tag)
