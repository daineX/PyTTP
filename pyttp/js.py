import ast
from inspect import getsource
import json
from textwrap import dedent

__all__ = ['toJS']

class RootSentinel:

    def __repr__(self):
        return "Root"

OPS = {
    ast.Add: "+",
    ast.UAdd: "+",
    ast.Sub: "-",
    ast.USub: "-",
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
}

def make_name_transformer(mapping):

    class _NameTransformer(ast.NodeTransformer):

        def visit_Name(self, node):
            replacement = mapping.get(node.id)
            if replacement is not None:
                return replacement
            else:
                return node

    return _NameTransformer().visit

def make_constant(const):
    return ast.NameConstant(value=const)


class JSVisitor(ast.NodeVisitor):

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

    def emit(self, value):
        self.result.append(value)

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
            dec = self.visit(decorator)
            self.emit(f"{node.name} = {dec}({node.name});")

    def iterate_body(self, node, body):
        self.emit("\n")
        self.ctx_stack.append(type(node))
        for child in body:
            self.visit(child)
        self.ctx_stack.pop()
        self.emit("\n")

    def iterate(self, node):
        self.iterate_body(node, node.body)

    def visit_Import(self, node):
        return ""

    def visit_ClassDef(self, node):
        self.emit(f"class {node.name}")
        if node.bases:
            if len(node.bases) > 1:
                raise NotImplementedError("Classes cannot have more than one base.")
            base = self.visit(node.bases[0])
            self.emit(f" extends {base}")
        self.emit(" {")
        self.iterate(node)
        self.emit("}\n")
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

    def find_node(self, node, node_types, exclude=()):
        t = type(node)
        if t in node_types:
            return True
        if hasattr(node, "body") and t not in exclude:
            return any(self.find_node(child, node_types) for child in node.body)
        if t is ast.Expr:
            return self.find_node(node.value, node_types)
        return False

    def is_generator_function(self, node):
        if not isinstance(node, ast.FunctionDef):
            return False
        return any(self.find_node(child,
                                  {ast.Yield, ast.YieldFrom},
                                  {ast.ClassDef, ast.FunctionDef})
                   for child in node.body)

    def visit_FunctionDef(self, node):
        if self.context is not ast.ClassDef:
            self.emit("function")
        if self.is_generator_function(node):
            self.emit("*")
        if self.context is not ast.ClassDef:
            self.emit(" ")
        self.emit(f"{node.name} (")
        self.emit(self.visit(node.args))
        self.emit(") {")
        self.iterate(node)
        self.emit("}\n")
        self.decorate(node)

    def visit_Assign(self, node):
        v = self.visit(node.value)
        for target in node.targets:
            t = self.visit(target)
            self.emit(f"{t} = {v};")

    def visit_AnnAssign(self, node):
        specs = {"var", "let", "const"}
        t = self.visit(node.target)
        v = self.visit(node.value)
        annotations = {ann.strip() for ann in self.visit(node.annotation).split("|")}
        for annotation in annotations:
            if annotation in specs:
                self.emit(f"{annotation} {t}")
                break
        else:
            self.emit(t)
        self.emit(" = ")
        if "new" in annotations:
            self.emit(f"new {v};")
        else:
            self.emit(f"{v};")

    def visit_Pow(self, left, right):
        return f"Math.pow({left}, {right})"

    def visit_AugAssign(self, node):
        target = self.visit(node.target)
        value = self.visit(node.value)
        if isinstance(node.op, ast.Pow):
            op = self.visit_Pow(target, value)
            self.emit(f"{target} = {op};")
        else:
            op = self.visit(node.op)
            self.emit(f"{target} {op}= {value};")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Pow):
            return self.visit_Pow(left, right)
        else:
            op = self.visit(node.op)
            return f"({left} {op} {right})"

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
        self.emit(f"if ({t}) {{")
        self.iterate(node)
        self.emit("}")
        if node.orelse:
            self.emit(" else ")
            if len(node.orelse) > 1:
                self.emit("{")
            for orelse in node.orelse:
                self.visit(orelse)
            if len(node.orelse) > 1:
                self.emit("}")

    def visit_Dict(self, node):
        items = []
        for key, value in zip(node.keys, node.values):
            key = self.visit(key)
            value = self.visit(value)
            items.append(f"{key}: {value}")
        items = ','.join(items)
        return ''.join(["{", items, "}"])

    def visit_Str(self, node, delim='"'):
        return f'{delim}{node.s}{delim}'

    def visit_JoinedStr(self, node):
        result = []
        result.append("`")
        for value in node.values:
            if isinstance(value, ast.Str):
                result.append(self.visit_Str(value, delim=""))
            else:
                result.append(self.visit(value))
        result.append("`")
        return ''.join(result)

    def visit_FormattedValue(self, node):
        v = self.visit(node.value)
        return f"${{{v}}}"

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
        self.emit(self.visit(node.value))
        self.emit(";\n")

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        if isinstance(node.slice, ast.Slice):
            if node.slice.step:
                raise NotImplementedError("Slice steps are not supported.")
            lower = self.visit(node.slice.lower)
            upper = self.visit(node.slice.upper)
            return f"({value}).slice({lower}, {upper})"
        else:
            slice = self.visit(node.slice)
            return f"{value}[{slice}]"

    def visit_Load(self, node):
        return ""

    def visit_Return(self, node):
        if node.value is None:
            self.emit("return;")
        else:
            v = self.visit(node.value)
            self.emit(f"return {v};")

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

    def _visit_Comp(self, node, impl, mapping):
        gen = node.generators[0]
        if len(node.generators) > 1 or len(gen.ifs) > 1:
            raise NotImplementedError("Multi-dimensional comprehensions are not supported.")
        transform_mapping = mapping.copy()
        transform_mapping.update({
            "target": gen.target,
            "pred": gen.ifs[0] if gen.ifs else make_constant(True),
        })
        transform = make_name_transformer(transform_mapping)
        r = toJS(impl, transform=transform, include_env=False, debug=self.debug)
        return "({})({})".format(r, self.visit(gen.iter))

    def list_comp_impl(iterable):
        result: var = []
        for target in iterable:
            if pred:
                result.push(elem)
        return result

    def gen_expr_impl(iterable):
        for target in iterable:
            if pred:
                yield elem

    def dict_comp_impl(iterable):
        result: var = {}
        for target in iterable:
            if pred:
                result[key] = value
        return result

    def visit_ListComp(self, node):
        return self._visit_Comp(node, self.list_comp_impl, {"elem": node.elt})

    def visit_GeneratorExp(self, node):
        return self._visit_Comp(node, self.gen_expr_impl, {"elem": node.elt})

    def visit_DictComp(self, node):
        return self._visit_Comp(node, self.dict_comp_impl, {"value": node.value, "key": node.key})

    def visit_For(self, node):
        if node.orelse:
            raise NotImplementedError("for: else: is not supported.")
        target = self.visit(node.target)
        it = self.visit(node.iter)
        self.emit(f"for (var {target} of {it}) {{")
        self.iterate(node)
        self.emit("}")

    def visit_While(self, node):
        if node.orelse:
            raise NotImplementedError("while: else: is not supported.")
        test = self.visit(node.test)
        self.emit(f"while ({test}) {{")
        self.iterate(node)
        self.emit("}")

    def visit_Break(self, node):
        self.emit("break;\n")

    def visit_Continue(self, node):
        self.emit("continue;\n")

    def visit_Starred(self, node):
        v = self.visit(node.value)
        return f"...{v}"

    def visit_Lambda(self, node):
        args = self.visit(node.args)
        body = self.visit(node.body)
        return f"(({args}) => {{return {body}}})"

    def visit_Raise(self, node):
        exc = self.visit(node.exc)
        self.emit(f"throw {exc};")

    def visit_Try(self, node):
        self.emit("try {")
        self.iterate(node)
        self.emit("} catch (_exc) {")
        for handler in node.handlers:
            self.visit(handler)
        self.emit("}")
        if node.finalbody:
            self.emit("finally {")
            self.iterate_body(node, node.finalbody)
            self.emit("}")
        self.emit(";\n")

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.iterate(node)
        else:
            if isinstance(node.type, ast.Tuple):
                types = node.type.elts
            else:
                types = [node.type]
            for typ_ in types:
                t = self.visit(typ_)
                self.emit(f"if (_exc instanceof {t}) {{")
                if node.name:
                    self.emit(f"var {node.name} = _exc;")
                self.iterate(node)
            self.emit("}")

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

    def Element_on(eventName, callback):
        self = this
        def decorator(callback):
            def encapsulated(event):
                return callback(event.target, event)
            self.addEventListener(eventName, encapsulated)
            return self

        if callback != None:
            return decorator(callback)
        else:
            return decorator
    Element.prototype.on = Element_on

    def NodeListMethod(methodName):
        def decorator(func):
            def NodeList_method(*args):
                for elem in this:
                    func.bind(elem)(*args)
                return this
            NodeList.prototype[methodName] = NodeList_method
            return func
        return decorator

    @NodeListMethod("set")
    def Element_set(key, value):
        this[key] = value
        return this
    Element.prototype.set = Element_set

    @NodeListMethod("val")
    def Element_val(value):
        this.value = value
        return this
    Element.prototype.val = Element_val

    @NodeListMethod("trigger")
    def Element_trigger(eventName):
        event: new | var = Event(eventName)
        this.dispatchEvent(event)
        return this
    Element.prototype.trigger = Element_trigger

    def NodeList_on(eventName, callback):
        self = this
        def decorator(callback):
            def encapsulated(event):
                return callback(event.target, event)
            for elem in self:
                elem.addEventListener(eventName, encapsulated)
            return self
        if callback != None:
            return decorator(callback)
        else:
            return decorator
    NodeList.prototype.on = NodeList_on

    def NodeList_apply(func):
        for elem in this:
            func(elem)
        return this
    NodeList.prototype.apply = NodeList_apply

    def objectItems(obj):
        for key, value in Object.entries(obj):
            yield key, value

    def range(start, stop, step):
        if step == None:
            step = 1
        if step != 0:
            if stop == None:
                stop = start
                start = 0
            n = start
            while (step > 0 and n < stop) or (step < 0 and n > stop):
                yield n
                n += step

def treeFromObj(obj):
    return ast.parse(dedent(getsource(obj)))

def toJS(*objs, context=None, transform=None, include_env=True, debug=False):
    body = []
    if include_env:
        body.extend(treeFromObj(environment).body[0].body)
    for obj in objs:
        body.extend(treeFromObj(obj).body)
    tree = ast.Module(body=body)
    if transform:
        tree = transform(tree)
    visitor = JSVisitor(debug=debug)
    visitor.visit(tree)
    src = visitor.toJS()
    if context:
        ctx_lines = []
        for variable, value in context.items():
            ctx_lines.append("{} = {};".format(variable, json.dumps(value)));
        src = '\n'.join(ctx_lines + [src])
    return src


if __name__ == "__main__":

    def toCompile():

        class Foo(object):

            def constructor(a):
                this.a = a

            def bar():
                return this.a

        myList: var = [1, 2, 3]
        for i in myList:
            jq(".foo").text(i)
            if i > 1:
                break

        idx: var = 0
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

        c = [x + 2 for x in [1, 2, 3, 4, 5, 6] if x % 2 == 1]
        d = [x * 2 for x in c][0:-1]

        def p(*args):
            console.log(*args)
        p(a, b, c)

        (lambda x: x + 1)(2)

        foo = sep or ' '

        {a: b - 1 for a, b in objectItems({"t": 3, "h": 0})}

        (a + 2 for a in (1, 2, 3, 4) if a % 2 == 0)

        [x for x in range(10)]

        a: var = Foo()
        exc: new | var = Error("foo happened.")

        try:
            raise exc from Exception()
        except Error as e:
            e.message
        finally:
            a + b

        try:
            foo
        except:
            pass

        button: var = select(".button")

        @button.on("click")
        def on_button_click(elem):
            select(".para").textContent += "foobar"

        @button.on
        def foobar():
            pass

        a **= b
        foo = f"bar = {a ** b}"

        k = (10 + 3) % 2
        k = 10 + 3 % 2
        k = 10 * 3 + 2
        k = 10 + 3 * 2

    print(toJS(toCompile, debug=True))
