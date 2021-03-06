import os

from .settings import get_settings
from .template_execution_node import ExecutionNodeRegistry, PreNode
from .template_node import (
    CommentNode,
    EvalNode,
    Node,
    TagNode,
    TextNode,
    UnescapedEvalNode,
)

settings = get_settings()

PREFIX_TO_NODE = {
    '//': CommentNode,
    '%': TagNode,
    '#': TagNode,
    '.': TagNode,
    '-': ExecutionNodeRegistry.get_node,
    '==': UnescapedEvalNode,
    '=': EvalNode,
}

class Template(object):

    GLOBAL_SEARCH_PATH = None


    def __init__(self, search_path=None):
        if search_path:
            self.search_path = search_path
        else:
            try:
                self.search_path = settings.TEMPLATE_SEARCH_PATH
            except AttributeError:
                self.search_path = None
        if not self.search_path:
            self.search_path = self.GLOBAL_SEARCH_PATH

        try:
            self.context_processors = settings.TEMPLATE_CONTEXT_PROCESSORS
        except AttributeError:
            self.context_processors = []

    class ParseError(Exception):
        pass

    TAB_INDENT = 4


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


    def load(self, f):
        if self.search_path:
                return open(os.path.join(self.search_path, f)).read()
        else:
            return open(f).read()


    @classmethod
    def load_and_render(cls, f, context=None, base_indent=0, search_path=None):
        template = cls(search_path)
        markup = template.load(f)
        return template.render(markup, context, base_indent)


    def _fill_placeholder(self, name, indent, placeholders):
        new_lines = []
        for placeholder_line in placeholders[name]:
            if placeholder_line.lstrip().startswith("-placeholder"):
                _, placeholder_name = placeholder_line.lstrip().split(' ', 1)
                _, placeholder_indent = self.indentation_depth(placeholder_line)
                new_lines += self._fill_placeholder(placeholder_name, placeholder_indent + indent - self.TAB_INDENT, placeholders)
            else:
                new_lines.append((' '*indent) + placeholder_line[self.TAB_INDENT:])
        return new_lines


    def pre_process(self, markup, placeholders=None):
        lines = markup.split("\n")
        parent = None
        if lines[0].startswith("-extends "):
            _, f = lines[0].split(' ', 1)
            parent = self.load(f)

        new_lines = []
        if placeholders:
            parent_placeholders = placeholders
        else:
            parent_placeholders = {}
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.lstrip().startswith("-placeholder "):
                _, placeholder_name = line.lstrip().split(' ', 1)
                _, placeholder_indent = self.indentation_depth(line)

                if placeholders and placeholder_name in placeholders:
                    new_lines += self._fill_placeholder(placeholder_name, placeholder_indent, placeholders)
                else:
                    placeholder_content = []
                    for placeholder_line in lines[index+1:]:
                        stripped_line, indent = self.indentation_depth(placeholder_line)
                        if not stripped_line: continue
                        if  indent <= placeholder_indent:
                            break
                        placeholder_content.append(placeholder_line)
                        index += 1
                    if placeholder_content:
                        parent_placeholders[placeholder_name] = placeholder_content
            else:
                new_lines.append(line)
            index += 1
        if parent:
            new_lines = self.pre_process(parent, parent_placeholders)
        return new_lines


    def render(self, markup, context=None, base_indent=0):
        if not context:
            context = {}

        if base_indent == 0:
            # Let's assume noone will ever call render with base_indent set
            # to something different.
            for processor in self.context_processors:
                context = processor(context)

        context.update({"_TEMPLATE_SEARCH_PATH": self.search_path})
        tag_stack = [(Node(''), -1)]
        old_indent = None
        old_tag_name = None
        last_line_had_tag = False
        last_line_had_remainder = False

        pre_processed = self.pre_process(markup)
        for line in pre_processed:
            if not line:
                continue

            stripped_line, indent = self.indentation_depth(line)

            if not stripped_line:
                continue

            for closed_node, closed_indent in reversed(tag_stack):
                if closed_indent >= indent:
                    tag_stack.pop()

            closed_node, closed_indent = tag_stack[-1]

            if type(closed_node) is PreNode:
                closed_node.add_child(TextNode(line))
                continue

            for prefix, node_type in PREFIX_TO_NODE.items():
                if stripped_line.startswith(prefix):
                    break
            else:
                node_type = TextNode
            node = node_type(stripped_line, closed_node)

            if node.is_tag or node.is_exec_node:
                tag_stack.append((node, indent))

        root_node, root_indent = tag_stack[0]
        yield root_node.render(context, base_indent)


def render_string(markup, context=None):
    t = Template()
    return ''.join(t.render(markup, context=context))
