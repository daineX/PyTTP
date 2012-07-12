from .template_node import (
    Node,
    TAB_INDENT,
    )



class ExecutionNode(Node):

    PREFIX = None

    def __init__(self, line, parent=None):
        super(ExecutionNode, self).__init__(line, parent)


    @property
    def is_exec_node(self):
        return True

    def __repr__(self):
        return "ExecNode(%s, %s)" % (self.PREFIX, self.line)



class ExecutionNodeRegistry(object):

    REGISTRY = None

    def __init__(self):
        self.lookup = {}


    @classmethod
    def register(cls, node_cls):
        if not cls.REGISTRY:
            cls.REGISTRY = cls()
        cls.REGISTRY.lookup[node_cls.PREFIX] = node_cls

    @classmethod
    def get_node_cls(cls, prefix):
        return cls.REGISTRY.lookup[prefix]


def registered(node):
    ExecutionNodeRegistry.register(node)
    return node


@registered
class IfNode(ExecutionNode):

    PREFIX = 'if'


    def __init__(self, line, parent=None):
        super(IfNode, self).__init__(line, parent)
        self.parse_condition()

    def parse_condition(self):
        self.condition = self.line.split(' ', 1)[1]


    def render(self, context, indent):
        if self.eval_code(context, self.condition):
            return super(ExecutionNode, self).render(context, indent)
        else:
            return ''


@registered
class ElseNode(IfNode):

    PREFIX = 'else'

    def __init__(self, line, parent=None):
        ExecutionNode.__init__(self, line, parent)
        self.parse_condition(parent)

    def parse_condition(self, parent):
        for child in reversed(parent.children):
            if child.is_exec_node and child.PREFIX == IfNode.PREFIX:
                self.condition = child.condition
                break
        else:
            raise Node.ParseError("Missing if for ElseNode")


    def render(self, context, indent):
        if not self.eval_code(context, self.condition):
            return super(ExecutionNode, self).render(context, indent)
        else:
            return ''


@registered
class ForNode(ExecutionNode):

    PREFIX = 'for'

    def __init__(self, line, parent=None):
        super(ForNode, self).__init__(line, parent)

        _, self.var, in_, self.collection = self.line.split(' ', 3)
        assert(in_ == "in")


    def render(self, context, indent):
        ctx = context.copy()
        collection = self.eval_code(context, self.collection)

        res = ''
        for value in collection:
            ctx.update({self.var: value})
            res += super(ExecutionNode, self).render(ctx, indent)
        return res


@registered
class PreNode(ExecutionNode):

    PREFIX = 'pre'

    def _fetch_child_lines(self, node, indent):
        lines = []
        for child_node in node.children:
            lines.append(' '*4*indent + child_node.line)
            lines += self._fetch_child_lines(child_node, indent + 1)            
        return lines

    def render(self, context, indent):
        return '\n' + '\n'.join(self._fetch_child_lines(self, indent))


@registered
class IncludeNode(ExecutionNode):

    PREFIX = 'include'

    def render(self, context, indent):
        from .template import Template
        _, template = self.line.split(' ', 1)
        search_path = context.get("_TEMPLATE_SEARCH_PATH")
        return ''.join(Template.load_and_render(template,
                                                context,
                                                search_path=search_path,
                                                base_indent=indent))


@registered
class DoctypeNode(ExecutionNode):

    PREFIX = '!!!'

    def render(self, context, indent):
        return '<!DOCTYPE html>\n'


@registered
class WithNode(ExecutionNode):

    PREFIX = 'with'

    def __init__(self, line, parent=None):
        super(WithNode, self).__init__(line, parent)
        _, self.var, _as, self.value = self.line.split(' ', 3)
        assert "as" == _as

    def render(self, context, indent):
        ctx = context.copy()
        ctx.update({self.var: self.eval_code(context, self.value)})
        return super(WithNode, self).render(ctx, indent)


@registered
class AutoEscapeNode(WithNode):

    PREFIX = 'autoescape'

    def __init__(self, line, parent=None):
        super(WithNode, self).__init__(line, parent)        
        self.var = '_autoescape'
        self.value = 'True'
