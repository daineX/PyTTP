from ast import parse, NodeVisitor
from inspect import getsource
from textwrap import dedent


class JSVisitor(NodeVisitor):
    
    def __init__(self):
        self.result = []
        self.found_outer_func = False
    
    def visit_FunctionDef(self, node):
        have_outer_func = self.found_outer_func
        self.found_outer_func = True
        if have_outer_func:
            self.result.append(f"function {node.name} {{")
        for child in node.body:
            self.visit(child)
        if have_outer_func:
            self.result.append("}") 
            for decorator in node.decorator_list:
                call = self.visit(decorator)[:-1]
                self.result.append(f"{node.name} = {call}, {node.name});")
    
    def visit_Assign(self, node):
        value = self.visit(node.value)
        for target in node.targets:
            self.result.append(f"{target.id} = {value};")
    
    def visit_Str(self, node):
        return f'"{node.s}"'
    
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
            bar = "blub"
            foo = jq(".foo")
            @foo.on('click')
            def trigger(this):
                el = jq(this)
                jq(".text").text("triggered")
        
        anonymous(window.jQuery)
    print(toJS(toCompile))
