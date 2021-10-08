from collections import OrderedDict

class OrderedListDictProxy:

    def __init__(self):
        self.data = OrderedDict()

    def __getitem__(self, key):
        if key not in self.data:
            lst = []
            self.data[key] = lst
            return lst
        else:
            return self.data[key]

    def __getattr__(self, key):
        return getattr(self.data, key)


class Rule:

    PREFIX_SPACING = " "

    def __init__(self, selectors, *sub_rules_args, sub_rules=None, extra_declarations=None, **declarations):
        self.selectors = [selector.strip() for selector in selectors.split(",")]
        self.sub_rules = list(sub_rules_args)
        if sub_rules is not None:
            self.sub_rules.extend(sub_rules)
        self.declarations = declarations
        if extra_declarations is not None:
            self.declarations.update(extra_declarations)

    def collect(
        self,
        selector_prefix="",
        extra_declarations=None,
        decl_joiner=" ",
        line_joiner="\n",
        normalized_rules=None
    ):
        if normalized_rules is None:
            normalized_rules = OrderedListDictProxy()
        if extra_declarations is not None:
            declarations = extra_declarations.copy()
        else:
            declarations = {}
        declarations.update(self.declarations)
        formatted_declarations = []
        for property_name, value in declarations.items():
            property_name = property_name.replace("_", "-")
            formatted_declarations.append(
                f"{decl_joiner}{decl_joiner}{property_name}:{decl_joiner}{value};{line_joiner}"
            )
        decl = ''.join(formatted_declarations)
        sub_rules = []
        for sub_selector in self.selectors:
            sub_selector = f"{selector_prefix}{self.PREFIX_SPACING}{sub_selector}".strip()
            if sub_selector:
                normalized_rules[decl].append(sub_selector)
            for sub_rule in self.sub_rules:
                sub_rules.append((sub_rule, sub_selector, declarations))
        for sub_rule, sub_selector, declarations in sub_rules:
            sub_normalized_rules = sub_rule.collect(
                selector_prefix=sub_selector,
                extra_declarations=declarations,
                decl_joiner=decl_joiner,
                line_joiner=line_joiner,
                normalized_rules=normalized_rules,
            )
        return normalized_rules

    def format_head(self, selectors, selector_prefix="", decl_joiner=" ", line_joiner="\n"):
        return "{selectors}{decl_joiner}{{{line_joiner}".format(
            selectors=(',' + line_joiner).join(selectors),
            decl_joiner=decl_joiner,
            line_joiner=line_joiner,
        )

    def format_block(self, selectors, declarations, selector_prefix="", decl_joiner=" ", line_joiner="\n"):
        if selectors:
            head = self.format_head(
                selectors,
                selector_prefix=selector_prefix,
                decl_joiner=decl_joiner,
                line_joiner=line_joiner)
            tail = f"}}{line_joiner}"
        else:
            head = tail = ""
        return "{}{}{}".format(head, declarations, tail)

    def format(self, selector_prefix="", extra_declarations=None, pretty=False):
        if pretty:
            line_joiner = "\n"
            decl_joiner = " "
        else:
            line_joiner = ""
            decl_joiner = ""
        normalized_rules = self.collect(
            selector_prefix=selector_prefix,
            extra_declarations=extra_declarations,
            decl_joiner=decl_joiner,
            line_joiner=line_joiner,
        )
        return line_joiner.join(
            self.format_block(
                selectors,
                declarations,
                selector_prefix=selector_prefix,
                decl_joiner=decl_joiner,
                line_joiner=line_joiner
            ) for declarations, selectors in normalized_rules.items()
        )

    def copy(self, selector):
        return type(self)(selector, sub_rules=self.sub_rules, **self.declarations)

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


r = Rule
ar = AugmentingRule
rs = Ruleset


if __name__ == "__main__":
    ruleset = rs(
        r("#body",
            r(".foo, bar",
                border_width="2px",
                sub_rules=[
                    r("span", font_weight=300),
                    ar(".wide", border_width="var(--wide-border)"),
                ]
            ),
            __wide_border="3px",
    ))
    ruleset += r("h2", font_style="italic")

    print(ruleset)
    print(ruleset.format(pretty=True))
