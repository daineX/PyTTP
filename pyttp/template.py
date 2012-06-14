
from .template_node import Node, EvalNode, TagNode, TextNode
from .template_execution_node import ExecutionNodeRegistry

class Template(object):

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


    def render(self, context, markup):
        tag_stack = [(Node(''), -1)]
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
            stripped_line = self.handle_div(stripped_line)

            for closed_node, closed_indent in reversed(tag_stack):
                if closed_indent >= indent:
                    tag_stack.pop()

            closed_node, closed_indent = tag_stack[-1]

            if self.is_tag(stripped_line):
                node = TagNode(stripped_line)
            elif self.is_exec_node(stripped_line):
                prefix = stripped_line.split(' ')[0][1:]
                node = ExecutionNodeRegistry.get_node_cls(prefix)(stripped_line)

                #special treatment for ElseNode
                if node.PREFIX == 'else': 
                    node.parent_hook(closed_node)

            elif self.is_eval_node(stripped_line):
                node = EvalNode(stripped_line)
            else:
                node = TextNode(stripped_line)

            closed_node.add_child(node)

            if node.is_tag or node.is_exec_node:
                tag_stack.append((node, indent))

        root_node, root_indent = tag_stack[0]
        yield root_node.render(context, 0)

