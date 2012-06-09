import unittest

import sys
sys.path.append("../..")

from pyttp.template import Template


class RenderTests(unittest.TestCase):

    def setUp(self):
        self.template = Template()

    def test_comment(self):
        comment_line = "#this is a comment"
        non_comment_line = '%li'

        self.assertTrue(self.template.is_comment(comment_line))
        self.assertFalse(self.template.is_comment(non_comment_line))


    def test_tag(self):
        tag_line = '%li'
        non_tag_line = '$li'

        self.assertTrue(self.template.is_tag(tag_line))
        self.assertFalse(self.template.is_tag(non_tag_line))


    def test_value_insert(self):
        value_line = '= foo'
        non_value_line = 'bar'
        self.assertTrue(self.template.is_value_insert(value_line))
        self.assertFalse(self.template.is_value_insert(non_value_line))


    def test_indentation_depth(self):
        line = " \tI am indented"

        stripped_line, indent = self.template.indentation_depth(line)
        self.assertEqual(indent, 5)
        self.assertEqual(stripped_line, "I am indented")


    def test_parse_tag(self):
        line = "%a(href: 'bar', target: '_blank')= foo"

        self.assertEqual(self.template.parse_tag(line), ('a',
                                                    "href: 'bar', target: '_blank'",
                                                    True,
                                                    "foo"))

    def test_parse_attrs(self):
        attrs = "href: 'bar', target: \"foo\""

        self.assertEqual(self.template.parse_attrs(attrs), [('href', 'bar'), ('target', 'foo')])


    def test_handle_shortcuts(self):
        tag_string = "div#title.big.boxed"
        attrs = [('style', 'float: left;')]

        name, attrs = self.template.handle_shortcuts(tag_string, attrs)

        self.assertEqual(name, "div")
        self.assertEqual(attrs, [('style', 'float: left;'),
                                 ('class', 'big boxed'),
                                 ('id', 'title')])

    def test_invalid_attrs(self):
        missing_key = "'bar', target: 'foo'"
        missing_value = "href: 'bar', target: "
        wrong_delimiter = "href: 'bar'; target: 'foo'"
        missing_quotes = "href: 'bar'; target: foo"
        mixed_quotes = "href: 'bar\"; target: 'foo'"
        doubled_quotes = "href: ''bar''; target: 'foo'"

        self.assertRaises(Template.ParseError, self.template.parse_attrs, missing_key)
        self.assertRaises(Template.ParseError, self.template.parse_attrs, missing_value)
        self.assertRaises(Template.ParseError, self.template.parse_attrs, wrong_delimiter)
        self.assertRaises(Template.ParseError, self.template.parse_attrs, missing_quotes)
        self.assertRaises(Template.ParseError, self.template.parse_attrs, mixed_quotes)
        self.assertRaises(Template.ParseError, self.template.parse_attrs, doubled_quotes)


    def test_render_tag_start(self):

        indent = 4
        tag_name = 'li'
        remainder = "I'm a list item"
        attrs = ''

        rendered = self.template.render_tag_start({}, indent, tag_name, attrs, remainder)
        self.assertEqual(rendered, "\n    <li>\n        I'm a list item")


    def test_render_tag_end(self):

        self.assertEqual(self.template.render_tag_end(one_line=True), " />")
        self.assertEqual(self.template.render_tag_end(one_line=False), ">")


    def test_render(self):

        markup = """
%html
    %body
        %div#title.big.boxed= title
            %p= title
                bla
                foo
        #everything we got in one line
        %a.bold(href: '= link', target: "_blank")= greeting
"""
        expected = """
<html>
    <body>
        <div class="big boxed" id="title">
            Guten Tag
            <p>
                Guten Tag bla foo
            </p>
        </div>
        <a href="http://example.com" target="_blank" class="bold">
            hello
        </a>
    </body>
</html>"""

        context = dict(title="Guten Tag",
                       link="http://example.com",
                       greeting="hello",
                       )
        rendered = ''.join(self.template.render(context, markup))

        print rendered
        self.assertEqual(rendered, expected)