from ast import (
    ClassDef,
    Expr,
    FunctionDef,
    Module,
    Name,
    If,
    NameConstant,
    NodeTransformer,
    NodeVisitor,
    parse,
    Yield,
    YieldFrom,
)
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
    # Use **= to use "new" operator.
    ast.Pow: "new"
}

def make_name_transformer(mapping):

    class _NameTransformer(NodeTransformer):

        def visit_Name(self, node):
            for name, replacement in mapping.items():
                if node.id == name:
                    return replacement
            else:
                return node

    return _NameTransformer().visit

def make_constant(const):
    return NameConstant(value=const)


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

    def visit_Import(self, node):
        return ""

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

    def visit_arguments(self, node):
        args = []
        for arg in node.args:
            args.append(arg.arg)
        if node.vararg:
            args.append("..." + node.vararg.arg)
        return ', '.join(args)

    def find_node(self, node, node_types):
        t = type(node)
        if t in node_types:
            return True
        if hasattr(node, "body"):
            return any(self.find_node(child, node_types) for child in node.body)
        if t is Expr:
            return self.find_node(node.value, node_types)
        return False

    def is_generator_function(self, node):
        if type(node) is not FunctionDef:
            return False
        return self.find_node(node, {Yield, YieldFrom})

    def visit_FunctionDef(self, node):
        if self.context is not ClassDef:
            if self.is_generator_function(node):
                self.result.append("function* ")
            else:
                self.result.append("function ")
        self.result.append(f"{node.name} (")
        self.result.append(self.visit(node.args))
        self.result.append(") {")
        self.iterate(node)
        self.result.append("}")
        self.decorate(node)

    def visit_Assign(self, node):
        v = self.visit(node.value)
        for target in node.targets:
            t = self.visit(target)
            self.result.append(f"{t} = {v};")

    visit_AnnAssign = visit_Assign

    def visit_AugAssign(self, node):
        value = self.visit(node.value)
        op = self.visit(node.op)
        if op == "var":
            self.result.append(f"var {node.target.id} = {value};")
        elif op == "new":
            self.result.append(f"{node.target.id} = new {value};")
        else:
            self.result.append(f"{node.target.id} {op}= {value};")

    def visit_BinOp(self, node):
        right = self.visit(node.right)
        op = self.visit(node.op)
        left = self.visit(node.left)
        return f"{left} {op} {right}"

    def visit_BoolOp(self, node):
        left, right = node.values
        left = self.visit(left)
        op = self.visit(node.op)
        right = self.visit(right)
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

    def visit_Yield(self, node):
        if node.value is None:
            return "yield"
        else:
            v = self.visit(node.value)
            return f"yield {v}"

    def visit_YieldFrom(self, node):
        v = self.visit(node.value)
        return f"for (let yieldVar of {v}) yield yieldVar"

    def visit_List(self, node):
        elems = ", ".join(self.visit(e) for e in node.elts)
        return f"[{elems}]"

    visit_Tuple = visit_List

    def visit_ListComp(self, node):
        gen = node.generators[0]
        if len(node.generators) > 1 or len(gen.ifs) > 1:
            raise NotImplementedError("Multi-dimensional list comprehensions are not supported.")

        def __listComp__(it):
            r @= []
            for __target__ in it:
                if __pred__:
                    r.push(__elem__)
            return r

        transform = make_name_transformer({
            "__elem__": node.elt,
            "__target__": gen.target,
            "__pred__": gen.ifs[0] if gen.ifs else make_constant(True),
        })

        r = toJS(__listComp__, transform=transform, include_env=False, debug=self.debug)
        return "({})({})".format(r, self.visit(gen.iter))

    def visit_For(self, node):
        if node.orelse:
            raise NotImplementedError("for: else: is not supported.")
        target = self.visit(node.target)
        it = self.visit(node.iter)
        self.result.append(f"for ({target} of {it}) {{")
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

    def visit_Starred(self, node):
        v = self.visit(node.value)
        return f"...{v}"

    def visit_Lambda(self, node):
        args = self.visit(node.args)
        body = self.visit(node.body)
        return f"(({args}) => {{return {body}}})"

    def toJS(self):
        if self.debug:
            print(self.result)
        return ''.join(self.result)


def environment():

    def bool(obj):
        return not not obj

    def int(obj):
        return obj - 0

    def float(obj):
        return obj - 0.0

    def str(obj):
        return obj + ""

    def select(selectors):
        return document.querySelector(selectors)

    def selectAll(selectors):
        return document.querySelectorAll(selectors)

    Element.prototype.selectAll = Element.prototype.querySelectorAll

    def on(eventName, callback, *args):

        def encapsulated(event):
            return callback(event.target, event)

        this.addEventListener(eventName, encapsulated, *args)
        return this

    Element.prototype.on = on

    def trigger(eventName):
        event **= Event(eventName)
        this.dispatchEvent(event)
    Element.prototype.trigger = trigger

    def objectItems(obj):
        for key, value in Object.entries(obj):
            yield key, value

def treeFromObj(obj):
    return parse(dedent(getsource(obj)))

def toJS(*objs, transform=None, include_env=True, debug=False):
    body = []
    if include_env:
        body.extend(treeFromObj(environment).body[0].body)
    for obj in objs:
        body.extend(treeFromObj(obj).body)
    tree = Module(body=body)
    if transform:
        tree = transform(tree)
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

        for x in Object.keys({"foo": "bar"}):
            x

        def gen(it):
            for x in it:
                yield x + 1
            yield from it

        g = gen([1, 2, 3])
        for x in g:
            console.log(x)

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
        a, b = 2, 3

        c = [x + 2 for x in [1, 2, 3] if x % 2 == 1]
        d = [x * 2 for x in c]

        def p(*args):
            console.log(*args)
        p(a, b, c)

        (lambda x: x + 1)(2)

        foo = sep or ' '

    print(toJS(toCompile, debug=True))
