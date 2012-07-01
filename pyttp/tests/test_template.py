import unittest

import os

from pyttp.template import Template
from pyttp.template_node import Node, TagNode, TextNode


class RenderTests(unittest.TestCase):

    def setUp(self):
        self.template = Template(os.path.join(os.path.dirname(__file__)))

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

        tag_node = TagNode( line)

        self.assertEqual(tag_node._parse_tag(), ('a',
                                                    "href: 'bar', target: '_blank'",
                                                    True,
                                                    "foo"))
    def test_parse_attrs(self):
        attrs = "href: 'bar', target: \"foo\""
        tag_node = TagNode( "%dummy")
        self.assertEqual(tag_node._parse_attrs(attrs), [('href', 'bar'), ('target', 'foo')])


    def test_handle_div(self):

        line = ".big"
        self.assertEqual(self.template.handle_div(line), "%div.big")

        line = "#title"
        self.assertEqual(self.template.handle_div(line), "%div#title")


    def test_handle_shortcuts(self):
        tag_node = TagNode( "%dummy")

        tag_string = "div#title.big.boxed"
        attrs = [('style', 'float: left;')]

        name, attrs = tag_node._handle_shortcuts(tag_string, attrs)

        self.assertEqual(name, "div")
        self.assertEqual(attrs, [('style', 'float: left;'),
                                 ('class', 'big boxed'),
                                 ('id', 'title')])

    def test_invalid_attrs(self):
        tag_node = TagNode( "%dummy")
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

        tag_node = TagNode("%li")
        tag_node.add_child(TextNode("I'm a list item"))

        indent = 4
        tag_name = 'li'
        remainder = "I'm a list item"
        attrs = ''

        rendered = tag_node._render_tag_start({}, indent, tag_name, attrs, remainder)
        self.assertEqual(rendered, "\n                <li>I'm a list item")


    def test_render_tag_end(self):
        tag_node = TagNode( "%dummy")

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
        expected = '\n<html>\n    <body>\n        <div class="big boxed" id="title">Guten Tag \n            <img src="http://example.com" /> \n            <p>Guten Tag bla foo</p>\n        </div> \n        <a href="http://example.com" target="_blank" class="bold" id="link">hello</a> blub\n    </body>\n</html>'

        context = dict(title="Guten Tag",
                       link="http://example.com",
                       greeting=dict(obj=greeting),
                       )
        rendered = ''.join(self.template.render(markup, context))

        self.assertEqual(rendered, expected)


    def test_conditional(self):
        context = {'foo': 'baz'}

        markup = """
%html
    %body
        -if foo == 'bar'
            bar
        -else
            .baz= foo
                =foo
"""

        expected = '\n<html>\n    <body> \n        <div class="baz">baz baz</div>\n    </body>\n</html>'


        rendered = ''.join(self.template.render(markup, context))
        self.assertEqual(rendered, expected)


    def test_loop(self):
        context = {}

        markup = """
%html
    %body
        -for item in [str(x) for x in range(10)]
            -if item != '4'
                .item= item
            -if item == '4'
                .item4 Item is 4!
        """
        expected = '\n<html>\n    <body>\n        <div class="item">0</div>\n        <div class="item">1</div>\n        <div class="item">2</div>\n        <div class="item">3</div>\n        <div class="item4">Item is 4!</div>\n        <div class="item">5</div>\n        <div class="item">6</div>\n        <div class="item">7</div>\n        <div class="item">8</div>\n        <div class="item">9</div>\n    </body>\n</html>'
        rendered = ''.join(self.template.render(markup, context))
        self.assertEqual(rendered, expected)


    def test_load(self):

        class Greeting(object):
            pass

        greeting = Greeting()
        greeting.en = lambda: "hello"

        context = dict(title="Guten Tag",
                       link="http://example.com",
                       greeting=dict(obj=greeting),
                       )

        expected = '\n<html>\n    <body>\n        <div class="big boxed" id="title">Guten Tag \n            <img src="http://example.com" /> \n            <p>Guten Tag bla foo</p>\n        </div> \n        <a href="http://example.com" target="_blank" class="bold" id="link">hello</a> blub\n    </body>\n</html>'

        rendered = ''.join(
                        Template.load_and_render(
                            'test.pyml',
                            context,
                            search_path=os.path.join(os.path.dirname(__file__)))
                        )
        self.assertEqual(rendered, expected)


    def test_pre_process(self):

        context = {}
        expected = '\n<html>\n    <head>\n        <title>Extending...</title>\n    </head> \n    <body>\n        <div class="content">We are extending templates</div> \n        <b>YAY</b> \n        <div class="bar" />\n    </body>\n</html>'
        rendered = ''.join(
                        Template.load_and_render(
                            'childchildchild.pyml',
                            context,
                            search_path=os.path.join(os.path.dirname(__file__)) )
                        )
        self.assertEqual(rendered, expected)


    def test_pre(self):
        context = {}
        markup = \
"""
%html
    %body
        -pre
            //This is PyML
            %html
                %head
                    -placeholder extend_head
                %body
                    .content
                        %h1 title
                        Here we have some text
"""
        rendered = ''.join(self.template.render(markup, context))


    def test_include(self):
        context = {}

        expected = '\n<html>\n    <head>\n        <link rel="stylesheet" type="text/css" href="/static/base.css" /> \n        <title>This is the title</title>\n    </head> \n    <body>\n        <div class="content" /> \n        <a href="#top">back to top</a>\n    </body>\n</html>'
        rendered = ''.join(
                        Template.load_and_render(
                           'extended_include.pyml',
                           context,
                           search_path=os.path.join(os.path.dirname(__file__)) )
                        )

        self.assertEqual(rendered, expected)


    def test_doctype(self):
        markup = """
-!!!
%html
    %head
        %title doctype
    %body
        .content
            This is the content
"""
        expected = '<!DOCTYPE html>\n\n<html>\n    <head>\n        <title>doctype</title>\n    </head> \n    <body>\n        <div class="content">This is the content</div>\n    </body>\n</html>'
        rendered = ''.join(self.template.render(markup))
        self.assertEqual(rendered, expected)


    def test_with(self):
        context = dict(title="Titel")        
        markup = """
-!!!
%html
    %head
        -with title as "Real.Titel"
            %title= title
    %body
        %h1= title
"""
        expected = '<!DOCTYPE html>\n\n<html>\n    <head>\n        <title>Real.Titel</title>\n    </head> \n    <body>\n        <h1>Titel</h1>\n    </body>\n</html>'
        rendered = ''.join(self.template.render(markup, context))
        self.assertEqual(rendered, expected)

    def test_indent_placeholder(self):
        rendered = ''.join(
                        Template.load_and_render(
                           'placeholder_indentation.pyml',
                           context=dict(),
                           search_path=os.path.join(os.path.dirname(__file__)) )
                        )

        expected = '\n<a href="#top">back to top</a>\n<div class="foo" />'

        self.assertEqual(expected, rendered)

if __name__ == "__main__":
    unittest.main()
