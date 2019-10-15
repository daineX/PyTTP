from ast import parse, NodeVisitor
from inspect import getsource
from textwrap import dedent


class JSVisitor(NodeVisitor):

    CONSTANTS = {
        False: "false",
        True: "true",
        None: "undefined",
    }

    def __init__(self):
        self.result = []
        self.found_outer_func = False

    def generic_visit(self, node):
        raise NotImplementedError()

    def visit_Module(self, node):
        return super().generic_visit(node)

    def visit_NameConstant(self, node):
        return self.CONSTANTS[node.value]

    def visit_FunctionDef(self, node):
        have_outer_func = self.found_outer_func
        self.found_outer_func = True
        if have_outer_func:
            self.result.append(f"function {node.name} (")
            args = []
            for arg in node.args.args:
                args.append(arg.arg)
            self.result.append(', '.join(args))
            self.result.append(") {")
        for child in node.body:
            self.visit(child)
        if have_outer_func:
            self.result.append("}")
            for decorator in node.decorator_list:
                call = self.visit(decorator)
                if call.endswith(")"):
                    call = call[:-1]
                    self.result.append(f"{node.name} = {call}, {node.name});")
                else:
                    self.result.append(f"{node.name} = {call}({node.name});")

    def visit_Assign(self, node):
        value = self.visit(node.value)
        for target in node.targets:
            self.result.append(f"{target.id} = {value};")

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

    def visit_Gt(self, node):
        return ">"

    def visit_GtE(self, node):
        return ">="

    def visit_Lt(self, node):
        return "<"

    def visit_Lt(self, node):
        return "<="

    def visit_Compare(self, node):
        comps = [self.visit(c) for c in node.comparators]
        left = self.visit(node.left)
        ops = [self.visit(op) for op in node.ops]
        compOps = ' '.join(sum(zip(ops, comps), ()))
        return f"{left} {compOps}"

    def visit_If(self, node):
        t = self.visit(node.test)
        self.result.append(f"if ({t}) {{")
        for child in node.body:
            self.visit(child)
        self.result.append("}")
        if node.orelse:
            self.result.append(" else ")
            if len(node.orelse) > 1:
                self.result.append("{")
            for orelse in node.orelse:
                self.visit(orelse)
            if len(node.orelse) > 1:
                self.result.append("}")

    def visit_Add(self, node):
        return "+"

    def visit_Sub(self, node):
        return "-"

    def visit_MatMult(self, node):
        return "var"

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

    def toJS(self):
        return ''.join(self.result)


def toJS(func):
    tree = parse(dedent(getsource(func)))
    visitor = JSVisitor()
    visitor.visit(tree)
    return visitor.toJS()


if __name__ == "__main__":

    def toCompile():
        def anonymous(jq):
            foo = jq(".foo")

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
    print(toJS(toCompile))
