import unittest

import sys
sys.path.append("../..")

from pyttp.template import Node, TagNode, TextNode, Template


class RenderTests(unittest.TestCase):

    def setUp(self):
        self.template = Template()

    def test_comment(self):
        comment_line = "//this is a comment"
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

        tag_node = TagNode({}, line)

        self.assertEqual(tag_node._parse_tag(), ('a',
                                                    "href: 'bar', target: '_blank'",
                                                    True,
                                                    "foo"))
    def test_parse_attrs(self):
        attrs = "href: 'bar', target: \"foo\""
        tag_node = TagNode({}, "%dummy")
        self.assertEqual(tag_node._parse_attrs(attrs), [('href', 'bar'), ('target', 'foo')])


    def test_handle_div(self):

        line = ".big"
        self.assertEqual(self.template.handle_div(line), "%div.big")

        line = "#title"
        self.assertEqual(self.template.handle_div(line), "%div#title")


    def test_handle_shortcuts(self):
        tag_node = TagNode({}, "%dummy")

        tag_string = "div#title.big.boxed"
        attrs = [('style', 'float: left;')]

        name, attrs = tag_node._handle_shortcuts(tag_string, attrs)

        self.assertEqual(name, "div")
        self.assertEqual(attrs, [('style', 'float: left;'),
                                 ('class', 'big boxed'),
                                 ('id', 'title')])

    def test_invalid_attrs(self):
        tag_node = TagNode({}, "%dummy")
        missing_key = "'bar', target: 'foo'"
        missing_value = "href: 'bar', target: "
        wrong_delimiter = "href: 'bar'; target: 'foo'"
        missing_quotes = "href: 'bar'; target: foo"
        mixed_quotes = "href: 'bar\"; target: 'foo'"
        doubled_quotes = "href: ''bar''; target: 'foo'"

        self.assertRaises(Node.ParseError, tag_node._parse_attrs, missing_key)
        self.assertRaises(Node.ParseError, tag_node._parse_attrs, missing_value)
        self.assertRaises(Node.ParseError, tag_node._parse_attrs, wrong_delimiter)
        self.assertRaises(Node.ParseError, tag_node._parse_attrs, missing_quotes)
        self.assertRaises(Node.ParseError, tag_node._parse_attrs, mixed_quotes)
        self.assertRaises(Node.ParseError, tag_node._parse_attrs, doubled_quotes)


    def test_render_tag_start(self):

        tag_node = TagNode({}, "%li")
        tag_node.add_child(TextNode({}, "I'm a list item"))

        indent = 4
        tag_name = 'li'
        remainder = "I'm a list item"
        attrs = ''

        rendered = tag_node._render_tag_start({}, indent, tag_name, attrs, remainder)
        self.assertEqual(rendered, "\n                <li>I'm a list item")


    def test_render_tag_end(self):
        tag_node = TagNode({}, "%dummy")

        self.assertEqual(tag_node._render_tag_end(one_line=True), " />")
        self.assertEqual(tag_node._render_tag_end(one_line=False), ">")


    def test_render(self):

        class Greeting(object):
            pass

        greeting = Greeting()
        greeting.en = lambda: "hello"

        markup = """
%html
    %body
        #title.big.boxed= title
            %img(src: '= link')
            %p= title
                bla
                foo
        //everything we got in one line
        %a.bold#link(href: '= link', target: "_blank")= greeting['obj'].en
        blub
"""
        expected = '\n<html>\n    <body>\n        <div class="big boxed" id="title">Guten Tag \n            <img src="http://example.com" /> \n            <p>Guten Tag bla foo</p>\n        </div> \n        <a href="http://example.com" target="_blank" class="bold" id="link" />hello blub\n    </body>\n</html>'

        context = dict(title="Guten Tag",
                       link="http://example.com",
                       greeting=dict(obj=greeting),
                       )
        rendered = ''.join(self.template.render(context, markup))

        print markup
        print '=' * 80
        print rendered
        print '=' * 80
        print expected
        self.assertEqual(rendered, expected)


class NodeTests(unittest.TestCase):

    def test_render(self):

        ctx = {'link': 'example.com',
               'label': 'click me'}

        root_node = TagNode(ctx, "%html")
        body_node = TagNode(ctx, "%body")
        div_node = TagNode(ctx, "%div.big this is a test")
        a_node = TagNode(ctx, "%a(href: '= link')= label")
        text_node = TextNode(ctx, "hello")

        root_node.add_child(body_node)
        body_node.add_child(div_node)
        body_node.add_child(a_node)
        div_node.add_child(text_node)

        print root_node.render(0)


if __name__ == "__main__":

    unittest.main()        