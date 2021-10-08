class Rule:

    PREFIX_SPACING = " "

    def __init__(self, selector, *sub_rules_args, sub_rules=None, **declarations):
        self.selector = selector.strip()
        self.sub_rules = list(sub_rules_args)
        if sub_rules is not None:
            self.sub_rules.extend(sub_rules)
        self.declarations = declarations

    def format_head(self, selector_prefix="", decl_joiner=" ", line_joiner="\n"):
        if selector_prefix:
            return f"{selector_prefix}{self.PREFIX_SPACING}{self.selector}{decl_joiner}{{{line_joiner}"
        else:
            return f"{self.selector}{decl_joiner}{{{line_joiner}"

    def format(self, selector_prefix="", extra_declarations=None, pretty=False):
        if pretty:
            line_joiner = "\n"
            decl_joiner = " "
        else:
            line_joiner = ""
            decl_joiner = ""
        if extra_declarations is not None:
            declarations = extra_declarations.copy()
        else:
            declarations = {}
        declarations.update(self.declarations)

        if self.selector:
            head = self.format_head(
                selector_prefix=selector_prefix,
                decl_joiner=decl_joiner,
                line_joiner=line_joiner)
            tail = f"}}{line_joiner}"
        else:
            head = tail = ""

        formatted_declarations = []
        for property_name, value in declarations.items():
            property_name = property_name.replace("_", "-")
            formatted_declarations.append(
                f"{decl_joiner}{decl_joiner}{property_name}:{decl_joiner}{value};{line_joiner}"
            )

        output = []
        output.append("{}{}{}".format(head, ''.join(formatted_declarations), tail))

        for sub_selector in self.selector.split(","):
            for sub_rule in self.sub_rules:
                output.append(sub_rule.format(
                    selector_prefix=f"{selector_prefix} {sub_selector}".strip(),
                    extra_declarations=self.declarations,
                    pretty=pretty))
        return line_joiner.join(output)

    def __str__(self):
        return self.format()


class AugmentingRule(Rule):

    PREFIX_SPACING = ""

class Ruleset(Rule):

    def __init__(self, *rules):
        self.rules = list(rules)
        super().__init__("", sub_rules=rules)

    def __add__(self, ruleset_or_rule):
        rules = self.rules[:]
        if isinstance(ruleset_or_rule, Ruleset):
            rules.extend(ruleset_or_rule.rules)
        else:
            rules.append(ruleset_or_rule)
        return type(self)(*rules)

    def __str__(self):
        return self.format()

r = Rule
ar = AugmentingRule
rs = Ruleset

if __name__ == "__main__":

    ruleset = rs(
        r(".foobar, table > tr",
            border_color="#f00baa",
            border_width="2px",
            _moz_transform="translateY(10%)",
            __wide_border="3px",
            sub_rules=[
                r("td", r("span", font_weight=400), border_color="#baaf00"),
                ar(".wide", border_width="var(--wide-border)"),
            ]
        ),
        r("h1", font_weight=900),
    )

    ruleset += r("h2", font_style="italic")

    print(ruleset)
    print(ruleset.format(pretty=True))
