from ast import ClassDef, parse, Module, NodeVisitor
import ast
from inspect import getsource
from textwrap import dedent


__all__ = ['toJS']

class RootSentinel:

    def __repr__(self):
        return "Root"

OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "/",
    ast.Mod: "%",
    ast.And: "&&",
    ast.BitAnd: "&",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.Eq: "===",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.NotEq: "!==",
    ast.Not: "!",
    ast.Invert: "~",
    ast.Pass: ";",
    ast.Or: "||",

    # Use @= to mark variables as local.
    ast.MatMult: "var",
}

class JSVisitor(NodeVisitor):

    ROOT = RootSentinel()

    CONSTANTS = {
        False: "false",
        True: "true",
        None: "undefined",
    }

    def __init__(self, debug=False):
        self.result = []
        self.ctx_stack = [self.ROOT]
        self.debug = debug

    @property
    def context(self):
        return self.ctx_stack[-1]

    def generic_visit(self, node):
        node_type = type(node)
        if node_type in OPS:
            return OPS[node_type]
        raise NotImplementedError(type(node).__name__)

    def visit(self, node):
        if self.debug:
            print(node, self.ctx_stack)
        return super().visit(node)

    def decorate(self, node):
        for decorator in node.decorator_list:
            call = self.visit(decorator)
            if call.endswith(")"):
                call = call[:-1]
                self.result.append(f"{node.name} = {call}, {node.name});")
            else:
                self.result.append(f"{node.name} = {call}({node.name});")

    def iterate(self, node):
        self.ctx_stack.append(type(node))
        for child in node.body:
            self.visit(child)
        self.ctx_stack.pop()

    def visit_ClassDef(self, node):
        self.result.append(f"class {node.name}")
        if node.bases:
            if len(node.bases) > 1:
                raise NotImplementedError("Classes cannot have more than one base.")
            base = self.visit(node.bases[0])
            self.result.append(f" extends {base}")
        self.result.append(" {")
        self.iterate(node)
        self.result.append("}")
        self.decorate(node)

    def visit_Module(self, node):
        return super().generic_visit(node)

    def visit_NameConstant(self, node):
        return self.CONSTANTS[node.value]

    def visit_FunctionDef(self, node):
        if self.context is not ClassDef:
            self.result.append("function ")
        self.result.append(f"{node.name} (")
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        self.result.append(', '.join(args))
        self.result.append(") {")
        self.iterate(node)
        self.result.append("}")
        self.decorate(node)

    def visit_Assign(self, node):
        v = self.visit(node.value)
        for target in node.targets:
            t = self.visit(target)
            self.result.append(f"{t} = {v};")

    def visit_AugAssign(self, node):
        value = self.visit(node.value)
        op = self.visit(node.op)
        if op == "var":
            self.result.append(f"var {node.target.id} = {value};")
        else:
            self.result.append(f"{node.target.id} {op}= {value};")

    def visit_BinOp(self, node):
        right = self.visit(node.right)
        op = self.visit(node.op)
        left = self.visit(node.left)
        return f"{left} {op} {right}"

    def visit_UnaryOp(self, node):
        op = self.visit(node.op)
        operand = self.visit(node.operand)
        return f"{op} {operand}"

    def visit_Compare(self, node):
        comps = [self.visit(c) for c in node.comparators]
        left = self.visit(node.left)
        ops = [self.visit(op) for op in node.ops]
        compOps = ' '.join(sum(zip(ops, comps), ()))
        return f"{left} {compOps}"

    def visit_If(self, node):
        t = self.visit(node.test)
        self.result.append(f"if ({t}) {{")
        self.iterate(node)
        self.result.append("}")
        if node.orelse:
            self.result.append(" else ")
            if len(node.orelse) > 1:
                self.result.append("{")
            for orelse in node.orelse:
                self.visit(orelse)
            if len(node.orelse) > 1:
                self.result.append("}")

    def visit_Dict(self, node):
        items = []
        for key, value in zip(node.keys, node.values):
            key = self.visit(key)
            value = self.visit(value)
            items.append(f"{key}: {value}")
        items = ','.join(items)
        return ''.join(["{", items, "}"])

    def visit_Str(self, node):
        return f'"{node.s}"'

    def visit_Num(self, node):
        return str(node.n)

    def visit_Name(self, node):
        return node.id

    def visit_Attribute(self, node):
        return self.visit(node.value) + "." + node.attr

    def visit_Call(self, node):
        result = []
        result.append(self.visit(node.func))
        result.append("(")
        result.append(', '.join(
            self.visit(arg) for arg in node.args
        ))
        result.append(")");
        return ''.join(result)

    def visit_Expr(self, node):
        self.result.append(self.visit(node.value))
        self.result.append(";")

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Subscript(self, node):
        v = self.visit(node.value)
        s = self.visit(node.slice)
        return f"{v}[{s}]"

    def visit_Load(self, node):
        return ""

    def visit_Return(self, node):
        if node.value is None:
            self.result.append("return;")
        else:
            v = self.visit(node.value)
            self.result.append(f"return {v};")

    def visit_List(self, node):
        elems = ", ".join(self.visit(e) for e in node.elts)
        return f"[{elems}]"

    def visit_For(self, node):
        if node.orelse:
            raise NotImplementedError("for: else: is not supported.")
        target = self.visit(node.target)
        it = self.visit(node.iter)
        self.result.append(f"for ({target} in {it}) {{")
        self.iterate(node)
        self.result.append("}")

    def visit_While(self, node):
        if node.orelse:
            raise NotImplementedError("while: else: is not supported.")
        test = self.visit(node.test)
        self.result.append(f"while ({test}) {{")
        self.iterate(node)
        self.result.append("}")

    def visit_Break(self, node):
        self.result.append("break;")

    def visit_Continue(self, node):
        self.result.append("continue;")

    def toJS(self):
        return ''.join(self.result)


def environment():

    def bool(obj):
        return not not obj


def treeFromObj(obj):
    return parse(dedent(getsource(obj)))

def toJS(*objs, debug=False):
    body = []
    body.extend(treeFromObj(environment).body[0].body)
    for obj in objs:
        body.extend(treeFromObj(obj).body)
    tree = Module(body=body)
    visitor = JSVisitor(debug=debug)
    visitor.visit(tree)
    return visitor.toJS()


if __name__ == "__main__":

    def toCompile():

        class Foo(object):

            def constructor(a):
                this.a = a

            def bar():
                return this.a

        myList @= [1, 2, 3]
        for i in myList:
            jq(".foo").text(i)
            if i > 1:
                break

        idx @= 0
        while idx < 3:
            idx += 1
            continue

        bool(2)

        def anonymous(jq):
            foo = Foo(1, {"foo": "bar"})

            @foo.on('click')
            def trigger():
                el = jq(this)
                jq(".text").text(1)

            @jq.each({"foo": "bar"})
            def it(key, value):
                jq(".buttons").append(
                    jq("<input type='button' value='" + value + "'>")
                )

        anonymous(window.jQuery)
    print(toJS(toCompile, debug=True))
