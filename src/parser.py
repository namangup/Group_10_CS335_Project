# https://www.lysator.liu.se/c/ANSI-C-grammar-y.html
# https://github.com/dabeaz/ply/blob/master/doc/ply.md

import ply.yacc as yacc
from lexer import Lexer, error_func
import argparse
import sys
import pygraphviz as pgv
from symboltable import SymbolTable,bcolors

num_nodes = 0
graph = pgv.AGraph(strict=False, directed=True)
graph.layout(prog="circo")

def new_node():
    global num_nodes
    graph.add_node(num_nodes)
    node = graph.get_node(num_nodes)
    num_nodes += 1
    return node

def remove_node(node):
    graph.remove_node(node)

class Node:
    def __init__(self, label, children=None, create_ast=True):
        self.label = label
        self.children = []
        self.create_ast = create_ast
        self.node = None
        self.attributes = {"error": False}
        self.is_var = False
        self.extraVals = []
        self.variables = {}
        self.type = None

        if children is None:
            self.is_terminal = True
        else:
            self.is_terminal = False

        if children is not None:
            self.children = children

        if self.create_ast:
            self.make_graph()

    def make_graph(self):
        if self.is_terminal:
            self.node = new_node()
            self.node.attr["label"] = self.label
        else:
            children = []
            for child in self.children:
                if (child is not None) and (child.node is not None):
                    children.append(child)
            self.children = children
            if self.children:
                self.node = new_node()
                self.node.attr["label"] = self.label
                listNode = []
                for child in self.children:
                    graph.add_edge(self.node, child.node)
                    listNode.append(child.node)

                graph.add_subgraph(listNode, rank="same")

    def remove_graph(self):
        for child in self.children:
            if child.node:
                child.remove_graph()
        remove_node(self.node)
        self.node = None

    def addTypeInDict(self, type):
        """
        Add "data_type" to all variables in the dictionary
        """
        for key in self.variables.keys():
            self.variables[key].append(type)

    def print_val(self):
        for child in self.children:
            child.print_val()
        print(self.label)


sizes = {"int": 4, "char": 1, "short": 2, "float": 4, "ptr": 4, "bool": 1, "void": 0}

class Parser:

    tokens = Lexer.tokens
    keywords = Lexer.keywords
    precedence = (("nonassoc", "IF_STATEMENTS"), ("nonassoc", "ELSE"))

    def __init__(self):
        self.symtab = SymbolTable()
        self.ast_root = Node("AST Root")
        self.error = False

    def build(self):
        self.parser = yacc.yacc(
            module=self, start="start", outputdir="tmp", debug=args.debug
        )

    def p_start(self, p):
        """
        start : translation_unit
        """
        if self.error:
            return
        p[0] = self.ast_root
        self.symtab.store_results()

    def p_error(self, p):
        self.error = True
        position = (
            p.lexer.lexpos
            - sum(map(lambda line: len(line) + 1, p.lexer.lines[: p.lineno - 1]))
            - len(p.value)
            + 1
        )
        print(
            bcolors.BOLD + "{}:{}:".format(p.lineno, position) + bcolors.ENDC,
            end="",
            file=sys.stderr,
        )
        print(
            bcolors.FAIL + " SyntaxError: " + bcolors.ENDC,
            "Unexpected token {}".format(p.value),
            file=sys.stderr,
        )
        print(
            "     {} |{}".format(p.lineno, p.lexer.lines[p.lineno - 1][: position - 1]),
            end="",
            file=sys.stderr,
        )
        print(
            bcolors.WARNING
            + bcolors.UNDERLINE
            + "{}".format(
                p.lexer.lines[p.lineno - 1][position - 1 : position - 1 + len(p.value)]
            )
            + bcolors.ENDC
            + bcolors.ENDC,
            end="",
            file=sys.stderr,
        )
        print(
            "{}".format(p.lexer.lines[p.lineno - 1][position - 1 + len(p.value) :]),
            file=sys.stderr,
        )

    # Expressions
    def p_BoolConst(self, p):
        """BoolConst : TRUE
        | FALSE
        """
        if self.error:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["bool"]

    def p_IntegerConst(self, p):
        """IntegerConst : INTEGER_CONSTANT"""
        if self.error:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["int"]

    def p_FloatConst(self, p):
        """FloatConst : FLOAT_CONSTANT"""
        if self.error:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["float"]

    def p_CharConst(self, p):
        """CharConst : CHAR_CONSTANT"""
        if self.error:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["char"]

    def p_primary_expression(self, p):
        """
        primary_expression : IDENTIFIER
                        | IntegerConst
                        | FloatConst
                        | CharConst
                        | BoolConst
                        | STRING_CONSTANT
                        | '(' expression ')'
        """
        if self.error:
            return

        if p.slice[1].type == "IDENTIFIER":
            found, entry = self.symtab.return_sym_tab_entry(p[1]["lexeme"], p.lineno(1))
            if found:
                if "data_type" not in entry.keys():
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Use of self referencing variables  isn't allowed at line No "
                        + str(p.lineno(1))+bcolors.ENDC
                    )
                    return
                if entry["identifier_type"] == "function":
                    p[0] = Node(str(p[1]["lexeme"]))
                    p[0].type = []
                    p[0].type.append("func")
                    p[0].ret_type = entry["data_type"]
                    p[0].parameter_nums = entry["num_parameters"]
                    p[0].parameters = []

                    for var in entry["scope"][0]:
                        if var == "struct_or_union":
                            p[0].structorunion = entry["scope"][0][var]
                            continue
                        if var == "scope":
                            continue

                        if entry["scope"][0][var]["identifier_type"] == "parameter":
                            p[0].parameters.append(entry["scope"][0][var])
                    return

                isArr = 0

                for i in range(len(entry["data_type"])):
                    if entry["data_type"][i][0] == "[" and entry["data_type"][i][-1] == "]":
                        isArr += 1

                p[0] = Node(str(p[1]["lexeme"]))
                type_list = entry["data_type"]

                if entry["identifier_type"] == "variable" or entry["identifier_type"] == "parameter":
                    p[0].is_var = 1

                p[0].type = []

                if "int" in type_list:
                    p[0].type.append("int")
                    for single_type in type_list:
                        if single_type != "int":
                            p[0].type.append(single_type)

                elif "short" in type_list:
                    p[0].type.append("short")
                    for single_type in type_list:
                        if single_type != "short":
                            p[0].type.append(single_type)

                elif "char" in type_list:
                    p[0].type.append("char")
                    for single_type in type_list:
                        if single_type != "char":
                            p[0].type.append(single_type)

                elif "bool" in type_list:
                    p[0].type.append("bool")
                    for single_type in type_list:
                        if single_type != "bool":
                            p[0].type.append(single_type)

                elif "str" in type_list:
                    p[0].type.append("str")
                    for single_type in type_list:
                        if single_type != "str":
                            p[0].type.append(single_type)

                elif "float" in type_list:
                    p[0].type.append("float")
                    for single_type in type_list:
                        if single_type != "float":
                            p[0].type.append(single_type)

                if isArr > 0:
                    temp_type = []
                    temp_type.append(p[0].type[0] + " ")
                    for i in range(isArr):
                        temp_type[0] += "*"

                    for i in range(len(p[0].type)):
                        if i > isArr:
                            temp_type.append(p[0].type[i])
                    p[0].type = temp_type
                    p[0].type.append("arr")

                if "struct" in type_list:
                    p[0].type.append("struct")
                    for single_type in type_list:
                        if single_type != "struct":
                            p[0].type.append(single_type)

                if "union" in type_list:
                    p[0].type.append("union")
                    for single_type in type_list:
                        if single_type != "union":
                            p[0].type.append(single_type)

                if "*" in type_list:
                    temp_type = []
                    temp_type.append(p[0].type[0] + " *")
                    for i in range(len(p[0].type)):
                        if i >= 2:
                            if p[0].type[i] == "*":
                                temp_type[0] += "*"
                            else:
                                temp_type.append(p[0].type[i])
                    p[0].type = temp_type

                if "struct" in p[0].type or "union" in p[0].type:
                    p[0].vars = entry["vars"]

                elif "struct *" in p[0].type or "union *" in p[0].type:
                    p[0].vars = entry["vars"]

                elif p[0].type and (
                    "struct" in p[0].type[0] or "union" in p[0].type[0]
                ):
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Multilevel pointer for structures/unions not allowed at line"
                        + str(p.lineno(1))+bcolors.ENDC
                    )

        elif str(p.slice[1])[-5:] == "Const":
            p[0] = p[1]
        elif p.slice[1].type == "STRING_CONSTANT":
            p[0] = Node(str(p[1]))
            p[0].type = ["str"]
        elif len(p) == 4:
            p[0] = p[2]

    def p_postfix_expression(self, p):
        """
        postfix_expression : primary_expression
                        | postfix_expression '[' expression ']'
                        | postfix_expression '(' ')'
                        | postfix_expression '(' argument_expression_list ')'
                        | postfix_expression '.' IDENTIFIER
                        | postfix_expression PTR_OP IDENTIFIER
                        | postfix_expression INC_OP
                        | postfix_expression DEC_OP
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 3:
            if p[1].type is None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to increment/decrement the expression at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            elif p[1].type[0] not in ["char", "short", "int"]:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to increment/decrement "
                    + str(p[1].type[0])
                    + " type expression at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            elif not p[1].is_terminal:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to increment/decrement the expression at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            elif not p[1].is_var:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to increment/decrement the expression at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            else:
                p[0] = Node("Postfix" + str(p[2]), children=[p[1]])
                if p[1].type[0] in ["char", "short"]:
                    p[0].type = ["int"]
                    p[0].type += p[1].type[1:]
                    p[1].totype = p[0].type
                else:
                    p[0].type = p[1].type

        elif len(p) == 4:
            if p[2] == ".":
                p3val = p[3]["lexeme"]
                p[3] = Node(str(p3val))
                p[0] = Node(".", children=[p[1], p[3]])
                if "struct" not in p[1].type and "union" not in p[1].type:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Requested an invalid member of object that isn't a structure/union at Line No.: "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                elif p3val not in p[1].vars:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Requested an invalid member of object that doesn't belong to the structure/union at Line No.: "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                else:
                    old_type_list = p[1].vars[p3val]["data_type"]
                    narr = 0
                    for i in range(len(old_type_list)):
                        if old_type_list[i][0] == "[" and old_type_list[i][-1] == "]":
                            narr += 1

                    type_list = old_type_list

                    p[0].type = []

                    if "int" in type_list:
                        p[0].type.append("int")
                        for single_type in type_list:
                            if single_type != "int":
                                p[0].type.append(single_type)

                    elif "short" in type_list:
                        p[0].type.append("short")
                        for single_type in type_list:
                            if single_type != "short":
                                p[0].type.append(single_type)

                    elif "char" in type_list:
                        p[0].type.append("char")
                        for single_type in type_list:
                            if single_type != "char":
                                p[0].type.append(single_type)

                    elif "bool" in type_list:
                        p[0].type.append("bool")
                        for single_type in type_list:
                            if single_type != "bool":
                                p[0].type.append(single_type)

                    elif "str" in type_list:
                        p[0].type.append("str")
                        for single_type in type_list:
                            if single_type != "str":
                                p[0].type.append(single_type)

                    elif "float" in type_list:
                        p[0].type.append("float")
                        for single_type in type_list:
                            if single_type != "float":
                                p[0].type.append(single_type)

                    if narr > 0:
                        temp_type = []
                        temp_type.append(p[0].type[0] + " ")
                        for i in range(narr):
                            temp_type[0] += "*"

                        for i in range(len(p[0].type)):
                            if i > narr:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type
                        p[0].type.append("arr")

                    if "struct" in type_list:
                        p[0].type.append("struct")
                        for single_type in type_list:
                            if single_type != "struct":
                                p[0].type.append(single_type)

                    if "union" in type_list:
                        p[0].type.append("union")
                        for single_type in type_list:
                            if single_type != "union":
                                p[0].type.append(single_type)

                    if "*" in type_list:
                        temp_type = []
                        temp_type.append(p[0].type[0] + " *")
                        for i in range(len(p[0].type)):
                            if i >= 2:
                                if p[0].type[i] == "*":
                                    temp_type[0] += "*"
                                else:
                                    temp_type.append(p[0].type[i])
                        p[0].type = temp_type

                    if (
                        "struct" in p[0].type
                        or "struct *" in p[0].type
                        or "union" in p[0].type
                        or "union *" in p[0].type
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Use of nested structures or unions aren't allowed at Line No.: "
                            + str(p.lineno(2))+bcolors.ENDC
                        )

                    elif p[0].type and (
                        "struct" in p[0].type[0] or "union" in p[0].type[0]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Use of multilevel pointer for structures isn't allowed at Line No.: "
                            + str(p.lineno(1))+bcolors.ENDC
                        )

                    if "struct" not in p[0].type and "union" not in p[0].type:
                        p[0].is_var = True

            elif p[2] == "(":
                p[0] = Node("FuncCall", [p[1]])
                if "func" not in p[1].type:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to call non-function at Line No.: " + str(p.lineno(2))+bcolors.ENDC
                    )

                elif p[1].parameter_nums != 0:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        str(p[1].parameter_nums)
                        + " parameters are required for calling the function at Line No.:"
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                else:
                    p[0].type = p[1].ret_type

            elif p[2] == "->":
                p3val = p[3]["lexeme"]
                p[3] = Node(str(p3val))
                p[0] = Node(".", children=[p[1], p[3]])
                if "struct *" not in p[1].type and "union *" not in p[1].type:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Requested an invalid member of object which isn't a structure/union at Line No.: "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                elif p3val not in p[1].vars:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Requested an invalid member of object which doesn't belong to the structure/union at Line No.: "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                else:
                    old_type_list = p[1].vars[p3val]["data_type"]
                    narr = 0
                    for i in range(len(old_type_list)):
                        if old_type_list[i][0] == "[" and old_type_list[i][-1] == "]":
                            narr += 1

                    type_list = old_type_list

                    p[0].type = []

                    if "int" in type_list:
                        p[0].type.append("int")
                        for single_type in type_list:
                            if single_type != "int":
                                p[0].type.append(single_type)

                    elif "short" in type_list:
                        p[0].type.append("short")
                        for single_type in type_list:
                            if single_type != "short":
                                p[0].type.append(single_type)

                    elif "char" in type_list:
                        p[0].type.append("char")
                        for single_type in type_list:
                            if single_type != "char":
                                p[0].type.append(single_type)

                    elif "bool" in type_list:
                        p[0].type.append("bool")
                        for single_type in type_list:
                            if single_type != "bool":
                                p[0].type.append(single_type)

                    elif "str" in type_list:
                        p[0].type.append("str")
                        for single_type in type_list:
                            if single_type != "str":
                                p[0].type.append(single_type)

                    elif "float" in type_list:
                        p[0].type.append("float")
                        for single_type in type_list:
                            if single_type != "float":
                                p[0].type.append(single_type)

                    if narr > 0:
                        temp_type = []
                        temp_type.append(p[0].type[0] + " ")
                        for i in range(narr):
                            temp_type[0] += "*"

                        for i in range(len(p[0].type)):
                            if i > narr:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type
                        p[0].type.append("arr")

                    if "struct" in type_list:
                        p[0].type.append("struct")
                        for single_type in type_list:
                            if single_type != "struct":
                                p[0].type.append(single_type)

                    if "union" in type_list:
                        p[0].type.append("union")
                        for single_type in type_list:
                            if single_type != "union":
                                p[0].type.append(single_type)

                    if "*" in type_list:
                        temp_type = []
                        temp_type.append(p[0].type[0] + " *")
                        for i in range(len(p[0].type)):
                            if i >= 2:
                                if p[0].type[i] == "*":
                                    temp_type[0] += "*"
                                else:
                                    temp_type.append(p[0].type[i])
                        p[0].type = temp_type

                    if (
                        "struct" in p[0].type
                        or "struct *" in p[0].type
                        or "union" in p[0].type
                        or "union *" in p[0].type
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Use of nested structures/unions isn't allowed at Line No.: "
                            + str(p.lineno(2))+bcolors.ENDC
                        )

                    elif p[0].type and (
                        "struct" in p[0].type[0] or "union" in p[0].type[0]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Use of multilevel pointers for structures isn't allowed at Line No.: "
                            + str(p.lineno(1))+bcolors.ENDC
                        )

                    if "struct" not in p[0].type and "union" not in p[0].type:
                        p[0].is_var = True

        elif len(p) == 5:
            if p[2] == "(":
                p[0] = Node("FuncCall", [p[1], p[3]])

                if p[1] == None or "func" not in p[1].type:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to call non-function at Line No.: " + str(p.lineno(2))+bcolors.ENDC
                    )

                elif p[3].parameter_nums != p[1].parameter_nums:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Wrong no. of parameters (required: "
                        + str(p[1].parameter_nums)
                        + " but provided: "
                        + str(p[3].parameter_nums)
                        + " ) at Line No.: "
                        + str(p.lineno(2))
                        +bcolors.ENDC
                    )
                else:
                    ctr = -1
                    for i in p[1].parameters:

                        ctr += 1

                        if p[3].parameters == None or p[3].parameters[0] == None:
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "One or more invalid arguments provided to the call function at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return

                        if "*" in i["data_type"] and p[3].parameters[ctr][0] == "float":
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a float value to pointer at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "struct" in i["data_type"][0]
                            and "struct" not in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a non-struct value to struct object at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "struct" not in i["data_type"][0]
                            and "struct" in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a struct value to non-struct at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "struct" in i["data_type"][0]
                            and "struct" in p[3].parameters[ctr]
                            and p[3].parameters[ctr][1] not in i["data_type"]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a struct value to these objects (since incompatible) at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "union" in i["data_type"][0]
                            and "union" not in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a non-union value to object of union type at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "union" not in i["data_type"][0]
                            and "union" in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a union value to non-union type at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return
                        if (
                            "union" in i["data_type"][0]
                            and "union" in p[3].parameters[ctr]
                            and p[3].parameters[ctr][1] not in i["data_type"]
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to assign a union value to to these objects (since incompatible) at Line No.: "
                                + str(p.lineno(2))+bcolors.ENDC
                            )
                            return

                    p[0].type = p[1].ret_type

            elif p[2] == "[":

                if p[3] == None:
                    self.symtab.error = True
                    print(bcolors.FAIL+"Array subscript is invalid at Line No.: " + str(p.lineno(2))+bcolors.ENDC)
                    return

                flag = 0
                if "int" in p[3].type:
                    flag = 1
                elif "char" in p[3].type:
                    flag = 1

                if flag == 0:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Array subscript of type "
                        + str(p[3].type)
                        + " is invalid at Line No.: "
                        + str(p.lineno(2))+bcolors.ENDC
                    )
                else:
                    if p[1].type[0][-1] != "*":
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Expression of the type "
                            + str(p[1].type)
                            + " isn't an array type at Line No.: "
                            + str(p.lineno(2))+bcolors.ENDC
                        )
                    else:
                        p[0] = Node("ArraySubscript", [p[1], p[3]])
                        p[0].type = p[1].type
                        p[0].type[0] = p[0].type[0][0:-1]
                        if p[0].type[0][-1] == " ":
                            p[0].type[0] = p[0].type[0][0:-1]
                            p[0].is_var = 1

    def p_argument_expression_list(self, p):
        """
        argument_expression_list : assignment_expression
                                | argument_expression_list ',' assignment_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
            if p[1] == None:
                return
            p[0].parameter_nums = 1
            p[0].parameters = []
            p[0].parameters.append(p[1].type)
            p[0].type = ["arg list"]

        elif len(p) == 4:
            p[0] = Node(",", [p[1], p[3]])
            if p[1] == None:
                return
            p[0].parameter_nums = p[1].parameter_nums + 1
            p[0].type = ["arg list"]
            p[0].parameters = p[1].parameters
            p[0].parameters.append(p[3].type)

    def p_unary_expression(self, p):
        """
        unary_expression : postfix_expression
                        | INC_OP unary_expression
                        | DEC_OP unary_expression
                        | unary_operator cast_expression
                        | SIZEOF unary_expression
                        | SIZEOF '(' type_name ')'
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 3:
            if p[1] == "++" or p[1] == "--":

                if p[2].type is None:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to increment/decrement the value of expression at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )

                elif p[2].type[0] not in ["int", "char"]:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to use increment/decrement operator on a non-integral at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )
                elif p[2].is_terminal == False:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to use increment/decrement operator on the expression at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )
                elif p[2].is_var == 0:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Unable to use increment/decrement operator on a constant at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )
                else:
                    p[0] = Node("Prefix" + str(p[1]), children=[p[2]])

                    if p[2].type[0] in ["char", "short"]:
                        p[0].type = ["int"]
                        p[0].type += p[2].type[1:]
                        p[2].totype = p[0].type
                    else:
                        p[0].type = p[2].type

            elif p[1] == "sizeof":
                p[0] = Node("SIZEOF", [p[2]])
                p[0].type = ["int"]

            else:
                p[0] = p[1]
                if (p[2] is not None) and (p[2].node is not None):
                    p[0].children.append(p[2])
                    graph.add_edge(p[0].node, p[2].node)

                    if p[2].type == None:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Unable to perform a unary operation at Line No.: "
                            + str(p.lineno(1))+bcolors.ENDC
                        )
                        return

                    if p[1].label[-1] in ["+", "-", "!"]:
                        if p[2].type[0] in ["int", "char", "float"]:
                            p[0].type = [p[2].type[0]]
                            if p[2].type[0] == "char" or p[1].label[-1] == "!":
                                p[0].type = ["int"]
                            else:
                                pass
                        else:
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))+bcolors.ENDC
                            )

                    elif p[1].label[-1] == "~":
                        if p[2].type[0] in ["int", "char"]:
                            p[0].type = [p[2].type[0]]
                            if p[2].type[0] == "char":
                                p[0].type = ["int"]
                            else:
                                pass
                        else:
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))+bcolors.ENDC
                            )

                    elif p[1].label[-1] == "*":
                        if p[2].type[0][-1] != "*":
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))+bcolors.ENDC
                            )
                        else:
                            p[0].is_var = 1
                            p[0].type = p[2].type
                            p[0].type[0] = p[0].type[0][:-1]
                            if p[0].type[0][-1] == " ":
                                p[0].type[0] = p[0].type[0][:-1]
                            try:
                                p[0].vars = p[2].vars
                            except:
                                pass

                    elif p[1].label[-1] == "&":

                        if (
                            "struct" != p[2].type[0]
                            and "union" != p[2].type[0]
                            and p[2].is_var == 0
                        ):
                            self.symtab.error = True
                            print(bcolors.FAIL+
                                "Unable to find a pointer for non-variable type : "
                                + str(p[2].type)
                                + " at Line No.: "
                                + str(p.lineno(1))+bcolors.ENDC
                            )
                        elif "struct" == p[2].type[0] or "union" == p[2].type[0]:
                            p[0].type = p[2].type
                            p[0].type[0] += " *"
                            p[0].vars = p[2].vars

                        else:
                            p[0].type = ["int", "unsigned"]

        elif len(p) == 5:
            p[0] = Node("SIZEOF", [p[3]])
            p[0].type = ["int"]

    def p_unary_operator(self, p):
        """
        unary_operator : '&'
                    | '*'
                    | '+'
                    | '-'
                    | '~'
                    | '!'
        """
        if self.error:
            return
        p[0] = Node("UNARY" + str(p[1]))
        p[0].lineno = p.lineno(1)

    def p_cast_expression(self, p):
        """
        cast_expression : unary_expression
                        | '(' type_name ')' cast_expression
        """
        if self.error:
            return

        if len(p) == 5:
            chd = [p[2], p[4]]
            p[0] = Node("CAST", chd)
            p[0].type = p[2].type

            if p[2].type == None or p[4].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+"Can't perform cast on line no. " + str(p.lineno(1))+bcolors.ENDC)

            elif "struct" in p[2].type:
                self.symtab.error = True
                if "*" not in p[2].type and "struct" not in p[4].type:
                    print(bcolors.FAIL+
                        "Can't cast non-struct value "
                        + str(p[4].type)
                        + " to struct type "
                        + str(p[2].type)
                        + " at Line No.:"
                        + str(p.lineno(1))+bcolors.ENDC
                    )
                elif "struct" in p[4].type and p[4].type[1] not in p[2].type:
                    print(bcolors.FAIL+
                        "Incompatible struct types to perform casting at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )

            elif "union" in p[2].type:
                self.symtab.error = True
                if "*" not in p[2].type and "union" not in p[4].type:
                    print(bcolors.FAIL+
                        "Can't cast non-union value "
                        + str(p[4].type)
                        + " to union type "
                        + str(p[2].type)
                        + " at Line No.:"
                        + str(p.lineno(1))+bcolors.ENDC
                    )

                elif "union" in p[4].type and p[4].type[1] not in p[2].type:
                    print(bcolors.FAIL+
                        "Incompatible union types to perform casting at Line No.: "
                        + str(p.lineno(1))+bcolors.ENDC
                    )

            elif (
                p[4].type[0] not in ["bool", "char", "short", "int", "float"]
                and p[2].type[0] in ["bool", "char", "short", "int", "float"]
            ) or (
                "*" not in p[2].type
                and p[2].type[0] not in ["bool", "char", "short", "int", "float"]
            ):
                self.symtab.error = True
                print(bcolors.FAIL+"Type Mismatch on value casting : Line No. " + str(p.lineno(1))+bcolors.ENDC)

            elif (
                p[4].type[0] not in ["bool", "char", "short", "int"]
                and "*" in p[2].type
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Incompatible casting between "
                    + str(p[4].type)
                    + " and pointer at Line No.:"
                    + str(p.lineno(1))+bcolors.ENDC
                )

        elif len(p) == 2:
            p[0] = p[1]

    def p_multiplicative_expression(self, p):
        """
        multiplicative_expression : cast_expression
                                | multiplicative_expression '*' cast_expression
                                | multiplicative_expression '/' cast_expression
                                | multiplicative_expression '%' cast_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node(str(p[2]), [p[1], p[3]])

            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to multiply the two expressions at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[1].type[0] in ["short", "int", "float"] and p[3].type[0] in [
                "short",
                "int",
                "float",
            ]:
                temp_list = ["short", "int", "float"]
                p[0].type = []
                p[0].type.append(
                    temp_list[
                        max(
                            temp_list.index(p[1].type[0]), temp_list.index(p[3].type[0])
                        )
                    ]
                )
                if ("unsigned" in p[1].type or "unsigned" in p[3].type) and max(
                    temp_list.index(p[1].type[0]), temp_list.index(p[3].type[0])
                ) <= 1:
                    p[0].type.append("unsigned")

                flag = True
                for i in p[0].type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p[0].type

                flag = True
                for i in p[0].type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p[0].type

                p[0].label = p[0].label + p[0].type[0]
                if len(p[0].type) == 2:
                    p[0].label = p[0].label + " " + p[0].type[1]

                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to multiply two incompatible type of expressions ("
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + ") at Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

    def p_additive_expression(self, p):
        """
        additive_expression : multiplicative_expression
                            | additive_expression '+' multiplicative_expression
                            | additive_expression '-' multiplicative_expression
        """
        if self.error:
            return
        temp_list_aa = ["char", "short", "int", "float"]
        temp_list_ii = ["char", "short", "int"]
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node(str(p[2]), [p[1], p[3]])

            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+"Unable to add the expressions on Line No.: " + str(p.lineno(2))+bcolors.ENDC)

            elif p[1].type[0] in temp_list_aa and p[3].type[0] in temp_list_aa:
                p[0].type = []
                p[0].type.append(
                    temp_list_aa[
                        max(
                            temp_list_aa.index(p[1].type[0]),
                            temp_list_aa.index(p[3].type[0]),
                        )
                    ]
                )
                if ("unsigned" in p[1].type or "unsigned" in p[3].type) and max(
                    temp_list_aa.index(p[1].type[0]), temp_list_aa.index(p[3].type[0])
                ) <= 2:
                    p[0].type.append("unsigned")

                isIn = True
                for single_type in p[0].type:
                    if single_type not in p[1].type:
                        isIn = False
                if isIn == False:
                    p[1].totype = p[0].type

                isIn = True
                for single_type in p[0].type:
                    if single_type not in p[3].type:
                        isIn = False
                if isIn == False:
                    p[3].totype = p[0].type

                p[0].label = p[0].label + p[0].type[0]
                if len(p[0].type) == 2:
                    p[0].label = p[0].label + " " + p[0].type[1]

                p[0].node.attr["label"] = p[0].label

            elif p[1].type[0][-1] == "*" and p[3].type[0] in temp_list_ii:
                p[0].label = p[0].label + p[1].type[0]
                p[0].node.attr["label"] = p[0].label
                p[0].type = p[1].type

            elif (
                p[3].type[0][-1] == "*"
                and p[1].type[0] in temp_list_ii
                and p[0].label == "+"
            ):
                p[0].label = p[0].label + p[1].type[0]
                p[0].node.attr["label"] = p[0].label
                p[0].type = p[3].type

            elif (
                p[3].type[0][-1] == "*"
                and p[1].type[0] in temp_list_ii
                and p[0].label == "-"
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Invalid Operation of Binary - performed between the incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to add two incompatible type of expressions ( "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " ) "+bcolors.ENDC
                )

    def p_shift_expression(self, p):
        """
        shift_expression : additive_expression
                        | shift_expression LEFT_OP additive_expression
                        | shift_expression RIGHT_OP additive_expression
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:

            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to perform a bitshift operation between the expressions on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[1].type[0] in ["char", "short", "int"] and p[3].type[0] in [
                "char",
                "short",
                "int",
            ]:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "int"

                if "unsigned" in p[1].type:
                    p[0].type.append("unsigned")
                    p[0].label += "unsigned"

                flag = True
                for i in p[0].type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p[0].type

                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Bitshift operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

    def p_relational_expression(self, p):
        """
        relational_expression : shift_expression
                            | relational_expression '<' shift_expression
                            | relational_expression '>' shift_expression
                            | relational_expression LE_OP shift_expression
                            | relational_expression GE_OP shift_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:

            temp_list = ["char", "short", "int", "float"]
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to perform relational operation between the expressions on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[1].type[0] in temp_list and p[3].type[0] in temp_list:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                val = max(temp_list.index(p[1].type[0]), temp_list.index(p[3].type[0]))
                p[0].label = p[0].label + " " + temp_list[val]

                flag = 0
                if "unsigned" in p[1].type or "unsigned" in p[3].type and val <= 2:
                    flag = 1
                    p[0].lavel = p[0].label + "_" + "unsigned"
                    p[0].node.attr["label"] = p[0].label

                else:
                    p[0].node.attr["label"] = p[0].label

                if temp_list[val] not in p[1].type:
                    p[1].totype = [temp_list[val]]
                    if flag:
                        p[1].totype.append("unsigned")
                if temp_list[val] not in p[3].type:
                    p[3].totype = [temp_list[val]]
                    if flag:
                        p[3].totype.append("unsigned")

            elif p[1].type[0] == "str" and p[3].type[0] == "str":
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "str"
                p[0].node.attr["label"] = p[0].label

            elif p[1].type[0][-1] == "*" and p[3].type[0] in ["float"]:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[3].type[0][-1] == "*" and p[1].type[0] in ["float"]:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif (
                (p[1].type[0][-1] == "*" or p[3].type[0][-1] == "*")
                and "struct" not in p[1].type
                and "union" not in p[1].type
                and "struct" not in p[3].type
                and "union" not in p[3].type
            ):
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "*"
                p[0].node.attr["label"] = p[0].label
                p[1].totype = ["int", "unsigned"]
                p[3].totype = ["int", "unsigned"]

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

    def p_equality_expression(self, p):
        """
        equality_expression : relational_expression
                            | equality_expression EQ_OP relational_expression
                            | equality_expression NE_OP relational_expression
        """

        if True == self.error:
            return

        if len(p) == 4:

            temp_list_a = ["char", "short", "int", "float"]

            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Can't perform check of equality operation between the expressions at Line No.: "
                    + str(p.lineno(1))+bcolors.ENDC
                )

            elif p[1].type[0] in temp_list_a and p[3].type[0] in temp_list_a:
                labell = str(p[2])
                chd = [p[1], p[3]]
                p[0] = Node(labell, chd)
                p[0].type = ["int"]

        elif len(p) == 2:
            p[0] = p[1]

    def p_and_expression(self, p):
        """
        and_expression : equality_expression
                    | and_expression '&' equality_expression
        """
        temp_list = ["bool", "char", "short", "int"]
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to perform bitwise AND operation between the expressions on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[1].type[0] in temp_list and p[3].type[0] in temp_list:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "int"

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p[0].type.append("unsigned")
                    p[0].label += "unsigned"
                p[0].node.attr["label"] = p[0].label

                flag = True
                for i in p[0].type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p[0].type

                flag = True
                for i in p[0].type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p[0].type

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Unable to perform bitwise AND operation between incompatible expression types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))+bcolors.ENDC
                )

    def p_exclusive_or_expression(self, p):
        """
        exclusive_or_expression : and_expression
                                | exclusive_or_expression '^' and_expression
        """
        temp_list_ii = ["bool", "char", "short", "int"]
        if self.error:
            return

        if len(p) == 2:
            p[0] = p[1]
        if len(p) == 4:
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+"Cannot perform bitwise xor on line " + str(p.lineno(2))+bcolors.ENDC)

            elif p[1].type[0] in temp_list_ii and p[3].type[0] in temp_list_ii:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "int"

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p[0].type.append("unsigned")
                    p[0].label += "unsigned"
                p[0].node.attr["label"] = p[0].label

                isIn = 1
                for single_type in p[0].type:
                    if single_type not in p[1].type:
                        isIn = 0
                if isIn == 0:
                    p[1].totype = p[0].type

                isIn = 1
                for single_type in p[3].type:
                    if single_type not in p[3].type:
                        isIn = 0
                if isIn == 0:
                    p[3].totype = p[0].type
            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Bitwise xor operation between types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on line "
                    + str(p.lineno(2))
                    + " is incompatible."+bcolors.ENDC
                )

    def p_inclusive_or_expression(self, p):
        """
        inclusive_or_expression : exclusive_or_expression
                                | inclusive_or_expression '|' exclusive_or_expression
        """
        temp_list = ["bool", "char", "short", "int"]
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Cannot perform bitwise or between expressions on line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif p[1].type[0] in temp_list and p[3].type[0] in temp_list:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "int"

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p[0].type.append("unsigned")
                    p[0].label += "unsigned"
                p[0].node.attr["label"] = p[0].label

                flag = True
                for i in p[0].type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p[0].type

                flag = True
                for i in p[0].type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p[0].type

            else:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Bitwise or operation between types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on line "
                    + str(p.lineno(2))
                    + " is incompatible."+bcolors.ENDC
                )

    def p_logical_and_expression(self, p):
        """logical_and_expression : inclusive_or_expression
        | logical_and_expression AND_OP inclusive_or_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Cannot perform logical and between expressions on line "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            else:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]

    def p_logical_or_expression(self, p):
        """logical_or_expression : logical_and_expression
        | logical_or_expression OR_OP logical_and_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if p[1].type == None or p[3].type == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Cannot perform logical or between expressions on line "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            else:
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]

    def p_conditional_expression(self, p):
        """conditional_expression : logical_or_expression
        | logical_or_expression '?' expression ':' conditional_expression
        """
        temp_list_aa = ["bool", "char", "short", "int", "float"]
        temp_list_ii = ["bool", "char", "short", "int"]
        temp_list_di = ["char", "short", "int"]
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 6:
            p[0] = Node("TERNARY", [p[1], p[3], p[5]])

            if "struct" in p[1].type or "union" in p[1].type:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "First operand of a ternary operator cannot be struct/union type variable"+bcolors.ENDC
                )
                return

            elif p[3] == None or p[5] == None:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Cannot perform conditional operation at line " + str(p.lineno(2))+bcolors.ENDC
                )
                return

            elif p[3].type in [None, []] or p[5].type in [None, []]:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Cannot perform conditional operation at line " + str(p.lineno(2))+bcolors.ENDC
                )

            elif "struct" in p[3].type and "struct" not in p[5].type:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Type mismatch between "
                    + str(p[3].type)
                    + " and "
                    + str(p[5].type)
                    + " for conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif "struct" in p[5].type and "struct" not in p[3].type:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Type mismatch between "
                    + str(p[3].type)
                    + " and "
                    + str(p[5].type)
                    + " for conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif (
                "struct" in p[3].type
                and "struct" in p[5].type
                and p[3].type[1] != p[5].type[1]
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Incompatible struct types to perform conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif "union" in p[3].type and "union" not in p[5].type:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Type mismatch between "
                    + str(p[3].type)
                    + " and "
                    + str(p[5].type)
                    + " for conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif "union" in p[5].type and "union" not in p[3].type:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Type mismatch between "
                    + str(p[3].type)
                    + " and "
                    + str(p[5].type)
                    + " for conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif (
                "union" in p[3].type
                and "union" in p[5].type
                and p[3].type[1] != p[5].type[1]
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Incompatible union types to perform conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )
            elif (
                p[3].type[0] not in temp_list_aa
                and p[3].type[0][-1] != "*"
                and p[5].type[0] in temp_list_aa
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Type mismatch while performing conditional operation at line "
                    + str(p.lineno(2))+bcolors.ENDC
                )

            elif (
                p[3].type[0][-1] == "*"
                and p[5].type[0][-1] != "*"
                and p[5].type[0] not in temp_list_ii
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Conditional operation between pointer and "
                    + str(p[5].type)
                    + " at line "
                    + str(p.lineno(2))
                    + " is incompatible."+bcolors.ENDC
                )

            elif (
                p[5].type[0][-1] == "*"
                and p[3].type[0][-1] != "*"
                and p[3].type[0] not in temp_list_ii
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Conditional operation between pointer and "
                    + str(p[3].type)
                    + " at line "
                    + str(p.lineno(2))
                    + " is incompatible."+bcolors.ENDC
                )

            if p[3].type == p[5].type:
                p[0].type = p[3].type
                return
            if p[3].type[0][-1] == "*" or p[5].type[0][-1] == "*":
                p[0].type = ["int", "unsigned"]
                return
            if "str" in p[3].type:
                p[0].type = p[5].type
                return
            if "str" in p[5].type:
                p[0].type = p[3].type
                return

            if p[3].type[0] in temp_list_aa and p[5].type[0] in [
                "bool",
                "char",
                "short",
                "int",
                "float",
            ]:
                p[0].type = []
                p[0].type.append(
                    temp_list_aa[
                        max(
                            temp_list_aa.index(p[1].type[0]),
                            temp_list_aa.index(p[3].type[0]),
                        )
                    ]
                )
                if (
                    "unsigned" in p[3].type
                    or "unsigned" in p[5].type
                    and p[0].type[0] in temp_list_di
                ):
                    p[0].type.append("unsigned")
                return
            self.symtab.error = True
            print(bcolors.FAIL+
                "Conditional operation at line "
                + str(p.lineno(2))
                + " cannot be performed."+bcolors.ENDC
            )

    def p_assignment_expression(self, p):
        """
        assignment_expression : conditional_expression
                            | unary_expression assignment_operator assignment_expression
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            p[0] = p[2]
            if (p[1] is not None) and (p[1].node is not None):
                if (p[3] is not None) and (p[3].node is not None):

                    if p[1].type in [None, []] or p[3].type in [None, []]:
                        self.symtab.error = True
                        print(bcolors.FAIL+"Cannot perform assignment at line " + str(p[2].lineno)+bcolors.ENDC)

                    elif p[1].type[0][-1] == "*" and "arr" in p[1].type:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Cannot perform assignment to type array at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif (
                        p[1].is_var == 0
                        and "struct" not in p[1].type[0]
                        and "union" not in p[1].type[0]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Left hand side must be a variable at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif "struct" in p[1].type and "struct" not in p[3].type:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Cannot assign non-struct value "
                            + str(p[3].type)
                            + " to struct type "
                            + str(p[1].type)
                            + " at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif (
                        "struct" in p[1].type
                        and "struct" in p[3].type
                        and p[1].type[1] != p[3].type[1]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Incompatible struct types to perform assignment at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif "union" in p[1].type and "union" not in p[3].type:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Cannot assign non-struct value "
                            + str(p[3].type)
                            + " to struct type "
                            + str(p[1].type)
                            + " at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif (
                        "union" in p[1].type
                        and "union" in p[3].type
                        and p[1].type[1] != p[3].type[1]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Incompatible union types at line "
                            + str(p[2].lineno)
                            + " .Assignment not possible."+bcolors.ENDC
                        )

                    elif p[1].type in [None, []] or p[3].type in [None, []]:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Type mismatch while assigning value at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif (
                        p[1].type[0] not in ["bool", "char", "short", "int", "float"]
                        and p[1].type[0][-1] != "*"
                        and p[3].type[0] in ["bool", "char", "short", "int", "float"]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Type mismatch while assigning value at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    elif (
                        p[1].type[0][-1] == "*"
                        and p[3].type[0][-1] != "*"
                        and p[3].type[0] not in ["bool", "char", "short", "int"]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Assignment between pointer and "
                            + str(p[3].type)
                            + " at line "
                            + str(p[2].lineno)
                            + " is incompatible."+bcolors.ENDC
                        )

                    elif (
                        p[1].type[0][-1] == "*"
                        and p[3].type[0] in ["bool", "char", "short", "int"]
                        and p[2].label[0] not in ["+", "-", "="]
                    ):
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Incompatible operands to binary operator "
                            + str(p[2].label)
                            + " at line "
                            + str(p[2].lineno)+bcolors.ENDC
                        )

                    else:
                        graph.add_edge(p[0].node, p[1].node)
                        graph.add_edge(p[0].node, p[3].node)

                        graph.add_edge(p[1].node, p[3].node, style="invis")
                        graph.add_subgraph([p[1].node, p[3].node], rank="same")
                        p[0].children.append(p[1])
                        p[0].children.append(p[3])
                        p[0].type = p[1].type

                        isin = True
                        for single_type in p[0].type:
                            if single_type not in p[3].type:
                                isin = False
                        if isin == False:
                            p[3].totype = p[0].type

                        if "struct" in p[0].type:
                            p[0].label += "struct"
                        elif "union" in p[0].type:
                            p[0].label += "union"
                        elif p[0].type[0][-1] == "*":
                            p[0].label += "int unsigned"
                        else:
                            p[0].label += p[0].type[0]
                            if "unsigned" in p[0].type:
                                p[0].label += " unsigned"

                        p[0].node.attr["label"] = p[0].label

                else:
                    graph.add_edge(p[0].node, p[1].node)
                    p[0].children.append(p[1])

            else:
                if (p[3] is not None) and (p[3].node is not None):
                    graph.add_edge(p[0].node, p[3].node)
                    p[0].children.append(p[3])

    def p_assignment_operator(self, p):
        """
        assignment_operator : '='
                            | MUL_ASSIGN
                            | DIV_ASSIGN
                            | MOD_ASSIGN
                            | ADD_ASSIGN
                            | SUB_ASSIGN
                            | LEFT_ASSIGN
                            | RIGHT_ASSIGN
                            | AND_ASSIGN
                            | XOR_ASSIGN
                            | OR_ASSIGN
        """
        if self.error:
            return

        p[0] = Node(str(p[1]))
        p[0].lineno = p.lineno(1)

    def p_expression(self, p):
        """
        expression : assignment_expression
                | expression ',' assignment_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node(",", [p[1], p[3]])

    def p_constant_expression(self, p):
        """
        constant_expression	: conditional_expression
        """
        if self.error:
            return
        p[0] = p[1]

    # Initializers

    def p_initializer(self, p):
        """
        initializer : assignment_expression
                    | '{' initializer_list '}'
                    | '{' initializer_list ',' '}'
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4 or len(p) == 5:
            p[0] = Node("{}", [p[2]])
            p[0].type = ["init_list"]

    def p_initializer_list(self, p):
        """
        initializer_list : initializer
                        | initializer_list ',' initializer
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = Node(",", [p[1], p[3]])

    # Declarators
    def p_declaration(self, p):
        """declaration	: declaration_specifiers ';'
        | declaration_specifiers init_declarator_list ';'
        """
        if self.error:
            return
        if len(p) == 3:
            p[0] = Node("TypeDecl", create_ast=False)
        elif len(p) == 4:
            p[0] = p[2]
        p[1].remove_graph()

    def p_declaration_specifiers(self, p):
        """declaration_specifiers : type_specifier
        | type_specifier declaration_specifiers
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[1]
            if (p[2] is not None) and (p[2].node is not None):
                graph.add_edge(p[0].node, p[2].node)
                p[0].children.append(p[2])
                if p[2].type and p[0].type:
                    p[0].type += p[2].type

            p[0].extraVals = p[2].extraVals + p[0].extraVals

        if p[0].type and "union" in p[0].type and len(p[0].type) > 2:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Cannot have type specifiers for union type at line " + str(p[1].line)+bcolors.ENDC
            )
        elif p[0].type and "struct" in p[0].type and len(p[0].type) > 2:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Cannot have type specifiers for struct type at line " + str(p[1].line)+bcolors.ENDC
            )

    def p_init_declarator_list(self, p):
        """init_declarator_list : init_declarator
        | init_declarator_list ',' marker_init init_declarator
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            p[0] = Node(",", [p[1], p[4]])
        p[0].extraVals = p[-1].extraVals

    def p_marker_init(self, p):
        """
        marker_init :
        """
        if self.error:
            return
        p[0] = Node("", create_ast=False)
        p[0].extraVals = p[-2].extraVals

    def p_init_declarator(self, p):
        """init_declarator : declarator
        | declarator '=' initializer
        """
        temp_list_aa = ["bool", "char", "short", "int", "float"]
        temp_list_ii = ["bool", "char", "short", "int"]
        if self.error:
            return
        if len(p) == 2:
            p[1].remove_graph()
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node("=", [p[1], p[3]])
            p[0].variables = p[1].variables

        p[0].extraVals = p[-1].extraVals
        for val in p[0].extraVals:
            p[0].addTypeInDict(val)

        for var_name in p[0].variables:
            if p[0].variables[var_name] and p[0].variables[var_name][-1] in [
                "struct",
                "union",
            ]:
                found = self.symtab.return_type_tab_entry_su(
                    p[0].variables[var_name][-2],
                    p[0].variables[var_name][-1],
                    p.lineno(1),
                )
                if found:
                    self.symtab.modify_symbol(
                        var_name, "vars", found["vars"], p.lineno(1)
                    )
                    self.symtab.modify_symbol(
                        var_name, "identifier_type", found["identifier_type"], p.lineno(1)
                    )
                    self.symtab.modify_symbol(
                        var_name, "data_type", p[0].variables[var_name], p.lineno(1)
                    )
            else:
                self.symtab.modify_symbol(
                    var_name, "data_type", p[0].variables[var_name], p.lineno(1)
                )

            # updating sizes
            if p[0].variables[var_name]:
                # handling arrays
                multiplier = 1
                for type_name in p[0].variables[var_name]:
                    if type_name[0] == "[" and type_name[-1] == "]":
                        if type_name[1:-1] != "":
                            multiplier *= int(type_name[1:-1])
                    else:
                        break

                if "*" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["ptr"],
                        p.lineno(1),
                    )
                elif "struct" in p[0].variables[var_name]:
                    struct_size = 0
                    found, entry = self.symtab.return_sym_tab_entry(var_name, p.lineno(1))
                    if found:
                        for var in found["vars"]:
                            struct_size += found["vars"][var]["allocated_size"]
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * struct_size,
                        p.lineno(1),
                    )
                elif "union" in p[0].variables[var_name]:
                    struct_size = 0
                    found, entry = self.symtab.return_sym_tab_entry(var_name, p.lineno(1))
                    if found:
                        for var in found["vars"]:
                            struct_size = max(
                                found["vars"][var]["allocated_size"], struct_size
                            )
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * struct_size,
                        p.lineno(1),
                    )
                elif "float" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["float"],
                        p.lineno(1),
                    )
                elif "short" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["short"],
                        p.lineno(1),
                    )
                elif "int" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["int"],
                        p.lineno(1),
                    )
                elif "char" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["char"],
                        p.lineno(1),
                    )
                elif "bool" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["bool"],
                        p.lineno(1),
                    )
                else:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * sizes["void"],
                        p.lineno(1),
                    )

            found, entry = self.symtab.return_sym_tab_entry(var_name, p.lineno(1))

            temp_type_list = []
            temp2_type_list = []
            nums_arr = []

            for single_type in entry["data_type"]:
                if single_type != "*":
                    temp_type_list.append(single_type)
                    if single_type[0] != "[" or single_type[-1] != "]":
                        temp2_type_list.append(single_type)

                if single_type[0] == "[" and single_type[-1] == "]":
                    if single_type[1:-1] == "":
                        self.symtab.error = True
                        print(bcolors.FAIL+"Cannot have empty indices for array declarations at line"+str(entry["line"])+bcolors.ENDC)
                    elif int(single_type[1:-1]) <= 0:
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Cannot have non-positive integers for array declarations at line"+
                            str(entry["line"])+bcolors.ENDC
                        )

            if len(temp2_type_list) != len(set(temp2_type_list)):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "variables cannot have duplicating type of declarations at line"+
                    str(entry["line"])+bcolors.ENDC
                )

            if "unsigned" in entry["data_type"] and "signed" in entry["data_type"]:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "variable cannot be both signed and unsigned at line"+str(entry["line"])+bcolors.ENDC
                )
            else:
                data_type_count = 0
                if (
                    "int" in entry["data_type"]
                    or "short" in entry["data_type"]
                    or "unsigned" in entry["data_type"]
                    or "signed" in entry["data_type"]
                    or "char" in entry["data_type"]
                ):
                    data_type_count += 1
                if "bool" in entry["data_type"]:
                    data_type_count += 1
                if "float" in entry["data_type"]:
                    data_type_count += 1
                if "void" in entry["data_type"]:
                    data_type_count += 1
                if "struct" in entry["data_type"]:
                    data_type_count += 1
                if "union" in entry["data_type"]:
                    data_type_count += 1
                if data_type_count > 1:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Two or more conflicting data types specified for variable at line"+str(entry["line"])+bcolors.ENDC
                    )

            if len(p) == 4:
                isArr = 0
                for i in range(len(entry["data_type"])):
                    if entry["data_type"][i][0] == "[" and entry["data_type"][i][-1] == "]":
                        isArr += 1

                type_list = entry["data_type"]
                if entry["identifier_type"] == "variable":
                    p[1].is_var = 1

                p[1].type = []
                if "int" in type_list:
                    p[1].type.append("int")
                    for single_type in type_list:
                        if single_type != "int":
                            p[1].type.append(single_type)

                elif "short" in type_list:
                    p[1].type.append("short")
                    for single_type in type_list:
                        if single_type != "short":
                            p[1].type.append(single_type)

                elif "char" in type_list:
                    p[1].type.append("char")
                    for single_type in type_list:
                        if single_type != "char":
                            p[1].type.append(single_type)

                elif "bool" in type_list:
                    p[1].type.append("bool")
                    for single_type in type_list:
                        if single_type != "bool":
                            p[1].type.append(single_type)

                elif "str" in type_list:
                    p[1].type.append("str")
                    for single_type in type_list:
                        if single_type != "str":
                            p[1].type.append(single_type)

                elif "float" in type_list:
                    p[1].type.append("float")
                    for single_type in type_list:
                        if single_type != "float":
                            p[1].type.append(single_type)

                if isArr > 0:
                    temp_type = []
                    temp_type.append(p[1].type[0] + " ")
                    for i in range(isArr):
                        temp_type[0] += "*"

                    for i in range(len(p[1].type)):
                        if i > isArr:
                            temp_type.append(p[1].type[i])
                    p[1].type = temp_type
                    p[1].type.append("arr")

                if "struct" in type_list:
                    p[1].type.append("struct")
                    for single_type in type_list:
                        if single_type != "struct":
                            p[1].type.append(single_type)

                if "union" in type_list:
                    p[1].type.append("union")
                    for single_type in type_list:
                        if single_type != "union":
                            p[1].type.append(single_type)

                if "*" in type_list:
                    temp_type = []
                    temp_type.append(p[1].type[0] + " *")
                    for i in range(len(p[1].type)):
                        if i >= 2:
                            if p[1].type[i] == "*":
                                temp_type[0] += "*"
                            else:
                                temp_type.append(p[1].type[i])
                    p[1].type = temp_type

                if (
                    p[1] == None
                    or p[3] == None
                    or p[1].type == None
                    or p[3].type == None
                ):
                    self.symtab.error = True
                    print(bcolors.FAIL+"Assignment cannot be performed at line " + str(p.lineno(2))+bcolors.ENDC)
                    return

                if "struct" in p[1].type or "union" in p[1].type:
                    p[1].vars = entry["vars"]

                elif "struct *" in p[1].type or "union *" in p[1].type:
                    p[1].vars = entry["vars"]

                elif "struct" in p[1].type[0] or "union" in p[1].type[0]:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Multilevel pointer for structs/unions not allowed at line "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                if "struct" in p[1].type and "struct" not in p[3].type:
                    self.symtab.error = 1
                    print(bcolors.FAIL+
                        "Cannot assign non-struct value "
                        + str(p[3].type)
                        + " to struct type "
                        + str(p[1].type)
                        + " at line "
                        + str(p.lineno(2))
                        +bcolors.ENDC
                    )

                elif (
                    "struct" in p[1].type
                    and "struct" in p[3].type
                    and p[1].type[1] != p[3].type[1]
                ):
                    self.symtab.error = 1
                    print(bcolors.FAIL+"Incompatible struct types at line " + str(p.lineno(2))+bcolors.ENDC)

                elif "union" in p[1].type and "union" not in p[3].type:
                    self.symtab.error = 1
                    print(bcolors.FAIL+
                        "Cannot assign non-union value "
                        + str(p[3].type)
                        + " to union type "
                        + str(p[1].type)
                        + " at line "
                        + str(p.lineno(2))+bcolors.ENDC
                    )

                elif (
                    "union" in p[1].type
                    and "union" in p[3].type
                    and p[1].type[1] != p[3].type[1]
                ):
                    self.symtab.error = 1
                    print(bcolors.FAIL+"Incompatible union types at line " + str(p.lineno(2))+bcolors.ENDC)

                elif p[1].type[0] in temp_list_aa and p[3].type[0] not in temp_list_aa:
                    self.symtab.error = 1
                    print(bcolors.FAIL+"Type mismatch during assignment at line " + str(p.lineno(2))+bcolors.ENDC)

                elif (
                    p[1].type[0] not in temp_list_aa
                    and p[1].type[0][-1] != "*"
                    and p[3].type[0] in temp_list_aa
                ):
                    self.symtab.error = 1
                    print(bcolors.FAIL+"Type mismatch during assignment at line " + str(p.lineno(2))+bcolors.ENDC)

                elif "arr" in p[1].type and "init_list" not in p[3].type:
                    self.symtab.error = 1
                    print(bcolors.FAIL+"Invalid array initialization at line " + str(p.lineno(2))+bcolors.ENDC)

                elif (
                    "arr" not in p[1].type
                    and p[1].type[0][-1] == "*"
                    and p[3].type[0] not in temp_list_ii
                ):
                    self.symtab.error = 1
                    print(bcolors.FAIL+
                        "Assignment between pointer and "
                        + str(p[3].type)
                        + " at line "
                        + str(p.lineno(2))
                        + "is incompatible"+bcolors.ENDC
                    )

                p[0].type = p[1].type

                isIn = True
                for single_type in p[0].type:
                    if single_type not in p[3].type:
                        isIn = False
                if isIn == False:
                    p[3].totype = p[0].type

                if "struct" in p[0].type:
                    p[0].label += "struct"
                elif "union" in p[0].type:
                    p[0].label += "union"
                elif p[0].type[0][-1] == "*" and "arr" not in p[0].type:
                    p[0].label += "int unsigned"
                elif p[0].type[0][-1] == "*" and "arr" in p[0].type:
                    p[0].label += p[0].type[0] + " arr"
                else:
                    p[0].label += p[0].type[0]
                    if "unsigned" in p[0].type:
                        p[0].label += " unsigned"

                p[0].node.attr["label"] = p[0].label

    def p_type_specifier(self, p):
        """type_specifier : VOID
        | CHAR
        | SHORT
        | INT
        | FLOAT
        | SIGNED
        | UNSIGNED
        | struct_or_union_specifier
        | BOOL
        """
        if self.error:
            return
        if str(p[1]) not in [
            "void",
            "char",
            "short",
            "int",
            "float",
            "bool",
            "signed",
            "unsigned",
        ]:
            p[0] = p[1]
            p[0].line = p[1].line
        else:
            p[0] = Node(str(p[1]))
            p[0].extraVals.append(str(p[1]))
            p[0].type = []
            p[0].type.append(str(p[1]))
            p[0].line = p.lineno(1)

    def p_struct_or_union_specifier(self, p):
        """struct_or_union_specifier : struct_or_union IDENTIFIER '{' structMarker1 struct_declaration_list '}' structMarker0
        | struct_or_union IDENTIFIER
        """
        if self.error:
            return
        p[0] = p[1]
        p[0].type += [p[2]["lexeme"]]

        if len(p) == 8:
            p[2] = Node(str([p[2]["lexeme"]]))

            p[0].node.attr["label"] = p[0].node.attr["label"] + "{}"
            p[0].label = p[0].node.attr["label"]

            if (p[2] is not None) and (p[2].node is not None):
                if (p[5] is not None) and (p[5].node is not None):
                    graph.add_edge(p[0].node, p[2].node)
                    graph.add_edge(p[0].node, p[5].node)

                    graph.add_edge(p[2].node, p[5].node, style="invis")
                    graph.add_subgraph(p[2].node, p[5].node, rank="same")
                    p[0].children.append(p[2])
                    p[0].children.append(p[5])
                else:
                    graph.add_edge(p[0].node, p[2].node)
                    p[0].children.append(p[2])
            else:
                if (p[5] is not None) and (p[5].node is not None):
                    graph.add_edge(p[0].node, p[5].node)
                    p[0].children.append(p[5])

        elif len(p) == 3:
            pval = p[2]["lexeme"]
            p[2] = Node(str(pval))
            if (
                self.symtab.return_type_tab_entry_su(p[2].label, p[0].label, p.lineno(2))
                is None
            ):
                self.symtab.error = True
            else:
                p[0].extraVals.append(pval)
                p[0].extraVals.append(p[1].label)
                graph.add_edge(p[0].node, p[2].node)
                p[0].children.append(p[2])

    def p_structMarker0(self, p):
        """
        structMarker0 :
        """
        if self.error:
            return
        self.symtab.flag = 0

    def p_structMarker1(self, p):
        """
        structMarker1 :
        """
        if self.error:
            return
        self.symtab.flag = 1
        identity = p[-2]["lexeme"]
        type_name = p[-3].label.upper()
        line_num = p[-2]["additional"]["line"]
        self.symtab.insert_symbol(identity, line_num, type_name)

        self.symtab.flag = 2

    def p_struct_or_union(self, p):
        """struct_or_union : STRUCT
        | UNION
        """
        if self.error:
            return
        p[0] = Node(str(p[1]))
        p[0].type = [str(p[1]).lower()]
        p[0].line = p.lineno(1)

    def p_struct_declaration_list(self, p):
        """struct_declaration_list : struct_declaration
        | struct_declaration_list struct_declaration
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[2]
            if (p[1] is not None) and (p[1].node is not None):
                graph.add_edge(p[0].node, p[1].node)
                p[0].children.append(p[1])

    def p_struct_declaration(self, p):
        """struct_declaration : specifier_qualifier_list struct_declarator_list ';'"""
        if self.error:
            return
        p[0] = Node("StructORUnionDeclaration", [p[1], p[2]])

        temp_list = []
        for i in p[1].type:
            if i != "*":
                temp_list.append(i)

        length = len(set(temp_list))
        if len(temp_list) != length:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Structure variable cannot have duplicating type of declarations at line "+
                str(p.lineno(3))+bcolors.ENDC
            )

        if "signed" in p[1].type and "unsigned" in p[1].type:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Function type cannot be both signed and unsigned at line "+str(p.lineno(3))+bcolors.ENDC
            )

        else:
            count = 0
            if (
                "char" in p[1].type
                or "short" in p[1].type
                or "int" in p[1].type
                or "unsigned" in p[1].type
                or "signed" in p[1].type
            ):
                count = count + 1
            if "bool" in p[1].type:
                count = count + 1
            if "void" in p[1].type:
                count = count + 1
            if "float" in p[1].type:
                count = count + 1
            if "struct" in p[1].type:
                count = count + 1
            if "union" in p[1].type:
                count = count + 1

            if count > 1:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Two or more conflicting data types specified for function at line "+
                    str(p.lineno(3))+bcolors.ENDC,
                )

        if "union" in p[1].type[0] or "struct" in p[1].type[0]:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Nested structures/unions at line number "
                + str(p.lineno(3))
                + " not supported"+bcolors.ENDC
            )

    def p_specifier_qualifier_list(self, p):
        """specifier_qualifier_list : type_specifier
        | type_specifier specifier_qualifier_list
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[1]

            for i in p[2].type:
                p[0].type.append(i)
            if (p[2] is not None) and (p[2].node is not None):
                graph.add_edge(p[0].node, p[2].node)
                p[0].children.append(p[2])
                p[0].extraVals += p[2].extraVals

    def p_struct_declarator_list(self, p):
        """struct_declarator_list : struct_declarator
        | struct_declarator_list ',' structDeclaratorMarkerStart struct_declarator
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            p[0] = Node(",", [p[1], p[4]])
        p[0].extraVals = p[-1].extraVals

    def p_structDeclaratorMarkerStart(self, p):
        """structDeclaratorMarkerStart :"""
        if self.error:
            return
        p[0] = Node("", create_ast=False)
        p[0].extraVals = p[-2].extraVals

    def p_struct_declarator(self, p):
        """struct_declarator : declarator
        | ':' constant_expression
        | declarator ':' constant_expression
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node(":", [p[2]])
        elif len(p) == 4:
            p[0] = Node(":", [p[1], p[3]])
            p[0].variables = p[1].variables

        p[0].extraVals = p[-1].extraVals

        for value in p[0].extraVals:
            p[0].addTypeInDict(value)

        for name in p[0].variables.keys():
            self.symtab.modify_symbol(name, "data_type", p[0].variables[name], p.lineno(0))
            self.symtab.modify_symbol(name, "varclass", "Struct Local", p.lineno(0))

            if p[0].variables[name]:
                hold = 1
                for tname in p[0].variables[name]:
                    if tname[0] == "[" and tname[-1] == "]":
                        hold *= int(tname[1:-1])
                    else:
                        break

                if "*" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["ptr"], p.lineno(0)
                    )
                elif "float" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["float"], p.lineno(0)
                    )
                elif "short" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["short"], p.lineno(0)
                    )
                elif "int" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["int"], p.lineno(0)
                    )
                elif "char" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["char"], p.lineno(0)
                    )
                elif "bool" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["bool"], p.lineno(0)
                    )
                else:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * sizes["void"], p.lineno(0)
                    )

    def p_declarator(self, p):
        """declarator : pointer direct_declarator
        | direct_declarator
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node("Declarator", [p[1], p[2]])
            p[0].variables = p[2].variables
            for value in p[1].extraVals:
                p[0].addTypeInDict(value)

    def p_function_declarator(self, p):
        """function_declarator : pointer direct_declarator
        | direct_declarator
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node("Declarator", [p[1], p[2]])
            p[0].variables = p[2].variables
            p[0].extraVals += p[1].extraVals

    def p_direct_declarator(self, p):
        """direct_declarator    : IDENTIFIER
        | '(' declarator ')'
        | direct_declarator '[' IntegerConst ']'
        | direct_declarator '[' ']'
        | direct_declarator '(' FunctionPushMarker parameter_type_list ')'
        | direct_declarator '(' identifier_list ')'
        | direct_declarator '(' FunctionPushMarker ')'
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = Node(str(p[1]["lexeme"]))
            p[0].variables[p[0].label] = []
            p[0].is_var = 1
            self.symtab.insert_symbol(p[1]["lexeme"], p[1]["additional"]["line"])
            self.symtab.modify_symbol(p[1]["lexeme"], "identifier_type", "variable")

        elif len(p) == 4:
            if p[1] == "(":
                p[0] = p[2]
            elif p[2] == "[":
                p[0] = Node("DirectDeclaratorArraySubscript", [p[1]])
                p[0].variables = p[1].variables
                p[0].addTypeInDict("[]")

                try:
                    p[0].arrs = []
                except:
                    p[0].arrs = []
                p[0].arrs.append("empty")

        elif len(p) == 5:
            if p[2] == "(":
                if p[3] == None:
                    p[0] = Node("DirectDeclaratorFunctionCall", [p[1]])
                    p[0].variables = p[1].variables
                    p[0].addTypeInDict("Function Name")
                else:
                    p[0] = Node("DirectDeclaratorFunctionCallWithIdList", [p[1], p[3]])

            elif p[2] == "[":
                p[0] = Node("DirectDeclaratorArraySubscript", [p[1], p[3]])
                store = "[" + str(p[3].label) + "]"
                p[0].variables = p[1].variables
                p[0].addTypeInDict(store)

        elif len(p) == 6:
            p[0] = Node("DirectDeclaratorFunctionCall", [p[1], p[4]])
            p[0].variables = p[4].variables
            p[0].variables[p[1].label] = ["Function Name"]

    def p_FunctionPushMarker(self, p):
        """FunctionPushMarker :"""
        if self.error:
            return
        p[0] = None
        self.symtab.push_scope()
        self.symtab.offset = 0

    def p_pointer(self, p):
        """pointer : '*'
        | '*' pointer
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = Node("POINTER")
            p[0].extraVals.append("*")
            p[0].type = ["*"]

        elif len(p) == 3:
            p[0] = Node("POINTER", [p[2]])
            p[0].extraVals = p[2].extraVals
            p[0].extraVals.append("*")
            p[0].type = ["*"]
            if p[2].type:
                for i in p[2].type:
                    p[0].type.append(i)

        elif len(p) == 4:
            p[0] = Node("POINTER", [p[2], p[3]])
            p[0].extraVals = p[2].extraVals + p[3].extraVals
            p[0].extraVals.append("*")
            p[0].type = ["*"]
            if p[1].type:
                for i in p[1].type:
                    p[0].type.append(i)
            if p[2].type:
                for i in p[2].type:
                    p[0].type.append(i)

    def p_parameter_type_list(self, p):
        """parameter_type_list : parameter_list"""
        if self.error:
            return
        p[0] = p[1]

    def p_parameter_list(self, p):
        """parameter_list : parameter_declaration
        | parameter_list ',' parameter_declaration
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = Node(",", [p[1], p[3]])
            p[0].variables = {**p[1].variables, **p[3].variables}

    def p_parameter_declaration(self, p):
        """parameter_declaration : declaration_specifiers declarator
        | declaration_specifiers abstract_declarator
        | declaration_specifiers
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = Node("ParDeclWithoutDeclarator", [p[1]])
        else:
            if str(p.slice[2]) == "declarator":
                p[0] = Node("ParDecl", [p[1], p[2]], create_ast=False)
                p[0].variables = p[2].variables
                p[1].remove_graph()
                p[2].remove_graph()

                for val in p[1].extraVals:
                    p[0].addTypeInDict(val)

            else:
                p[0] = Node("ParDecl", [p[1], p[2]], create_ast=False)
                p[1].remove_graph()
                p[2].remove_graph()

    def p_identifier_list(self, p):
        """identifier_list : IDENTIFIER
        | identifier_list ',' IDENTIFIER
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = Node(str(p[1]["lexeme"]))
        else:
            p3val = p[3]["lexeme"]
            p[3] = Node(str(p3val))
            p[0] = Node(",", [p[1], p[3]])

    def p_type_name(self, p):
        """type_name : specifier_qualifier_list
        | specifier_qualifier_list abstract_declarator
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = Node("TypeName", [p[1]])
            p[0].type = p[1].type
        else:
            p[0] = Node("TypeName", [p[1], p[2]])
            p[0].type = p[1].type

            if not p[0].type:
                p[0].type = []

            if p[2].type:
                for single_type in p[2].type:
                    p[0].type.append(single_type)

    def p_abstract_declarator(self, p):
        """abstract_declarator : pointer
        | direct_abstract_declarator
        | pointer direct_abstract_declarator
        """
        if self.error:
            return

        if len(p) == 2:
            p[0] = Node("AbsDecl", [p[1]])
            p[0].type = p[1].type

        else:
            p[0] = Node("AbsDecl", [p[1], p[2]])
            p[0].type = p[1].type
            if p[2].type:
                for single_type in p[2].type:
                    p[0].type.append(single_type)

    def p_direct_abstract_declarator(self, p):
        """direct_abstract_declarator : '(' abstract_declarator ')'
        | '[' ']'
        | '[' constant_expression ']'
        | direct_abstract_declarator '[' ']'
        | direct_abstract_declarator '[' IntegerConst ']'
        | '(' ')'
        | '(' parameter_type_list ')'
        | direct_abstract_declarator '(' ')'
        | direct_abstract_declarator '(' parameter_type_list ')'
        """
        if self.error:
            return
        if len(p) == 3:
            if p[1] == "(":
                p[0] = Node("DirectAbstractDeclarator()")
            elif p[1] == "[":
                p[0] = Node("DirectAbstractDeclarator[]")

        if len(p) == 4:
            if p[1] == "(":
                p[0] = Node("DirectAbstractDeclarator()", [p[2]])
            elif p[1] == "[":
                p[0] = Node("DirectAbstractDeclarator[]", [p[2]])
            elif p[2] == "(":
                p[0] = Node("POSTDirectAbstractDeclarator()", [p[1]])
            elif p[2] == "[":
                p[0] = Node("POSTDirectAbstractDeclarator[]", [p[1]])

        elif len(p) == 5:
            if p[2] == "(":
                p[0] = Node("DirectAbstractDeclarator()", [p[1], p[3]])
            elif p[2] == "[":
                p[0] = Node("DirectAbstractDeclarator[]", [p[1], p[3]])

    # Statements
    def p_statement(self, p):
        """
        statement   : labeled_statement
                    | compound_statement
                    | expression_statement
                    | selection_statement
                    | iteration_statement
                    | jump_statement
        """
        if self.error:
            return
        p[0] = p[1]

    def p_labeled_statement(self, p):
        """
        labeled_statement   : IDENTIFIER ':' statement
                            | CASE constant_expression ':' statement
                            | DEFAULT ':' statement
        """
        if self.error:
            return

        if len(p) == 4:
            if p[1] == "default":
                p[0] = Node("DEFAULT:", [p[3]])
            else:
                p1val = p[1]["lexeme"]
                p[1] = Node(str(p1val))
                p[0] = Node("IDENTIFIER:", [p[1], p[3]])
        else:
            p[0] = Node("CASE:", [p[2], p[4]])

    def p_compound_statement(self, p):
        """
        compound_statement  : '{' marker_compound_statement_push '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push statement_list '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push declaration_list '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push declaration_list statement_list '}' marker_compound_statement_pop
        """
        if self.error:
            return
        if len(p) == 5:
            p[0] = Node("EmptySCOPE", create_ast=False)
        elif len(p) == 6:
            p[0] = Node("SCOPE", [p[3]])
        elif len(p) == 7:
            p[0] = Node("SCOPE", [Node(";", [p[3], p[4]])])

    def p_marker_compound_statement_push(self, p):
        """
        marker_compound_statement_push :
        """
        if self.error:
            return
        self.symtab.push_scope()

    def p_marker_compound_statement_pop(self, p):
        """
        marker_compound_statement_pop :
        """
        if self.error:
            return
        self.symtab.pop_scope()

    def p_block_item_list(self, p):
        """
        block_item_list : statement_list
                        | declaration_list
                        | declaration_list statement_list
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node(";", [p[1], p[2]])

    def p_statement_list(self, p):
        """
        statement_list  : statement
                        | statement_list statement
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node(";", [p[1], p[2]])

    def p_declaration_list(self, p):
        """
        declaration_list    : declaration
                            | declaration_list declaration
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node(";", [p[1], p[2]])

    def p_expression_statement(self, p):
        """
        expression_statement    : ';'
                                | expression ';'
        """
        if self.error:
            return
        if len(p) == 2:
            p[0] = Node("EmptyExprStmt")
        if len(p) == 3:
            p[0] = p[1]

    def p_selection_statement(self, p):
        """
        selection_statement : IF '(' expression ')' statement %prec IF_STATEMENTS
                            | IF '(' expression ')' statement ELSE statement
                            | SWITCH '(' expression ')' statement
        """
        if self.error:
            return

        if len(p) == 6:
            p[0] = Node(str(p[1]).upper(), [p[3], p[5]])
        else:
            p[0] = Node("IF-ELSE", [p[3], p[5], p[7]])

    def p_iteration_statement(self, p):
        """
        iteration_statement : WHILE '(' expression ')' statement
                            | DO statement WHILE '(' expression ')' ';'
                            | FOR '(' expression_statement expression_statement ')' statement
                            | FOR '(' expression_statement expression_statement expression ')' statement
                            | FOR '(' push_marker_loops declaration expression_statement ')' statement pop_marker_loops
                            | FOR '(' push_marker_loops declaration expression_statement expression ')' statement pop_marker_loops
        """
        if True == self.error:
            return

        l1 = ["FOR", "WHILE", "DO-WHILE"]

        if len(p) == 10:
            p[0] = Node(l1[0], [p[4], p[5], p[6], p[8]])
        elif len(p) == 9:
            p[0] = Node(l1[0], [p[4], p[5], p[7]])
        elif len(p) == 8:
            if p[1] == "do":
                p[0] = Node(l1[2], [p[2], p[5]])
            else:
                p[0] = Node(l1[0], [p[3], p[4], p[5], p[7]])
        elif len(p) == 7:
            p[0] = Node(l1[0], [p[3], p[4], p[6]])
        elif len(p) == 6:
            p[0] = Node(l1[1], [p[3], p[5]])

    def p_push_marker_loops(self, p):
        """
        push_marker_loops :
        """
        if True == self.error:
            return
        else:
            self.symtab.push_scope()

    def p_pop_marker_loops(self, p):
        """
        pop_marker_loops :
        """
        if True == self.error:
            return
        else:
            self.symtab.pop_scope()

    def p_jump_statement(self, p):
        """
        jump_statement  : CONTINUE ';'
                        | BREAK ';'
                        | RETURN ';'
                        | RETURN expression ';'
        """
        if self.error:
            return

        if len(p) == 3:
            p[0] = Node(str(p[1]).upper())
            if p[1] == "return":
                found = list(self.symtab.table[0])
                functype = self.symtab.table[0][found[-1]]["data_type"]

                if functype != ["void"]:
                    self.symtab.error = True
                    print(bcolors.FAIL+
                        "Cannot return! Need an argument of type "
                        + str(functype)
                        + " at line "
                        + str(p.lineno(1))+bcolors.ENDC
                    )

        else:
            p[0] = Node("RETURN", [p[2]])
            found = list(self.symtab.table[0])
            functype = self.symtab.table[0][found[-1]]["data_type"]

            if (
                "*" in functype
                and "*" not in p[2].type[0]
                and p[2].type[0] not in ["bool", "char", "short", "int"]
            ):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Incompatible types while returning "
                    + str(p[2].type)
                    + "."
                    + str(functype)
                    + " was expected at line "
                    + str(p.lineno(1))+bcolors.ENDC
                )

            elif functype[0] in ["bool", "char", "short", "int", "float"] and p[2].type[
                0
            ] not in ["bool", "char", "short", "int", "float"] and not ("*" in functype
                and "*" in p[2].type[0]):
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Mismatch in type while returning value at line " + str(p.lineno(1))+bcolors.ENDC
                )

            elif functype == ["void"] and p[2].type[0] != "void":
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Non void type at line number "
                    + str(p.lineno(1))
                    + ". Cannot return."+bcolors.ENDC
                )

    # External declaration and function definitions
    def p_translation_unit(self, p):
        """translation_unit : translation_unit external_declaration
        | external_declaration
        """
        if self.error:
            return

        p[0] = self.ast_root
        if len(p) == 2:
            if (p[1] is not None) and (p[1].node is not None):
                graph.add_edge(p[0].node, p[1].node)
                self.ast_root.children.append(p[1])
        elif len(p) == 3:
            if (p[2] is not None) and (p[2].node is not None):
                graph.add_edge(p[0].node, p[2].node)
                self.ast_root.children.append(p[2])

    def p_external_declaration(self, p):
        """external_declaration : function_definition
        | declaration
        """
        if self.error:
            return
        p[0] = p[1]

    def p_function_definition(self, p):
        """function_definition :  declaration_specifiers function_declarator '{' markerFuncStart '}' markerFuncEnd
        | declaration_specifiers function_declarator '{' markerFuncStart block_item_list '}' markerFuncEnd
        """
        if self.error:
            return
        line = 0
        if len(p) == 7:
            p[0] = Node("function", [p[2]])
            line = 3

        elif len(p) == 8:
            if p[3] == "{":
                p[0] = Node("function", [p[2], Node("SCOPE", [p[5]])])
                line = 3
            else:
                p[0] = Node("function", [p[2], p[3]])
                line = 4
        elif len(p) == 9:
            p[0] = Node("function", [p[2], p[3]], Node("SCOPE", [p[6]]))
            line = 4
        p[1].remove_graph()

        temp_list = []
        for i in p[1].type:
            if i != "*":
                temp_list.append(i)

        val = len(set(temp_list))
        if len(temp_list) != val:
            self.symtab.error = True
            print(bcolors.FAIL+
                "Function type cannot have duplicating type of declarations at line "+
                str(p.lineno(line))+bcolors.ENDC
            )

        if "unsigned" in p[1].type and "signed" in p[1].type:
            self.symtab.error = True
            print(bcolors.fail+
                "Function type cannot be both signed and unsigned at line "+
                str(p.lineno(line))+bcolors.ENDC
            )

        else:
            cnt = 0
            if (
                "signed" in p[1].type
                or "unsigned" in p[1].type
                or "int" in p[1].type
                or "char" in p[1].type
                or "short" in p[1].type
            ):
                cnt = cnt + 1
            if "bool" in p[1].type:
                cnt = cnt + 1
            if "void" in p[1].type:
                cnt = cnt + 1
            if "float" in p[1].type:
                cnt = cnt + 1
            if "struct" in p[1].type:
                cnt = cnt + 1
            if "union" in p[1].type:
                cnt = cnt + 1

            if cnt > 1:
                self.symtab.error = True
                print(bcolors.FAIL+
                    "Two or more conflicting data types specified for function at line "+
                    str(p.lineno(line))+bcolors.ENDC
                )

        for i in p[2].variables:
            temp = p[2].variables[i]
            if "Function Name" not in temp:
                temp_arr = []
                for i in temp:
                    if i[0] == "[" and i[-1] == "]":
                        temp_arr.append(i[1:-1])
                for i in range(len(temp_arr)):
                    if i != 0 and temp_arr[i] == "":
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Multidimensional array must have bound for all dimensions except first at line "+
                            str(p.lineno(line))+bcolors.ENDC
                        )

                    if int(temp_arr[i]) <= 0 and temp_arr[i] != "":
                        self.symtab.error = True
                        print(bcolors.FAIL+
                            "Array bound cannot be non-positive at line "+
                            str(p.lineno(line))+bcolors.ENDC
                        )

    def p_markerFuncStart(self, p):
        """
        markerFuncStart :
        """
        if self.error:
            return
        p[0] = Node("", create_ast=False)
        p[0].variables = p[-2].variables
        function_name = str()
        tosearch = "Function Name"
        valtype = "function"

        for key in p[0].variables.keys():
            if p[0].variables[key][0] == tosearch:
                function_name = key
                break

        p[0].variables[key] = p[0].variables[key] + p[-3].extraVals + p[-2].extraVals

        self.symtab.modify_symbol(
            function_name, "identifier_type", valtype, p.lineno(0)
        )  # says that this entry is a function
        param_nums = 0

        for var_name in p[0].variables.keys():
            if not var_name == function_name:

                if p[0].variables[var_name] and (
                    p[0].variables[var_name][-1] == "struct"
                    or p[0].variables[var_name][-1] == "union"
                ):
                    found = self.symtab.return_type_tab_entry_su(
                        p[0].variables[var_name][-2],
                        p[0].variables[var_name][-1],
                        p.lineno(0),
                    )
                    if found:
                        self.symtab.modify_symbol(
                            var_name, "identifier_type", found["identifier_type"], p.lineno(0)
                        )
                        self.symtab.modify_symbol(
                            var_name, "vars", found["vars"], p.lineno(0)
                        )
                        self.symtab.modify_symbol(
                            var_name, "data_type", p[0].variables[var_name], p.lineno(0)
                        )
                else:
                    self.symtab.modify_symbol(
                        var_name, "data_type", p[0].variables[var_name], p.lineno(0)
                    )
                self.symtab.modify_symbol(var_name, "identifier_type", "parameter", p.lineno(0))
                param_nums = param_nums + 1

                #updating variable class
                if p[0].variables[var_name]:
                    isGlobal = self.symtab.is_global(var_name)
                    if isGlobal:
                        self.symtab.modify_symbol(
                            var_name, "varclass", "Global", p.lineno(0)
                        )
                    else:
                        self.symtab.modify_symbol(
                            var_name, "varclass", "Local", p.lineno(0)
                        )

                # updating sizes
                if p[0].variables[var_name]:
                    # handling arrays
                    prod = 1
                    for type_name in p[0].variables[var_name]:
                        if type_name[0] == "[" and type_name[-1] == "]":
                            if type_name[1:-1] != "":
                                prod = prod * int(type_name[1:-1])
                        else:
                            break

                    szstr = "allocated_size"
                    vct = [
                        "struct",
                        "union",
                        "float",
                        "short",
                        "int",
                        "char",
                        "bool",
                        "void",
                    ]

                    if "*" in p[0].variables[var_name]:
                        self.symtab.modify_symbol(
                            var_name, szstr, prod * sizes["ptr"], p.lineno(0)
                        )

                    else:
                        for vc in vct:
                            if vc == "struct":
                                if vc in p[0].variables[var_name]:
                                    struct_size = 0
                                    found, tmp = self.symtab.return_sym_tab_entry(
                                        var_name, p.lineno(0)
                                    )
                                    if True == found:
                                        for var in found["vars"]:
                                            struct_size = (
                                                struct_size + found["vars"][var][szstr]
                                            )
                                    self.symtab.modify_symbol(
                                        var_name, szstr, prod * struct_size, p.lineno(0)
                                    )

                            elif vc == "union":
                                if vc in p[0].variables[var_name]:
                                    struct_size = 0
                                    found, tmp = self.symtab.return_sym_tab_entry(
                                        var_name, p.lineno(0)
                                    )
                                    if found:
                                        for var in found["vars"]:
                                            struct_size = max(
                                                found["vars"][var][szstr], struct_size
                                            )
                                    self.symtab.modify_symbol(
                                        var_name, szstr, prod * struct_size, p.lineno(0)
                                    )

                            else:
                                if vc in p[0].variables[var_name]:
                                    self.symtab.modify_symbol(
                                        var_name, szstr, prod * sizes[vc], p.lineno(0)
                                    )
            else:
                self.symtab.modify_symbol(var_name, "data_type", p[0].variables[key][1:])

        self.symtab.modify_symbol(function_name, "num_parameters", param_nums)

    def p_markerFuncEnd(self, p):
        """
        markerFuncEnd :
        """
        if True == self.error:
            return
        self.symtab.pop_scope()

    def printTree(self):
        self.ast_root.print_val()


aparser = argparse.ArgumentParser()
aparser.add_argument(
    "-d", "--debug", action="store_true", help="Parser Debug Mode", default=False
)
aparser.add_argument(
    "-o", "--out", help="Store output of parser in a file", default='symtab.csv'
)
aparser.add_argument("infile", help="Input File")
args = aparser.parse_args()

with open(args.infile, "r") as f:
    inp = f.read()

lex = Lexer(error_func)
lex.build()
lex.lexer.input(inp)
tokens = lex.tokens
lex.lexer.lineno = 1
lex.lexer.lines = inp.split("\n")

parser = Parser()
parser.build()
result = parser.parser.parse(inp, lexer=lex.lexer)

fdir = '/'.join(args.out.split("/")[:-1])
fname = args.out.split("/")[-1].split(".")[0]
outputFile = "dot/" + fname + ".dot"

if parser.error:
    print(bcolors.FAIL+"Error found. Aborting parsing of " + str(sys.argv[1]) + "...."+bcolors.ENDC)
    sys.exit(0)
elif parser.symtab.error:
    print(bcolors.FAIL+"Error in semantic analysis."+bcolors.ENDC)
    sys.exit(0)
else:
    symtab_csv= open(fdir + "/" + fname + ".csv", "w")
    print("Output Symbol Table CSV is: " + fname + ".csv")
    graph.write(outputFile)
    orig_stdout = sys.stdout
    sys.stdout = symtab_csv
    parser.symtab.print_table()
    sys.stdout = orig_stdout
