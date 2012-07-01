import os

from .template_node import Node, EvalNode, TagNode, TextNode
from .template_execution_node import ExecutionNodeRegistry

from .config import global_config



class Template(object):

    GLOBAL_SEARCH_PATH = None


    def __init__(self, search_path=None):
        if search_path:
            self.search_path = search_path
        else:
            self.search_path = global_config.getValue("TEMPLATE_SEARCH_PATH")
        if not self.search_path:
            self.search_path = GLOBAL_SEARCH_PATH

    class ParseError(Exception):
        pass

    TAB_INDENT = 4


    def is_comment(self, line):
        return line.strip().startswith('//')


    def is_tag(self, line):
        return line.strip().startswith('%')


    def is_exec_node(self, line):
        return line.strip().startswith('-')


    def is_eval_node(self, line):
        return line.strip().startswith('=')


    def is_value_insert(self, line):
        return line.startswith('=')


    def handle_div(self, line):
        if line.startswith(".") or line.startswith("#"):
            return "%div" + line
        else:
            return line


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
            if self.is_comment(line):
                continue

            stripped_line, indent = self.indentation_depth(line)
            stripped_line = self.handle_div(stripped_line)

            if not stripped_line:
                continue

            for closed_node, closed_indent in reversed(tag_stack):
                if closed_indent >= indent:
                    tag_stack.pop()

            closed_node, closed_indent = tag_stack[-1]

            if self.is_tag(stripped_line):
                node = TagNode(stripped_line, closed_node)
            elif self.is_exec_node(stripped_line):
                prefix = stripped_line.split(' ')[0][1:]
                node = ExecutionNodeRegistry.get_node_cls(prefix)(stripped_line, closed_node)
            elif self.is_eval_node(stripped_line):
                node = EvalNode(stripped_line, closed_node)
            else:
                node = TextNode(stripped_line, closed_node)

            if node.is_tag or node.is_exec_node:
                tag_stack.append((node, indent))

        root_node, root_indent = tag_stack[0]
        yield root_node.render(context, base_indent)

