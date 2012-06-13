from .template_node import Node



class ExecutionNode(Node):

    PREFIX = None

    def __init__(self, line):
        super(ExecutionNode, self).__init__(line)


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


class IfNode(ExecutionNode):

    PREFIX = 'if'


    def __init__(self, line):
        super(IfNode, self).__init__(line)

        self.condition = self.line.split(' ', 1)[1]

    def render(self, context, indent):
        if(self.eval_code(context, self.condition)):
            return super(ExecutionNode, self).render(context, indent)
        else:
            return ''

ExecutionNodeRegistry.register(IfNode)


class ForNode(ExecutionNode):

    PREFIX = 'for'

    def __init__(self, line):
        super(ForNode, self).__init__(line)

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

ExecutionNodeRegistry.register(ForNode)
