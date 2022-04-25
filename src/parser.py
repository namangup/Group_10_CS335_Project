# https://www.lysator.liu.se/c/ANSI-C-grammar-y.html
# https://github.com/dabeaz/ply/blob/master/doc/ply.md

import ply.yacc as yacc
from lexer import Lexer, error_func
import argparse
import sys
import pygraphviz as pgv
from symboltable import SymbolTable, bcolors
from three_address_code import three_address_code
import struct, copy

num_nodes = 0
graph = pgv.AGraph(strict=False, directed=True)
graph.layout(prog="circo")


class Node:
    def __init__(self, label, children=None, create_ast=True):
        self.label = label
        self.children = []
        self.create_ast = create_ast
        self.attributes = {"error": False}
        self.is_var = False
        self.variables = {}
        self.temp = ""

        (
            self.extraVals,
            self.var_name,
            self.break_list,
            self.continuelist,
            self.true_list,
            self.next_list,
            self.false_list,
            self.argument_list,
            self.test_list,
            self.type,
        ) = ([] for i in range(10))

        (
            self.node,
            self.totype,
            self.parameter_nums,
            self.parameters,
            self.quadruples,
            self.dim_list,
            self.address,
        ) = (None,) * 7

        self.numdef, self.array_level = (0,) * 2

        if children is None:
            self.is_terminal = True
        else:
            self.is_terminal = False

        if children is not None:
            self.children = children

        if self.create_ast:
            self.make_graph()

    def print_val(self):
        for child in self.children:
            child.print_val()
        self.node.attr["label"] += "\n" + str(self.temp)

    def append_dict(self, val):
        for key in self.variables.keys():
            self.variables[key].append(val)

    def insert_edge(self, children):
        listNode = []
        for idx, child in enumerate(children):
            listNode = listNode + [child.node]
            graph.add_edge(self.node, child.node)
        for i in range(0, len(children) - 1):
            graph.add_edge(children[i].node, children[i + 1].node, style="invis")
        graph.add_subgraph(listNode, rank="same")
        self.children = self.children + children

    def make_graph(self):
        if not self.is_terminal:
            children = []
            for idx, child in enumerate(self.children):
                if child is None:
                    pass
                elif child.node is None:
                    pass
                else:
                    children.append(child)
            self.children = children
            if self.children is not None:
                listNode = []
                self.node = new_node()
                self.node.attr["label"] = self.label
                for idx, child in enumerate(self.children):
                    graph.add_edge(self.node, child.node)
                    listNode.append(child.node)
                graph.add_subgraph(listNode, rank="same")
        else:
            self.node = new_node()
            self.node.attr["label"] = self.label

    def remove_graph(self):
        for child in self.children:
            if child.node:
                child.remove_graph()
        remove_node(self.node)
        self.node = None


datatype_size = dict()
datatype_size["void"] = 0
datatype_size["bool"] = 1
datatype_size["char"] = 1
datatype_size["short"] = 2
datatype_size["ptr"] = 4
datatype_size["int"] = 4
datatype_size["float"] = 4
datatype_size["unsigned int"] = 4
datatype_size["int unsigned"] = 4
datatype_size["str"] = 4  # char pointer


class Parser:

    tokens = Lexer.tokens
    keywords = Lexer.keywords
    precedence = (("nonassoc", "IF_STATEMENTS"), ("nonassoc", "ELSE"))

    def __init__(self):
        self.symtab = SymbolTable()
        self.ast_root = Node("AST Root")
        self.error = False
        self.three_address_code = three_address_code()

    def symtab_size_update(self, variables, var_name):
        multiplier = 1
        new_list = list()
        for idx, var in enumerate(variables):
            new_list += var.split(" ")
        variables = new_list

        if "*" in variables:
            self.symtab.modify_symbol(var_name, "allocated_size", datatype_size["ptr"])
        elif "struct" in variables:
            found = self.symtab.return_type_tab_entry_su(variables[1], "struct")
            if found is not None:
                struct_size = found["allocated_size"]
                self.symtab.modify_symbol(var_name, "allocated_size", struct_size)
        else:
            datatype_arr = ["float", "short", "int", "char", "bool", "void"]
            flag = False
            for idx, dtype in enumerate(datatype_arr):
                if dtype in variables:
                    flag = True
                    self.symtab.modify_symbol(
                        var_name, "allocated_size", datatype_size[dtype]
                    )
                    break

    # inspired from https://stackoverflow.com/a/60384184
    def convertFloatRepToLong(self, val):
        float_rep = "".join(
            bin(c).replace("0b", "").rjust(8, "0") for c in struct.pack("!f", val)
        )
        long_rep = int(float_rep, 2)
        self.three_address_code.float_values.append(long_rep)
        return len(self.three_address_code.float_values) - 1

    def build(self):
        self.parser = yacc.yacc(
            module=self, start="start", outputdir="tmp", debug=args.debug
        )

    def p_start(self, p):
        """
        start : push_lib_functions translation_unit
        """
        if self.error == True:
            return
        p[0] = self.ast_root
        self.symtab.store_results(self.three_address_code)

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

    def p_bool_constant(self, p):
        """bool_constant : TRUE
        | FALSE
        """
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["bool"]

    def p_integer_constant(self, p):
        """integer_constant : INTEGER_CONSTANT"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["int"]
        if self.symtab.error == True:
            return
        p[0].temp = self.three_address_code.create_temp_var()
        self.symtab.insert_symbol(p[0].temp, 0)
        self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
        self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
        self.symtab_size_update(p[0].type, p[0].temp)
        if self.symtab.is_global(p[0].temp):
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
        else:
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
            found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
            var_size = found["allocated_size"]
            if found["variable_scope"] == "Local":
                if found["offset"] > 0:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                    )
                else:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                    )
            p[0].temp = found["temp"]
        self.three_address_code.emit("=_int", p[0].temp, f"${p[1]}")

    def p_float_constant(self, p):
        """float_constant : FLOAT_CONSTANT"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        idx = self.convertFloatRepToLong(p[1])
        p[0].type = ["float"]
        if self.symtab.error == True:
            return
        p[0].temp = self.three_address_code.create_temp_var()
        self.symtab.insert_symbol(p[0].temp, 0)
        self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
        self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
        self.symtab_size_update(p[0].type, p[0].temp)
        if self.symtab.is_global(p[0].temp):
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
        else:
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
            found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
            var_size = found["allocated_size"]
            if found["variable_scope"] == "Local":
                if found["offset"] > 0:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                    )
                else:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                    )
            p[0].temp = found["temp"]
        self.three_address_code.emit("load_float", f".LF{idx}", p[0].temp, "")

    def p_char_constant(self, p):
        """char_constant : CHAR_CONSTANT"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        p[0].type = ["char"]
        if self.symtab.error == True:
            return
        p[0].temp = self.three_address_code.create_temp_var()
        self.symtab.insert_symbol(p[0].temp, 0)
        self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
        self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
        self.symtab_size_update(p[0].type, p[0].temp)
        if self.symtab.is_global(p[0].temp):
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
        else:
            self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
            found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
            var_size = found["allocated_size"]
            if found["variable_scope"] == "Local":
                if found["offset"] > 0:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                    )
                else:
                    self.symtab.modify_symbol(
                        p[0].temp,
                        "temp",
                        f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                    )
            p[0].temp = found["temp"]
        self.three_address_code.emit("=_char", p[0].temp, f"${p[1]}")

    def p_string_constant(self, p):
        """string_constant : STRING_CONSTANT"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        self.three_address_code.string_list.append(str(p[1]))
        p[0].type = ["str"]
        if self.symtab.error == True:
            return
        for i in range(0, len(self.three_address_code.string_list)):
            if self.three_address_code.string_list[i] == p[1]:
                idx = i
                break
        p[0].temp = f"$.LC{idx}"

    def p_primary_expression(self, p):
        """
        primary_expression : IDENTIFIER
                        | integer_constant
                        | float_constant
                        | char_constant
                        | bool_constant
                        | string_constant
                        | '(' expression ')'
        """
        if self.error == True:
            return

        if p.slice[1].type == "IDENTIFIER":
            found, entry = self.symtab.return_sym_tab_entry(p[1]["lexeme"], p.lineno(1))
            if found:
                if "data_type" not in entry.keys():
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Use of self referencing variables  isn't allowed at line No "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                    return
                if entry["identifier_type"] == "function":
                    p[0] = Node(str(p[1]["lexeme"]))
                    p[0].type.append("function")
                    p[0].ret_type = []
                    type_list = entry["data_type"]
                    isarr = 0

                    for i in range(len(entry["data_type"])):
                        if (
                            entry["data_type"][i][0] == "["
                            and entry["data_type"][i][-1] == "]"
                        ):
                            isarr += 1
                            p[0].array_level += 1

                    if "unsigned" in type_list or "signed" in type_list:
                        if (
                            "bool" not in type_list
                            and "char" not in type_list
                            and "short" not in type_list
                        ):
                            type_list.append("int")

                    if "int" in type_list:
                        p[0].ret_type.append("int")
                        for single_type in type_list:
                            if single_type != "int":
                                p[0].ret_type.append(single_type)

                    elif "short" in type_list:
                        p[0].ret_type.append("short")
                        for single_type in type_list:
                            if single_type != "short":
                                p[0].ret_type.append(single_type)

                    elif "char" in type_list:
                        p[0].ret_type.append("char")
                        for single_type in type_list:
                            if single_type != "char":
                                p[0].ret_type.append(single_type)

                    elif "bool" in type_list:
                        p[0].ret_type.append("bool")
                        for single_type in type_list:
                            if single_type != "bool":
                                p[0].ret_type.append(single_type)

                    elif "str" in type_list:
                        p[0].ret_type.append("str")
                        for single_type in type_list:
                            if single_type != "str":
                                p[0].ret_type.append(single_type)

                    elif "float" in type_list:
                        p[0].ret_type.append("float")
                        for single_type in type_list:
                            if single_type != "float":
                                p[0].ret_type.append(single_type)

                    if isarr > 0:
                        temp_type = []
                        temp_type.append(p[0].ret_type[0])
                        for i in range(isarr):
                            temp_type[0] += " *"

                        for i in range(len(p[0].ret_type)):
                            if i > isarr:
                                temp_type.append(p[0].ret_type[i])

                        p[0].ret_type = temp_type
                        p[0].ret_type.append("arr")
                        for i in range(len(type_list)):
                            if (
                                type_list[len(type_list) - i - 1][0] == "["
                                and type_list[len(type_list) - i - 1][-1] == "]"
                            ):
                                p[0].ret_type.append(type_list[len(type_list) - i - 1])

                    if "struct" in type_list:
                        p[0].ret_type.append("struct")
                        for single_type in type_list:
                            if single_type != "struct":
                                p[0].ret_type.append(single_type)

                    if "void" in type_list:
                        p[0].ret_type.append("void")
                        for single_type in type_list:
                            if single_type != "void":
                                p[0].ret_type.append(single_type)

                    if "*" in type_list:
                        temp_type = []
                        temp_type.append(p[0].ret_type[0])
                        for i in range(1, len(p[0].ret_type)):
                            if p[0].ret_type[i] == "*":
                                temp_type[0] += " *"
                            else:
                                temp_type.append(p[0].ret_type[i])
                        p[0].ret_type = temp_type

                    p[0].parameter_nums = entry["num_parameters"]
                    p[0].parameters = []

                    if "scope" in entry.keys():
                        for var in entry["scope"][0]:
                            if var == "struct":
                                p[0].struct = entry["scope"][0][var]
                                continue
                            if var == "scope" or var == "scope_num":
                                continue
                            if entry["scope"][0][var]["identifier_type"] == "parameter":
                                p[0].parameters.append(entry["scope"][0][var])

                    if self.symtab.error == True:
                        return
                    p[0].true_list.append(self.three_address_code.next_statement)
                    p[0].false_list.append(self.three_address_code.next_statement + 1)
                    return

                isArr = 0

                for i in range(len(entry["data_type"])):
                    if (
                        entry["data_type"][i][0] == "["
                        and entry["data_type"][i][-1] == "]"
                    ):
                        isArr += 1

                p[0] = Node(str(p[1]["lexeme"]))
                type_list = entry["data_type"]

                if type_list is None or set(type_list) == {"*"}:
                    type_list = []

                if (
                    entry["identifier_type"] == "variable"
                    or entry["identifier_type"] == "parameter"
                ):
                    p[0].is_var = 1

                if "unsigned" in type_list or "signed" in type_list:
                    if (
                        "bool" not in type_list
                        and "char" not in type_list
                        and "short" not in type_list
                    ):
                        type_list.append("int")

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

                if "struct" in type_list:
                    p[0].type.append("struct")
                    for single_type in type_list:
                        if single_type != "struct":
                            p[0].type.append(single_type)

                if isArr > 0:
                    temp_type = []
                    temp_type.append(p[0].type[0])
                    for i in range(isArr):
                        temp_type[0] += " *"

                    for i in range(len(p[0].type)):
                        if i > isArr:
                            temp_type.append(p[0].type[i])
                    p[0].type = temp_type
                    p[0].type.append("arr")

                    for i in range(len(type_list)):
                        if (
                            type_list[len(type_list) - i - 1][0] == "["
                            and type_list[len(type_list) - i - 1][-1] == "]"
                        ):
                            p[0].type.append(type_list[len(type_list) - i - 1])

                if "void" in type_list:
                    p[0].type.append("void")
                    for single_type in type_list:
                        if single_type != "void":
                            p[0].type.append(single_type)

                if "*" in type_list:
                    temp_type = []
                    temp_type.append(p[0].type[0])
                    for i in range(1, len(p[0].type)):
                        if p[0].type[i] == "*":
                            temp_type[0] += " *"
                        else:
                            temp_type.append(p[0].type[i])
                    p[0].type = temp_type

                if "struct" in p[0].type[0]:
                    p[0].vars = entry["vars"]

            else:
                p[0] = Node("error")

            if self.symtab.error == True:
                return

            p[0].var_name.append(p[1]["lexeme"])
            p[0].temp = self.three_address_code.find_symbol_in_symtab(
                self.symtab, p[0].label
            )
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

        elif str(p.slice[1])[-8:] == "constant":
            p[0] = p[1]
            if self.symtab.error == True:
                return
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")
        elif p.slice[1].type == "STRING_CONSTANT":
            p[0] = Node(str(p[1]))
            p[0].type = ["str"]

        elif len(p) == 4:
            p[0] = p[2]

    def p_identifier(self, p):
        """identifier : IDENTIFIER"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]["lexeme"]))
        p[0].variables[p[0].label] = []
        p[0].is_var = 1
        self.symtab.insert_symbol(p[1]["lexeme"], p[1]["additional"]["line"])
        self.symtab.modify_symbol(p[1]["lexeme"], "identifier_type", "variable")

        if self.symtab.error == True:
            return

        self.symtab.modify_symbol(p[1]["lexeme"], "temp", p[1]["lexeme"])

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
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
            if p[1] == None or p[1].type == None:
                self.symtab.error = True
                return
            for i in range(len(p[1].type) - 1, 0, -1):
                if p[1].type[i][0] != "[":
                    break
                else:
                    if p[0].dim_list is None:
                        p[0].dim_list = []
                    if len(p[0].dim_list) == 0 and len(p[1].type[i][1:-1]) == 0:
                        p[0].dim_list.append(0)
                    else:
                        try:
                            p[0].dim_list.append(int(p[1].type[i][1:-1]))
                        except:
                            p[0].dim_list.append(p[1].type[i][1:-1])
            if p[0].dim_list is not None:
                p[0].dim_list.reverse()
                p[0].dim_list.append("is_first_access")
                var = p[0].temp.split("(")[0]
                if var == "" or var is None:
                    return
                if var[0] != "-":
                    var = "+" + var
                p[0].address = f"%ebp{var}"
                if var[0] == "-":
                    p[0].temp = p[0].address

        elif len(p) == 3:
            if p[1] == None or p[1].type == None or p[1].type == []:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to increment/decrement the expression at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif (
                p[1].type[0] not in ["char", "short", "int"] and p[1].type[0][-1] != "*"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to increment/decrement "
                    + str(p[1].type[0])
                    + " type expression at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif not p[1].is_terminal == False and p[1].is_var == False:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to increment/decrement the expression at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif p[1].is_var == 0 and p[1].type[0][-1] != "*":
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to increment/decrement the constant at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif p[1].type[0][-1] == "*" and "arr" in p[1].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to increment/decrement on array type at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            else:
                p[0] = Node("Postfix" + str(p[2]), children=[p[1]])
                p[0].type = p[1].type

                if self.symtab.error == True:
                    return

                p[0].var_name = p[1].var_name
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]
                self.three_address_code.emit("=_int", p[0].temp, p[1].temp, "")
                if str(p[2]) == "++":
                    self.three_address_code.emit("+_int", p[1].temp, p[1].temp, f"$1")
                else:
                    self.three_address_code.emit("-_int", p[1].temp, p[1].temp, f"$1")
                p[0].true_list.append(self.three_address_code.next_statement)
                p[0].false_list.append(self.three_address_code.next_statement + 1)
                self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                self.three_address_code.emit("goto", "", "", "")

        elif len(p) == 4:
            if p[2] == ".":
                p3val = p[3]["lexeme"]
                p[3] = Node(str(p3val))
                p[0] = Node(".", children=[p[1], p[3]])
                if p[1] == None or p[1].type == None or p[1].type == []:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Requested an invalid member of object that isn't a structure at Line No.: "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                if "struct" not in p[1].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + f"Invalid request for member of object that is not a structure at line {p.lineno(2)}"
                    )
                    return
                if not hasattr(p[1], "vars"):
                    self.symtab.error = True
                    return

                elif p3val not in p[1].vars:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Requested an invalid member of object that doesn't belong to the structure at Line No.: "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                else:
                    old_type_list = p[1].vars[p3val]["data_type"]
                    narr = 0
                    for i in range(len(old_type_list)):
                        if old_type_list[i][0] == "[" and old_type_list[i][-1] == "]":
                            narr += 1

                    type_list = old_type_list
                    if type_list is None or set(type_list) == {"*"}:
                        type_list = []
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

                    if "struct" in type_list:
                        p[0].type.append("struct")
                        for single_type in type_list:
                            if single_type != "struct":
                                p[0].type.append(single_type)

                    if narr > 0:
                        temp_type = []
                        temp_type.append(p[0].type[0])
                        for i in range(narr):
                            temp_type[0] += " *"

                        for i in range(len(p[0].type)):
                            if i > narr:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type
                        p[0].type.append("arr")
                        for i in range(len(type_list)):
                            if (
                                type_list[len(type_list) - i - 1][0] == "["
                                and type_list[len(type_list) - i - 1][-1] == "]"
                            ):
                                p[0].type.append(type_list[len(type_list) - i - 1])

                    if "void" in type_list:
                        p[0].type.append("void")
                        for single_type in type_list:
                            if single_type != "void":
                                p[0].type.append(single_type)

                    if "*" in type_list:
                        temp_type = []
                        temp_type.append(p[0].type[0])
                        for i in range(1, len(p[0].type)):
                            if p[0].type[i] == "*":
                                temp_type[0] += " *"
                            else:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type

                    if "struct" in p[0].type[0]:
                        strtype = ""
                        if "struct" in p[0].type[0]:
                            strtype = "struct"
                        typet = self.symtab.return_type_tab_entry_su(
                            p[0].type[1], strtype, p.lineno(3)
                        )
                        p[0].vars = typet["vars"]
                    if "struct" not in p[0].type:
                        p[0].is_var = 1
                if self.symtab.error == True:
                    return
                p[0].var_name = p[1].var_name + [p3val]
                try:
                    found, entry = self.symtab.return_sym_tab_entry(
                        p[0].var_name[0], p.lineno(1)
                    )
                except:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid usage of '.' operator at line"
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return
                if found is not None:
                    if p[0].var_name[1] in found["vars"].keys():
                        ptr_flag = 0
                        p[0].temp = p[1].temp
                        if p[0].temp[0] == "(":
                            ptr_flag = 1
                            p0_offset = 0
                        else:
                            p0_offset = int(p[0].temp.split("(")[0])
                        if len(p[0].var_name) == 2:
                            tmp_offset = 0
                            for item in found["vars"]:
                                if item == p[0].var_name[1]:
                                    break
                                tmp_offset += found["vars"][item]["allocated_size"]
                            p0_offset += tmp_offset
                            if ptr_flag == 1:
                                self.three_address_code.emit(
                                    "+_int",
                                    p[0].temp[1:-1],
                                    p[0].temp[1:-1],
                                    f"${p0_offset}",
                                )
                            else:
                                p[0].temp = f"{p0_offset}(%ebp)"
                        else:
                            type_to_check = found["vars"][p[0].var_name[1]]["data_type"]
                            idx = 2
                            while "struct" in type_to_check:
                                tmp_type = copy.deepcopy(type_to_check)
                                tmp_type.remove("struct")
                                if "*" in tmp_type:
                                    tmp_type.remove("*")
                                found2 = self.symtab.return_type_tab_entry_su(
                                    tmp_type[0], "struct"
                                )
                                if idx == len(p[0].var_name) - 1:
                                    tmp_offset = 0
                                    for item in found2["vars"]:
                                        if item == p[0].var_name[idx]:
                                            break
                                        tmp_offset += found2["vars"][item][
                                            "allocated_size"
                                        ]
                                    p0_offset += tmp_offset
                                    if ptr_flag == 1:
                                        self.three_address_code.emit(
                                            "+_int",
                                            p[0].temp[1:-1],
                                            p[0].temp[1:-1],
                                            f"${p0_offset}",
                                        )
                                    else:
                                        p[0].temp = f"{p0_offset}(%ebp)"
                                    break
                                type_to_check = found2["vars"][p[0].var_name[idx]][
                                    "data_type"
                                ]
                                idx += 1

                p[0].true_list.append(self.three_address_code.next_statement)
                p[0].false_list.append(self.three_address_code.next_statement + 1)
                self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                self.three_address_code.emit("goto", "", "", "")

            elif p[2] == "(":
                p[0] = Node("FuncCall", [p[1]])

                if p[1] is None:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to call non-function at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                if p[1].type is None:
                    p[1].type = []
                if "function" not in p[1].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to call non-function at Line No.: "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                elif p[1].parameter_nums != 0:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + str(p[1].parameter_nums)
                        + " parameters are required for calling the function at Line No.:"
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return
                else:
                    p[0].type = p[1].ret_type

                p[0].var_name = p[1].var_name
                if self.symtab.error == True:
                    return
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]
                found, entry = self.symtab.return_sym_tab_entry(p[1].label)
                if ("struct" in found["data_type"]) and ("*" not in found["data_type"]):
                    self.three_address_code.emit(
                        "callq_struct", p[0].temp, p[1].label, "0"
                    )
                elif found["data_type"] == ["void"]:
                    self.three_address_code.emit("callq", "", p[1].label, "0")
                elif ("char" in found["data_type"]) and ("*" not in found["data_type"]):
                    self.three_address_code.emit(
                        "callq_char", p[0].temp, p[1].label, "0"
                    )
                else:
                    self.three_address_code.emit("callq", p[0].temp, p[1].label, "0")
                    p[0].true_list.append(self.three_address_code.next_statement)
                    p[0].false_list.append(self.three_address_code.next_statement + 1)
                    self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                    self.three_address_code.emit("goto", "", "", "")

            elif p[2] == "->":
                p3val = p[3]["lexeme"]
                p[3] = Node(str(p3val))
                p[0] = Node("->", children=[p[1], p[3]])

                if p[1] == None or p[1].type == None or p[1].type == []:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid request for member of object that is not a structure at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                if p[1].type is None:
                    p[1].type = []

                if "struct *" not in p[1].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Requested an invalid member of object which isn't a structure at Line No.: "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif p3val not in p[1].vars:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Requested an invalid member of object which doesn't belong to the structure at Line No.: "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                else:
                    old_type_list = p[1].vars[p3val]["data_type"]
                    narr = 0
                    for i in range(len(old_type_list)):
                        if old_type_list[i][0] == "[" and old_type_list[i][-1] == "]":
                            narr += 1

                    type_list = old_type_list

                    if type_list is None or set(type_list) == {"*"}:
                        type_list = []

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

                    if "struct" in type_list:
                        p[0].type.append("struct")
                        for single_type in type_list:
                            if single_type != "struct":
                                p[0].type.append(single_type)

                    if narr > 0:
                        temp_type = []
                        temp_type.append(p[0].type[0])
                        for i in range(narr):
                            temp_type[0] += " *"

                        for i in range(len(p[0].type)):
                            if i > narr:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type
                        p[0].type.append("arr")
                        for i in range(len(type_list)):
                            if (
                                type_list[len(type_list) - i - 1][0] == "["
                                and type_list[len(type_list) - i - 1][-1] == "]"
                            ):
                                p[0].type.append(type_list[len(type_list) - i - 1])

                    if "void" in type_list:
                        p[0].type.append("void")
                        for single_type in type_list:
                            if single_type != "void":
                                p[0].type.append(single_type)

                    if "*" in type_list:
                        temp_type = []
                        temp_type.append(p[0].type[0])
                        for i in range(1, len(p[0].type)):
                            if p[0].type[i] == "*":
                                temp_type[0] += " *"
                            else:
                                temp_type.append(p[0].type[i])
                        p[0].type = temp_type

                    if "struct" in p[0].type[0]:

                        strtype = ""
                        if "struct" in p[0].type[0]:
                            strtype = "struct"
                        typet = self.symtab.return_type_tab_entry_su(
                            p[0].type[1], strtype, p.lineno(3)
                        )
                        p[0].vars = typet["vars"]

                    if "struct" not in p[0].type:
                        p[0].is_var = True

                if self.symtab.error == True:
                    return

                p[0].var_name = p[1].var_name + [p3val]
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", ["int"])
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(["int"], p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                try:
                    found, entry = self.symtab.return_sym_tab_entry(
                        p[0].var_name[0], p.lineno(1)
                    )
                except:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid usage of '->' operator at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return
                if found is not False:
                    if p[0].var_name[1] in found["vars"].keys():
                        p0_offset = 0
                        if len(p[0].var_name) == 2:
                            tmp_offset = 0
                            for item in found["vars"]:
                                if item == p[0].var_name[1]:
                                    break
                                tmp_offset += found["vars"][item]["allocated_size"]
                            p0_offset += tmp_offset
                            self.three_address_code.emit(
                                "+_int", p[0].temp, p[1].temp, f"${p0_offset}"
                            )
                        else:
                            type_to_check = found["vars"][p[0].var_name[1]]["data_type"]
                            idx = 2
                            while "struct" in type_to_check:
                                tmp_type = copy.deepcopy(type_to_check)
                                tmp_type.remove("struct")
                                if "*" in tmp_type:
                                    tmp_type.remove("*")
                                found2 = self.symtab.return_type_tab_entry_su(
                                    tmp_type[0], "struct"
                                )
                                if idx == len(p[0].var_name) - 1:
                                    tmp_offset = 0
                                    for item in found2["vars"]:
                                        if item == p[0].var_name[idx]:
                                            break
                                        tmp_offset += found2["vars"][item][
                                            "allocated_size"
                                        ]
                                    p0_offset += tmp_offset
                                    self.three_address_code.emit(
                                        "+_int", p[0].temp, p[1].temp, f"${p0_offset}"
                                    )
                                    break
                                type_to_check = found2["vars"][p[0].var_name[idx]][
                                    "data_type"
                                ]
                                idx += 1

                p[0].temp = f"({p[0].temp})"
                p[0].true_list.append(self.three_address_code.next_statement)
                p[0].false_list.append(self.three_address_code.next_statement + 1)
                self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                self.three_address_code.emit("goto", "", "", "")

        elif len(p) == 5:
            if p[2] == "(":
                p[0] = Node("FuncCall", [p[1], p[3]])
                if (
                    p[1] is None
                    or p[1].type is None
                    or p[1].parameter_nums is None
                    or p[3] is None
                    or p[3].parameter_nums is None
                    or p[1].type == []
                    or p[1].parameters is None
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Cannot perform function call at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                elif "function" not in p[1].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Cannot call non-function at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                elif p[3].parameter_nums != p[1].parameter_nums:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Incorrect number of parameters (given: "
                        + str(p[3].parameter_nums)
                        + ", required: "
                        + str(p[1].parameter_nums)
                        + ") at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return
                else:
                    ctr = -1
                    for param in p[1].parameters:
                        ctr += 1
                        entry = param
                        isarr = 0
                        for i in range(len(entry["data_type"])):
                            if (
                                entry["data_type"][i][0] == "["
                                and entry["data_type"][i][-1] == "]"
                            ):
                                isarr += 1

                        type_list = entry["data_type"]
                        if "unsigned" in type_list or "signed" in type_list:
                            if (
                                "bool" not in type_list
                                and "char" not in type_list
                                and "short" not in type_list
                            ):
                                type_list.append("int")
                        paramtype = []

                        if "int" in type_list:
                            paramtype.append("int")
                            for single_type in type_list:
                                if single_type != "int":
                                    paramtype.append(single_type)

                        elif "short" in type_list:
                            paramtype.append("short")
                            for single_type in type_list:
                                if single_type != "short":
                                    paramtype.append(single_type)

                        elif "char" in type_list:
                            paramtype.append("char")
                            for single_type in type_list:
                                if single_type != "char":
                                    paramtype.append(single_type)

                        elif "bool" in type_list:
                            paramtype.append("bool")
                            for single_type in type_list:
                                if single_type != "bool":
                                    paramtype.append(single_type)

                        elif "str" in type_list:
                            paramtype.append("str")
                            for single_type in type_list:
                                if single_type != "str":
                                    paramtype.append(single_type)

                        elif "float" in type_list:
                            paramtype.append("float")
                            for single_type in type_list:
                                if single_type != "float":
                                    paramtype.append(single_type)

                        if "struct" in type_list:
                            paramtype.append("struct")
                            for single_type in type_list:
                                if single_type != "struct":
                                    paramtype.append(single_type)

                        if isarr > 0:
                            temp_type = []
                            temp_type.append(paramtype[0])
                            for i in range(isarr):
                                temp_type[0] += " *"

                            for i in range(len(paramtype)):
                                if i > isarr:
                                    temp_type.append(paramtype[i])
                            paramtype = temp_type
                            paramtype.append("arr")
                            for i in range(len(type_list)):
                                if (
                                    type_list[len(type_list) - i - 1][0] == "["
                                    and type_list[len(type_list) - i - 1][-1] == "]"
                                ):
                                    paramtype.append(type_list[len(type_list) - i - 1])

                        if "void" in type_list:
                            paramtype.append("void")
                            for single_type in type_list:
                                if single_type != "void":
                                    paramtype.append(single_type)

                        if "*" in type_list:
                            temp_type = []
                            temp_type.append(paramtype[0])
                            for i in range(1, len(paramtype)):
                                if paramtype[i] == "*":
                                    temp_type[0] += " *"
                                else:
                                    temp_type.append(paramtype[i])
                            paramtype = temp_type

                        if (
                            p[3] is None
                            or paramtype is None
                            or p[3].parameters[ctr] is None
                            or paramtype == []
                            or p[3].parameters[ctr] == []
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Cannot call function at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if ("struct" in paramtype) and (
                            "struct" not in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Need struct value "
                                + str(paramtype)
                                + " to call function but got non- struct type "
                                + str(p[3].parameters[ctr])
                                + " at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if ("struct" not in paramtype) and (
                            "struct" in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Need non-struct value "
                                + str(paramtype)
                                + " to call function but got struct type "
                                + str(p[3].parameters[ctr])
                                + " at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if (
                            "struct" in paramtype
                            and "struct" in p[3].parameters[ctr]
                            and paramtype[1] != p[3].parameters[ctr][1]
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Incompatible struct types to call function at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if (
                            paramtype[0] in ["bool", "char", "short", "int", "float"]
                            and p[3].parameters[ctr][0]
                            not in ["bool", "char", "short", "int", "float"]
                            and p[3].parameters[ctr][0][-1] != "*"
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid parameter type to call function at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if (
                            paramtype[0]
                            not in ["bool", "char", "short", "int", "float"]
                            and paramtype[0][-1] != "*"
                            and p[3].parameters[ctr][0]
                            in ["bool", "char", "short", "int", "float"]
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid parameter type to call function at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if (
                            paramtype[0][-1] == "*"
                            and p[3].parameters[ctr][0]
                            not in ["bool", "char", "short", "int"]
                            and p[3].parameters[ctr][0][-1] != "*"
                            and "str" not in p[3].parameters[ctr]
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Incompatible assignment between pointer and "
                                + str(p[3].parameters[ctr])
                                + " at line "
                                + str(p.lineno(2))
                                + bcolors.ENDC
                            )
                            return

                        if self.symtab.error == True:
                            return

                        isin = True
                        p3totype = []
                        for single_type in paramtype:
                            if (
                                single_type != "arr"
                                and single_type[0] != "["
                                and single_type[-1] != "]"
                            ):
                                p3totype.append(single_type)
                                if single_type not in p[3].parameters[ctr]:
                                    isin = False

                        if isin == False:

                            p3temp = self.three_address_code.create_temp_var()
                            self.symtab.insert_symbol(p3temp, 0)
                            self.symtab.modify_symbol(p3temp, "data_type", p3totype)
                            self.symtab.modify_symbol(p3temp, "identifier_type", "TEMP")
                            self.symtab_size_update(p3totype, p3temp)
                            if self.symtab.is_global(p3temp):
                                self.symtab.modify_symbol(
                                    p3temp, "variable_scope", "Global"
                                )
                            else:
                                self.symtab.modify_symbol(
                                    p3temp, "variable_scope", "Local"
                                )
                                found, entry = self.symtab.return_sym_tab_entry(p3temp)
                                var_size = found["allocated_size"]
                                if found["variable_scope"] == "Local":
                                    if found["offset"] > 0:
                                        self.symtab.modify_symbol(
                                            p3temp,
                                            "temp",
                                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                        )
                                    else:
                                        self.symtab.modify_symbol(
                                            p3temp,
                                            "temp",
                                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                        )
                                p3temp = found["temp"]

                            currtype = []
                            for single_type in p[3].parameters[ctr]:
                                if (
                                    single_type != "arr"
                                    and single_type[0] != "["
                                    and single_type[-1] != "]"
                                ):
                                    currtype.append(single_type)
                            currtyprstr = "," + " ".join(currtype).replace(" ", "_")

                            self.three_address_code.emit(
                                "cast",
                                p3temp,
                                p[3].argument_list[ctr][0],
                                " ".join(p3totype).replace(" ", "_") + currtyprstr,
                            )
                            p[3].argument_list[ctr] = [p3temp, p3totype]

                    p[0].type = p[1].ret_type

                p[0].var_name = p[1].var_name
                if self.symtab.error == True:
                    return

                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                math_funcs_list_single = [
                    "sqrt",
                    "ceil",
                    "floor",
                    "fabs",
                    "log",
                    "log10",
                    "exp",
                    "cos",
                    "sin",
                    "acos",
                    "asin",
                    "tan",
                    "atan",
                ]
                math_funcs_list_double = ["pow", "fmod"]
                for arg in reversed(p[3].argument_list):
                    if p[1].label == "printf":
                        if arg[0][0] == "$'":
                            self.three_address_code.emit("param", arg[0], "", "")
                        else:
                            if "float" in arg[1]:
                                self.three_address_code.emit(
                                    "printf_push_float", arg[0]
                                )
                            elif "char" in arg[1]:
                                self.three_address_code.emit("printf_push_char", arg[0])
                            else:
                                self.three_address_code.emit("param", arg[0], "", "")
                    elif p[1].label in math_funcs_list_single:
                        if "float" in arg[1]:
                            self.three_address_code.emit("math_func_push_float", arg[0])
                        elif "int" in arg[1]:
                            self.three_address_code.emit("math_func_push_int", arg[0])
                        elif "char" in arg[1]:
                            self.three_address_code.emit("push_char", arg[0])
                        else:
                            self.three_address_code.emit("math_func_push_int", arg[0])
                    elif p[1].label in math_funcs_list_double:
                        if "float" in arg[1]:
                            self.three_address_code.emit("pow_func_push_float", arg[0])
                        elif "int" in arg[1]:
                            self.three_address_code.emit("pow_func_push_int", arg[0])
                        elif "char" in arg[1]:
                            self.three_address_code.emit("push_char", arg[0])
                        else:
                            self.three_address_code.emit("pow_func_push_int", arg[0])
                    else:
                        new_p2_list = []
                        for elem in arg[1]:
                            if elem != "arr" and elem[0] != "[" and elem[-1] != "]":
                                new_p2_list = new_p2_list + elem.split(" ")
                        req_type = "void"
                        if "char" in arg[1]:
                            self.three_address_code.emit("push_char", arg[0])
                        else:
                            if "*" in new_p2_list:
                                req_type = "ptr"
                            else:
                                req_type = " ".join(new_p2_list)
                            if req_type in datatype_size:
                                if "struct" in new_p2_list and "*" not in new_p2_list:
                                    to_print = self.recurse_struct(new_p2_list, arg[0])
                                    to_print.reverse()
                                    for item in to_print:
                                        if item[0] == 1:
                                            self.three_address_code.emit(
                                                "push_char", item[1]
                                            )
                                        else:
                                            self.three_address_code.emit(
                                                "param", item[1], "$4"
                                            )
                                else:
                                    self.three_address_code.emit(
                                        "param", arg[0], f"${datatype_size[req_type]}"
                                    )
                            else:
                                self.symtab.error = True
                                print(
                                    bcolors.FAIL
                                    + "1 Invalid type given in line number "
                                    + str(p.lineno(4))
                                    + bcolors.ENDC
                                )

                found, entry = self.symtab.return_sym_tab_entry(p[1].label)
                if ("struct" in found["data_type"]) and ("*" not in found["data_type"]):
                    self.three_address_code.emit(
                        "callq_struct", p[0].temp, p[1].label, len(p[3].argument_list)
                    )
                elif found["data_type"] == ["void"]:
                    self.three_address_code.emit(
                        "callq", "", p[1].label, len(p[3].argument_list)
                    )
                elif ("char" in found["data_type"]) and ("*" not in found["data_type"]):
                    self.three_address_code.emit(
                        "callq_char", p[0].temp, p[1].label, len(p[3].argument_list)
                    )
                else:
                    self.three_address_code.emit(
                        "callq", p[0].temp, p[1].label, len(p[3].argument_list)
                    )
                    p[0].true_list.append(self.three_address_code.next_statement)
                    p[0].false_list.append(self.three_address_code.next_statement + 1)
                    self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                    self.three_address_code.emit("goto", "", "", "")

            elif p[2] == "[":
                if (
                    p[3] is None
                    or p[3].type is None
                    or p[3].type == []
                    or p[1] is None
                    or p[1].type is None
                    or p[1].type == []
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid call to access array element at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                flag = 0
                if p[3].type[0] in ["bool", "char", "short", "int"]:
                    flag = 1

                if flag == 0:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid array subscript of type "
                        + str(p[3].type)
                        + " at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return
                else:
                    if p[1].type[0][-1] != "*":
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Expression of type "
                            + str(p[1].type)
                            + " not an array at line "
                            + str(p.lineno(2))
                            + bcolors.ENDC
                        )
                        return
                    else:
                        p[0] = Node("array_subscript", [p[1], p[3]])
                        p[0].type = []
                        for single_type in p[1].type:
                            if single_type[0] == "[" and single_type[-1] == "]":
                                pass
                            else:
                                p[0].type.append(single_type)

                        p[0].type[0] = p[0].type[0][0:-2]
                        p[0].array_level = p[1].array_level - 1

                        if p[0].type[0][-1] != "*":
                            p[0].is_var = 1
                        elif "arr" not in p[0].type:
                            p[0].is_var = 1
                        for i in range(len(p[1].type)):
                            if p[1].type[i][0] == "[" and p[1].type[i][-1] == "]":
                                p[0].type.append(p[1].type[i])

                        if "struct" in p[0].type[0]:
                            p[0].vars = p[1].vars

                p[0].var_name = p[1].var_name
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", ["int"])
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(["int"], p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                p[0].dim_list = p[1].dim_list
                is_first_access = False

                if p[0].dim_list is None:

                    arrtemp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(arrtemp, 0)
                    self.symtab.modify_symbol(arrtemp, "data_type", ["int"])
                    self.symtab.modify_symbol(arrtemp, "identifier_type", "TEMP")
                    self.symtab_size_update(["int"], arrtemp)
                    if self.symtab.is_global(arrtemp):
                        self.symtab.modify_symbol(arrtemp, "variable_scope", "Global")
                    else:
                        self.symtab.modify_symbol(arrtemp, "variable_scope", "Local")
                        found, entry = self.symtab.return_sym_tab_entry(arrtemp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":
                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    arrtemp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    arrtemp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        arrtemp = found["temp"]

                    var = 0
                    if "*" in (" ".join(p[0].type)).split(" "):
                        var = 4
                    else:
                        var = datatype_size[" ".join(p[0].type)]

                    self.three_address_code.emit("*_int", arrtemp, p[3].temp, f"${var}")

                    if p[1].address is not None:
                        var = p[1].address.split("(")[0]
                        if var[0] != "-":
                            var = "+" + var
                        self.three_address_code.emit(
                            "+_int", p[0].temp, f"%ebp{var}", arrtemp
                        )
                    else:
                        self.three_address_code.emit(
                            "+_int", p[0].temp, p[1].temp, arrtemp
                        )

                    self.three_address_code.emit("UNARY*", p[0].temp, p[0].temp, "")

                    p[0].temp = f"({p[0].temp})"

                    p[0].true_list.append(self.three_address_code.next_statement)
                    p[0].false_list.append(self.three_address_code.next_statement + 1)
                    self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                    self.three_address_code.emit("goto", "", "", "")
                    p[0].address = None

                else:
                    if (
                        len(p[0].dim_list) > 0
                        and p[0].dim_list[-1] == "is_first_access"
                    ):
                        is_first_access = True
                        p[0].dim_list.pop()

                    if is_first_access:
                        self.three_address_code.emit("=_int", p[0].temp, p[3].temp, "")
                    else:
                        if len(p[0].dim_list) == 0:
                            self.symtab.error = True
                            return
                        curDimension = p[0].dim_list[-1]
                        self.three_address_code.emit(
                            "*_int", p[0].temp, p[1].temp, f"${curDimension}"
                        )
                        self.three_address_code.emit(
                            "+_int", p[0].temp, p[0].temp, p[3].temp
                        )

                    p[0].dim_list.pop()

                    if len(p[0].dim_list) == 0:
                        if p[0].type[0][-1] == "*":
                            self.three_address_code.emit(
                                "*_int", p[0].temp, p[0].temp, "$4"
                            )
                        else:
                            if "struct" == p[0].type[0]:
                                strtype = p[0].type[0] + " " + p[0].type[1]
                                self.three_address_code.emit(
                                    "*_int",
                                    p[0].temp,
                                    p[0].temp,
                                    f"${datatype_size[ strtype ]}",
                                )
                            else:
                                self.three_address_code.emit(
                                    "*_int",
                                    p[0].temp,
                                    p[0].temp,
                                    f"${datatype_size[p[0].type[0]]}",
                                )

                        if p[1].address is None or p[1].address == "":
                            self.symtab.error = True
                            return
                        var = p[1].address[4]
                        p1_addr = p[1].address
                        if var == "+":
                            p1_addr = f"{p[1].address[5:]}(%ebp)"
                        self.three_address_code.emit(
                            "+_int", p[0].temp, p1_addr, p[0].temp
                        )
                        p[0].temp = f"({p[0].temp})"

                        p[0].true_list.append(self.three_address_code.next_statement)
                        p[0].false_list.append(
                            self.three_address_code.next_statement + 1
                        )
                        self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                        self.three_address_code.emit("goto", "", "", "")

                p[0].address = p[1].address

    def p_argument_expression_list(self, p):
        """
        argument_expression_list : assignment_expression
                                | argument_expression_list ',' assignment_expression
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
            if p[1] is None:
                return
            p[0].parameter_nums = 1
            p[0].parameters = []
            p[0].parameters.append(p[1].type)
            p[0].argument_list = [[p[1].temp, p[1].type]]

        elif len(p) == 4:
            p[0] = Node(",", [p[1], p[3]])
            if (
                p[1] is None
                or p[1].parameter_nums is None
                or p[1].argument_list is None
                or p[1].parameters is None
                or p[3] is None
                or p[3].temp is None
                or p[3].type is None
                or p[3].type == []
            ):
                return
            p[0].parameter_nums = p[1].parameter_nums + 1
            p[0].parameters = p[1].parameters
            p[0].parameters.append(p[3].type)
            p[0].argument_list = p[1].argument_list
            p[0].argument_list.append([p[3].temp, p[3].type])

    def p_unary_expression(self, p):
        """
        unary_expression : postfix_expression
                        | INC_OP unary_expression
                        | DEC_OP unary_expression
                        | unary_operator cast_expression
                        | SIZEOF unary_expression
                        | SIZEOF '(' type_name ')'
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 3:
            if p[1] == "++" or p[1] == "--":

                if p[2] is None or p[2].type is None or p[2].type == []:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to increment/decrement the value of expression at Line No.: "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )

                elif (
                    p[2].type[0] not in ["int", "char", "short"]
                    and p[2].type[0][-1] != "*"
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to use increment/decrement operator on a non-integral at Line No.: "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                elif p[2].is_terminal == False and p[2].is_var == False:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to use increment/decrement operator on the expression at Line No.: "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                elif p[2].is_var == False and p[2].type[0][-1] != "*":
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to use increment/decrement operator on a constant at Line No.: "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                elif p[2].type[0][-1] == "*" and "arr" in p[2].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Unable to use increment/decrement operator on array at Line No.: "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                else:
                    p[0] = Node("Prefix" + str(p[1]), children=[p[2]])
                    if p[2].type is None:
                        p[2].type = []
                    p[0].type = p[2].type

                if self.symtab.error == True:
                    return

                p[0].var_name = p[2].var_name
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]
                self.three_address_code.emit("=_int", p[0].temp, p[2].temp, "")
                if str(p[1]) == "++":
                    self.three_address_code.emit("+_int", p[0].temp, p[0].temp, f"$1")
                    self.three_address_code.emit("+_int", p[2].temp, p[2].temp, f"$1")
                else:
                    self.three_address_code.emit("-_int", p[0].temp, p[0].temp, f"$1")
                    self.three_address_code.emit("-_int", p[2].temp, p[2].temp, f"$1")
                p[0].true_list.append(self.three_address_code.next_statement)
                p[0].false_list.append(self.three_address_code.next_statement + 1)
                self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                self.three_address_code.emit("goto", "", "", "")

            elif p[1] == "sizeof":
                p[0] = Node("SIZEOF", [p[2]])
                p[0].type = ["int"]
                if self.symtab.error == True:
                    return
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                p[0].var_name = p[2].var_name
                if p[2].type is None or p[2].type == []:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + f"2 Invalid type given in line number {p.lineno(1)}"
                    )
                    return
                new_p2_list = []
                multiplier = 1
                for elem in p[2].type:
                    if elem != "arr" and elem[0] != "[" and elem[-1] != "]":
                        new_p2_list = new_p2_list + elem.split(" ")

                    elif elem[0] == "[" and elem[-1] == "]":
                        multiplier *= int(elem[1:-1])

                req_type = "void"
                if "*" in new_p2_list:
                    req_type = "ptr"
                else:
                    req_type = " ".join(new_p2_list)
                if req_type in datatype_size:
                    self.three_address_code.emit(
                        "=_int", p[0].temp, f"${multiplier*datatype_size[req_type]}"
                    )
                else:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + f"3 Invalid type given in line number {p.lineno(1)}"
                    )
                    return
                p[0].true_list.append(self.TAC.nextstat)
                p[0].false_list.append(self.TAC.nextstat + 1)
                self.TAC.emit("ifnz goto", "", p[0].temp, "")
                self.TAC.emit("goto", "", "", "")

            else:
                p[0] = p[1]
                if (p[2] is not None) and (p[2].node is not None):
                    p[0].children.append(p[2])
                    graph.add_edge(p[0].node, p[2].node)

                    if p[2].type is None or p[2].type == []:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Unable to perform a unary operation at Line No.: "
                            + str(p.lineno(1))
                            + bcolors.ENDC
                        )
                        return

                    if p[1].label[-1] in ["+", "-", "!"]:
                        if (
                            p[2].type[0] in ["short", "int", "char", "float"]
                            and p[2].type != []
                        ):
                            p[0].type = [p[2].type[0]]
                            if (
                                p[2].type[0] in ["char", "short", "int"]
                                or p[1].label[-1] == "!"
                            ):
                                p[0].type = ["int"]
                            else:
                                pass

                            if p[0].label[-1] != "!":
                                if p[0].type != p[2].type:
                                    p[2].totype = p[0].type
                                    p2str = "to"
                                    for single_type in p[0].type:
                                        p2str += "_" + single_type
                                    p2 = Node(p2str, [p[2]])
                                else:
                                    p[2].totype = None
                                    p2 = p[2]

                                for single_type in p[0].type:
                                    p[0].label += "_" + single_type

                                p[0].label = p[0].label.replace(" ", "_")
                                p[0].node.attr["label"] = p[0].label

                        else:
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )

                    elif p[1].label[-1] == "~":
                        if len(p[2].type) > 0 and p[2].type[0] in [
                            "bool",
                            "char",
                            "short",
                            "int",
                        ]:
                            p[0].type = ["int"]
                            if p[0].type != p[2].type:
                                p[2].totype = p[0].type
                                p2str = "to"
                                for single_type in p[0].type:
                                    p2str += "_" + single_type
                                p2 = Node(p2str, [p[2]])
                            else:
                                p[2].totype = None
                                p2 = p[2]

                            for single_type in p[0].type:
                                p[0].label += "_" + single_type
                            p[0].label = p[0].label.replace(" ", "_")
                            p[0].node.attr["label"] = p[0].label

                        else:
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )

                    elif p[1].label[-1] == "*":
                        if p[2] is None or p[2].type is None or p[2].type == []:
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid usage of unary operator * at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )
                            return
                        elif (
                            len(p[2].type) > 0
                            and p[2].type[0][-1] != "*"
                            and ("*" not in p[2].type)
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid usage of unary operator for operand "
                                + str(p[2].type)
                                + " type at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )
                            return
                        else:
                            p[0].is_var = 1
                            p[0].type = p[2].type
                            p[0].type[0] = p[0].type[0][:-1]
                            if len(p[0].type) > 0 and p[0].type[0][-1] == " ":
                                p[0].type[0] = p[0].type[0][:-1]
                            try:
                                p[0].vars = p[2].vars
                            except:
                                pass

                    elif p[1].label[-1] == "&":

                        if p[2] is None or p[2].type is None or p[2].type == []:
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Invalid usage of unary operator * at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )
                            return
                        elif (
                            len(p[2].type) > 0
                            and "struct" != p[2].type[0]
                            and p[2].is_var == 0
                        ):
                            self.symtab.error = True
                            print(
                                bcolors.FAIL
                                + "Unable to find a pointer for non-variable type : "
                                + str(p[2].type)
                                + " at Line No.: "
                                + str(p.lineno(1))
                                + bcolors.ENDC
                            )
                            return
                        elif len(p[2].type) > 0 and "struct" == p[2].type[0]:
                            p[0].type = p[2].type
                            p[0].type[0] += " *"
                            p[0].vars = p[2].vars

                        else:
                            p[0].type = ["int", "unsigned"]

                    try:
                        p[0].insert_edge([p2])
                    except:
                        p[0].insert_edge([p[2]])

                if self.symtab.error == True:
                    return

                if p[2].totype is not None and p[2].totype != p[2].type:

                    p2.temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(p2.temp, 0)
                    self.symtab.modify_symbol(p2.temp, "data_type", p[2].totype)
                    self.symtab.modify_symbol(p2.temp, "identifier_type", "TEMP")
                    self.symtab_size_update(p[2].totype, p2.temp)
                    if self.symtab.is_global(p2.temp):
                        self.symtab.modify_symbol(p2.temp, "variable_scope", "Global")
                    else:
                        self.symtab.modify_symbol(p2.temp, "variable_scope", "Local")
                        found, entry = self.symtab.return_sym_tab_entry(p2.temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":

                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    p2.temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    p2.temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        p2.temp = found["temp"]

                    currtype = []
                    for single_type in p[2].type:
                        if (
                            single_type != "arr"
                            and single_type[0] != "["
                            and single_type[-1] != "]"
                        ):
                            currtype.append(single_type)
                    cstr = "," + " ".join(currtype).replace(" ", "_")

                    self.three_address_code.emit(
                        "cast",
                        p2.temp,
                        p[2].temp,
                        " ".join(p[2].totype).replace(" ", "_") + cstr,
                    )

                else:

                    try:
                        p2.temp = p[2].temp
                    except:
                        pass

                p[0].var_name = p[2].var_name
                p[0].temp = self.three_address_code.create_temp_var()

                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")

                if p[1].label == "UNARY*":

                    try:
                        found, entry = self.symtab.return_sym_tab_entry(
                            p[2].var_name[0]
                        )
                    except:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + f"Invalid usage of UNARY* operator at line {p[1].lineno}"
                        )
                        return
                    var_size = found["allocated_size"]
                    self.symtab.modify_symbol(p[0].temp, "allocated_size", var_size)
                else:
                    self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]
                try:
                    self.three_address_code.emit(p[0].label, p[0].temp, p2.temp)
                except:
                    self.three_address_code.emit(p[0].label, p[0].temp, p[2].temp)

                if p[1].label == "UNARY*":
                    p[0].temp = f"({p[0].temp})"

                if p[1].label[-1] == "!":
                    p[0].true_list = p[1].false_list
                    p[0].false_list = p[1].true_list
                else:
                    p[0].true_list.append(self.three_address_code.next_statement)
                    p[0].false_list.append(self.three_address_code.next_statement + 1)
                    self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
                    self.three_address_code.emit("goto", "", "", "")

        elif len(p) == 5:
            p[0] = Node("SIZEOF", [p[3]])
            p[0].type = ["int"]
            if self.symtab.error == True:
                return

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]

            if p[3].type is None or p[3].type == []:
                self.symtab.error = True
                print(
                    bcolors.FAIL + f"4 Invalid type given in line number {p.lineno(1)}"
                )
                return
            req_type = "void"
            if "*" in p[3].type:
                req_type = "ptr"
            else:
                req_type = " ".join(p[3].type)

            if req_type in datatype_size:
                self.three_address_code.emit(
                    "=_int", p[0].temp, f"${datatype_size[req_type]}"
                )
            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL + f"5 Invalid type given in line number {p.lineno(1)}"
                )
                return
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_unary_operator(self, p):
        """
        unary_operator : '&'
                    | '*'
                    | '+'
                    | '-'
                    | '~'
                    | '!'
        """
        if self.error == True:
            return
        p[0] = Node("UNARY" + str(p[1]))
        p[0].lineno = p.lineno(1)

    def p_cast_expression(self, p):
        """
        cast_expression : unary_expression
                        | '(' type_name ')' cast_expression
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            chd = [p[2], p[4]]
            p[0] = Node("CAST", chd)
            if (
                p[2] is None
                or p[2].type is None
                or p[2].type == []
                or p[4] is None
                or p[4].type is None
                or p[4].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform casting at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
                return
            temp_type_list = []
            temp2_type_list = []
            for single_type in p[2].type:
                if len(single_type) > 0 and single_type != "*":
                    temp_type_list.append(single_type)
                    if single_type[0] != "[" or single_type[-1] != "]":
                        temp2_type_list.append(single_type)
                if (
                    len(single_type) > 0
                    and single_type[0] == "["
                    and single_type[-1] == "]"
                ):
                    if single_type[1:-1] == "":
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot have empty indices for array declarations at line "
                            + str(p.lineno(1))
                            + bcolors.ENDC
                        )
                        return
                    elif int(single_type[1:-1]) <= 0:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot have non-positive integers for array declarations at line "
                            + str(p.lineno(1))
                            + bcolors.ENDC
                        )
                        return
            if len(temp2_type_list) != len(set(temp2_type_list)):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "variables cannot have duplicating type of declarations at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
                return
            if "unsigned" in p[2].type and "signed" in p[2].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Variable cannot be both signed and unsigned at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
                return
            else:
                data_type_count = 0
                if p[2].type is None:
                    p[2].type = []
                if (
                    "int" in p[2].type
                    or "short" in p[2].type
                    or "unsigned" in p[2].type
                    or "signed" in p[2].type
                ):
                    data_type_count += 1
                if "char" in p[2].type:
                    data_type_count += 1
                if "bool" in p[2].type:
                    data_type_count += 1
                if "float" in p[2].type:
                    data_type_count += 1
                if "void" in p[2].type:
                    data_type_count += 1
                if "struct" in p[2].type:
                    data_type_count += 1
                if data_type_count > 1:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Two or more conflicting data types specified for variable at line "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                    return

            isarr = 0
            for i in range(len(p[2].type)):
                if (
                    len(p[2].type[i]) > 0
                    and p[2].type[i][0] == "["
                    and p[2].type[i][-1] == "]"
                ):
                    isarr += 1

            type_list = p[2].type
            if type_list is None:
                type_list = []
            p[0].type = []

            if "unsigned" in type_list or "signed" in type_list:
                if (
                    "bool" not in type_list
                    and "char" not in type_list
                    and "short" not in type_list
                ):
                    type_list.append("int")

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

            if "struct" in type_list:
                p[0].type.append("struct")
                for single_type in type_list:
                    if single_type != "struct":
                        p[0].type.append(single_type)

            if isarr > 0:
                temp_type = []
                temp_type.append(p[0].type[0])
                for i in range(isarr):
                    temp_type[0] += " *"
                for i in range(len(p[0].type)):
                    if i > isarr:
                        temp_type.append(p[0].type[i])
                p[0].type = temp_type
                p[0].type.append("arr")
                for i in range(len(type_list)):
                    if (
                        type_list[len(type_list) - i - 1][0] == "["
                        and type_list[len(type_list) - i - 1][-1] == "]"
                    ):
                        p[0].type.append(type_list[len(type_list) - i - 1])

            if "void" in type_list:
                p[0].type.append("void")
                for single_type in type_list:
                    if single_type != "void":
                        p[0].type.append(single_type)

            if "*" in type_list:
                temp_type = []
                temp_type.append(p[0].type[0])
                for i in range(1, len(p[0].type)):
                    if p[0].type[i] == "*":
                        temp_type[0] += " *"
                    else:
                        temp_type.append(p[0].type[i])
                p[0].type = temp_type

            if p[2].type is None or p[4].type is None or p[0].type is None:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform casting at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
            elif (
                "struct" in p[2].type
                and "*" not in p[2].type
                and "struct" not in p[4].type
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot cast non-struct value "
                    + str(p[4].type)
                    + " to struct type "
                    + str(p[2].type)
                    + " at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                "struct" in p[2].type
                and "struct" in p[4].type
                and p[4].type[1] not in p[2].type
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible struct types to perform casting at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                p[0].type[0] in ["bool", "char", "short", "int", "float"]
                and p[4].type[0] not in ["bool", "char", "short", "int", "float"]
                and p[4].type[0][-1] != "*"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Type mismatch while casting value at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                "*" in p[2].type
                and p[4].type[0] not in ["bool", "char", "short", "int"]
                and p[4].type[0][-1] != "*"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible casting between pointer and "
                    + str(p[4].type)
                    + " at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
            p[4].totype = p[0].type

            if self.symtab.error == True:
                return

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":
                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]

            currtype = []
            for single_type in p[4].type:
                if (
                    single_type != "arr"
                    and single_type[0] != "["
                    and single_type[-1] != "]"
                ):
                    currtype.append(single_type)
            cstr = "," + " ".join(currtype).replace(" ", "_")
            self.three_address_code.emit(
                "cast",
                p[0].temp,
                p[4].temp,
                " ".join(p[4].totype).replace(" ", "_") + cstr,
            )
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_multiplicative_expression(self, p):
        """
        multiplicative_expression : cast_expression
                                | multiplicative_expression '*' cast_expression
                                | multiplicative_expression '/' cast_expression
                                | multiplicative_expression '%' cast_expression
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.error = True
                print(
                    bcolors.FAIL
                    + "Unable to multiply the two expressions at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif str(p[2]) == "%":
                if p[1].type[0] not in ["bool", "char", "short", "int"] or p[3].type[
                    0
                ] not in ["bool", "char", "short", "int"]:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Cannot perform modulo operation between expressions of type {p[1].type} and {p[3].type} only line {p.lineno(2)}"
                        + bcolors.ENDC
                    )

                    return
                p0type = ["int"]
                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p0type.append("unsigned")
                p0typestr = "to"
                for single_type in p0type:
                    p0typestr += "_" + single_type
                p0typestr = p0typestr.replace(" ", "_")

                flag = True
                for i in p0type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p0type
                    p1 = Node(p0typestr, [p[1]])
                else:
                    p1 = p[1]

                flag = True
                for i in p0type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p0type
                    p3 = Node(p0typestr, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type

                p[0].label = p[0].label + "_" + p[0].type[0]

                if len(p[0].type) == 2:
                    p[0].label = p[0].label + "_" + p[0].type[1]

                p[0].label = p[0].label.replace(" ", "_")

                p[0].node.attr["label"] = p[0].label

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in ["bool", "char", "short", "int", "float"]
                and len(p[3].type) > 0
                and p[3].type[0] in ["bool", "char", "short", "int", "float"]
            ):
                p0type = []
                p0type.append(
                    ["bool", "char", "short", "int", "float"][
                        max(
                            ["bool", "char", "short", "int", "float"].index(
                                p[1].type[0]
                            ),
                            ["bool", "char", "short", "int", "float"].index(
                                p[3].type[0]
                            ),
                        )
                    ]
                )
                if ("unsigned" in p[1].type or "unsigned" in p[3].type) and max(
                    ["bool", "char", "short", "int", "float"].index(p[1].type[0]),
                    ["bool", "char", "short", "int", "float"].index(p[3].type[0]),
                ) <= 4:
                    p0type.append("unsigned")
                p0typestr = "to"
                for single_type in p0type:
                    p0typestr += "_" + single_type
                p0typestr = p0typestr.replace(" ", "_")

                isIn = True
                for single_type in p0type:
                    if single_type not in p[1].type:
                        isIn = False
                if isIn == False:
                    p[1].totype = p0type
                    p1 = Node(p0typestr, [p[1]])
                else:
                    p1 = p[1]
                isIn = True
                for single_type in p0type:
                    if single_type not in p[3].type:
                        isIn = False
                if isIn == False:
                    p[3].totype = p0type
                    p3 = Node(p0typestr, [p[3]])
                else:
                    p3 = p[3]
                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type

                p[0].label = p[0].label + "_" + p[0].type[0]
                if len(p[0].type) == 2:
                    p[0].label = p[0].label + "_" + p[0].type[1]
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to multiply two incompatible type of expressions ("
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + ") at Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return
            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]

                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]
                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":
                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_additive_expression(self, p):
        """
        additive_expression : multiplicative_expression
                            | additive_expression '+' multiplicative_expression
                            | additive_expression '-' multiplicative_expression
        """
        if self.error == True:
            return
        temp_list_aa = ["bool", "char", "short", "int", "float"]
        temp_list_ii = ["bool", "char", "short", "int"]
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform additive operation between expressions on line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif (
                len(p[1].type) > 0
                and p[1].type[0] in ["bool", "char", "short", "int", "float"]
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list_aa
            ):
                p0type = []
                p0type.append(
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
                    p0type.append("unsigned")

                p0typestr = "to"
                for single_type in p0type:
                    p0typestr += "_" + single_type

                p0typestr = p0typestr.replace(" ", "_")

                isIn = True
                for single_type in p0type:
                    if single_type not in p[1].type:
                        isIn = False
                if isIn == False:
                    p[1].totype = p0type
                    p1 = Node(p0typestr, [p[1]])
                else:
                    p1 = p[1]

                isIn = True
                for single_type in p0type:
                    if single_type not in p[3].type:
                        isIn = False
                if isIn == False:
                    p[3].totype = p0type
                    p3 = Node(p0typestr, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p[0].label + "_" + p[0].type[0]

                if len(p[0].type) == 2:
                    p[0].label = p[0].label + "_" + p[0].type[1]
                p[0].label = p[0].label.replace(" ", "_")

                p[0].node.attr["label"] = p[0].label

            elif (
                len(p[1].type) > 0
                and p[1].type[0][-1] == "*"
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list_ii
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Pointer Arithmetic Not allowed at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif (
                len(p[3].type) > 0
                and p[3].type[0][-1] == "*"
                and len(p[1].type) > 0
                and p[1].type[0] in ["bool", "char", "short", "int"]
                and str(p[2]) == "+"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Pointer Arithmetic Not allowed at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[3].type) > 0
                and p[3].type[0][-1] == "*"
                and len(p[1].type) > 0
                and p[1].type[0] in temp_list_ii
                and str(p[2]) == "-"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Invalid binary - operation between incompatible types {p[1].type} and {p[3].type} on line {p.lineno(2)}"
                    + bcolors.ENDC
                )

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to add two incompatible type of expressions ( "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " ) "
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return

            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]
                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)

            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_shift_expression(self, p):
        """
        shift_expression : additive_expression
                        | shift_expression LEFT_OP additive_expression
                        | shift_expression RIGHT_OP additive_expression
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to perform a bitshift operation between the expressions on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in ["char", "short", "int"]
                and p[3].type[0]
                in [
                    "char",
                    "short",
                    "int",
                ]
            ):
                p0type = []
                p0label = str(p[2])
                p0typestr = "to"

                p0type = ["int"]
                p0label += "_int"
                p0typestr += "_int"

                if "unsigned" in p[1].type:
                    p0type.append("unsigned")
                    p0label += "_unsigned"
                    p0typestr += "_unsigned"

                flag = True

                for i in p0type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p0type
                    p1 = Node(p0typestr, [p[1]])
                else:
                    p1 = p[1]

                isin = True
                for single_type in p0type:
                    if single_type not in p[3].type:
                        isin = False
                if isin == False:
                    p[3].totype = p0type
                    p3 = Node(p0typestr, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p[3]])
                p[0].type = p0type
                p[0].label = p0label
                p[0].label = p[0].label.replace(" ", "_")

                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Bitshift operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return
            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]
                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_relational_expression(self, p):
        """
        relational_expression : shift_expression
                            | relational_expression '<' shift_expression
                            | relational_expression '>' shift_expression
                            | relational_expression LE_OP shift_expression
                            | relational_expression GE_OP shift_expression
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:

            temp_list = ["bool", "char", "short", "int", "float"]
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to perform relational operation between the expressions on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in temp_list
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list
            ):
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p0type = ["int"]
                val = max(temp_list.index(p[1].type[0]), temp_list.index(p[3].type[0]))
                p0label = (
                    str(p[2])
                    + "_"
                    + ["bool", "char", "short", "int", "float"][
                        max(
                            temp_list.index(p[1].type[0]), temp_list.index(p[3].type[0])
                        )
                    ]
                )

                flag = 0
                if "unsigned" in p[1].type or "unsigned" in p[3].type and val <= 2:
                    flag = 1
                    p0label = p0label + "_" + "unsigned"

                p0label = p0label.replace(" ", "_")
                p[1].totype = None
                p[3].totype = None

                if temp_list[val] not in p[1].type:
                    p[1].totype = [temp_list[val]]
                    if flag:
                        p[1].totype.append("unsigned")
                elif flag and "unsigned" not in p[1].type:
                    p[1].totype = [temp_list[val], "unsigned"]

                if p[1].totype != None and p[1].totype != p[1].type:
                    p1str = "to"
                    for single_type in p[1].totype:
                        p1str = p1str + "_" + single_type
                    p1 = Node(p1str, [p[1]])
                else:
                    p1 = p[1]

                if temp_list[val] not in p[3].type:
                    p[3].totype = [temp_list[val]]
                    if flag:
                        p[3].totype.append("unsigned")
                elif flag and "unsigned" not in p[3].type:
                    p[3].totype = [temp_list[val], "unsigned"]

                if p[3].totype != None and p[3].totype != p[3].type:
                    p3str = "to"
                    for single_type in p[3].totype:
                        p3str = p3str + "_" + single_type
                    p3 = Node(p3str, [p[3]])
                else:
                    p3 = p[3]
                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p0label
                p[0].node.attr["label"] = p[0].label

            elif (
                len(p[1].type) > 0
                and p[1].type[0] == "str"
                and len(p[3].type) > 0
                and p[3].type[0] == "str"
            ):
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label = p[0].label + "_str"
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label

            elif (
                len(p[1].type) > 0
                and p[1].type[0][-1] == "*"
                and len(p[3].type) > 0
                and p[3].type[0] in ["float"]
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[3].type) > 0
                and p[3].type[0][-1] == "*"
                and len(p[1].type) > 0
                and p[1].type[0] in ["float"]
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                (
                    (len(p[3].type) > 0 and p[3].type[0][-1] == "*")
                    or (len(p[1].type) > 0 and p[1].type[0][-1] == "*")
                )
                and "struct" not in p[1].type
                and "struct" not in p[3].type
            ):
                p[1].totype = ["int", "unsigned"]
                p1 = Node("to_int_unsigned", [p[1]])
                p[3].totype = ["int", "unsigned"]
                p3 = Node("to_int_unsigned", [p[3]])
                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = ["int"]
                p[0].label = p[0].label + "_*"
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Relational operation failed between incompatible types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            if self.symtab.error == True:
                return
            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]
                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_equality_expression(self, p):
        """
        equality_expression : relational_expression
                            | equality_expression EQ_OP relational_expression
                            | equality_expression NE_OP relational_expression
        """

        if True == self.error:
            return

        if len(p) == 4:

            temp_list_a = ["bool", "char", "short", "int", "float"]

            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Can't perform check of equality operation between the expressions at Line No.: "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in temp_list_a
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list_a
            ):
                p0type = ["int"]
                p0label = (
                    str(p[2])
                    + "_"
                    + temp_list_a[
                        max(
                            temp_list_a.index(p[1].type[0]),
                            temp_list_a.index(p[3].type[0]),
                        )
                    ]
                )

                flag = 0
                if (
                    "unsigned" in p[1].type
                    or "unsigned" in p[3].type
                    and max(
                        temp_list_a.index(p[1].type[0]), temp_list_a.index(p[3].type[0])
                    )
                    > 0
                    and max(
                        temp_list_a.index(p[1].type[0]), temp_list_a.index(p[3].type[0])
                    )
                    < 5
                ):
                    flag = 1
                    p0label = p0label + "_" + "unsigned"

                p0label = p0label.replace(" ", "_")
                p[1].totype = None
                p[3].totype = None

                if (
                    temp_list_a[
                        max(
                            temp_list_a.index(p[1].type[0]),
                            temp_list_a.index(p[3].type[0]),
                        )
                    ]
                    not in p[1].type
                ):
                    p[1].totype = [
                        temp_list_a[
                            max(
                                temp_list_a.index(p[1].type[0]),
                                temp_list_a.index(p[3].type[0]),
                            )
                        ]
                    ]
                    if flag:
                        p[1].totype.append("unsigned")
                elif flag and "unsigned" not in p[1].type:
                    p[1].totype = [
                        temp_list_a[
                            max(
                                temp_list_a.index(p[1].type[0]),
                                temp_list_a.index(p[3].type[0]),
                            )
                        ],
                        "unsigned",
                    ]

                if p[1].totype != None and p[1].totype != p[1].type:
                    p1str = "to"
                    for single_type in p[1].totype:
                        p1str = p1str + "_" + single_type
                    p1 = Node(p1str, [p[1]])
                else:
                    p1 = p[1]

                if (
                    temp_list_a[
                        max(
                            temp_list_a.index(p[1].type[0]),
                            temp_list_a.index(p[3].type[0]),
                        )
                    ]
                    not in p[3].type
                ):
                    p[3].totype = [
                        temp_list_a[
                            max(
                                temp_list_a.index(p[1].type[0]),
                                temp_list_a.index(p[3].type[0]),
                            )
                        ]
                    ]
                    if flag:
                        p[3].totype.append("unsigned")
                elif flag and "unsigned" not in p[3].type:
                    p[3].totype = [
                        temp_list_a[
                            max(
                                temp_list_a.index(p[1].type[0]),
                                temp_list_a.index(p[3].type[0]),
                            )
                        ],
                        "unsigned",
                    ]

                if p[3].totype != None and p[3].totype != p[3].type:
                    p3str = "to"
                    for single_type in p[3].totype:
                        p3str += "_" + single_type
                    p3 = Node(p3str, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p0label
                p[0].node.attr["label"] = p[0].label
            elif (
                len(p[1].type) > 0
                and p[1].type[0] == "str"
                and len(p[3].type) > 0
                and p[3].type[0] == "str"
            ):
                p[0] = Node(str(p[2]), [p[1], p[3]])
                p[0].type = ["int"]
                p[0].label += "_str"
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label
            elif (
                len(p[1].type) > 0
                and p[1].type[0][-1] == "*"
                and len(p[3].type) > 0
                and p[3].type[0] == "float"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Relational operation between incompatible types"
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + "on line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
            elif (
                len(p[3].type) > 0
                and p[3].type[0][-1] == "*"
                and len(p[1].type) > 0
                and p[1].type[0] == "float"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Relational operation between incompatible types"
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + "on line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
            elif (
                (
                    (len(p[1].type) > 0 and p[1].type[0][-1] == "*")
                    or (len(p[3].type) > 0 and p[3].type[0][-1] == "*")
                )
                and "struct" not in p[1].type
                and "struct" not in p[3].type
            ):
                p[1].totype = ["int", "unsigned"]
                p1 = Node("to_int_unsigned", [p[1]])
                p[3].totype = ["int", "unsigned"]
                p3 = Node("to_int_unsigned", [p[3]])

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = ["int"]
                p[0].label += "_*"
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label
            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Equality check operation between incompatible types"
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + "on line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )
            if self.symtab.error == True:
                return
            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]

                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp
            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

        elif len(p) == 2:
            p[0] = p[1]

    def p_and_expression(self, p):
        """
        and_expression : equality_expression
                    | and_expression '&' equality_expression
        """
        temp_list = ["bool", "char", "short", "int"]
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to perform bitwise AND operation between the expressions on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in temp_list
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list
            ):
                p0type = ["int"]
                p0label = str(p[2])

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p[0].type.append("unsigned")
                    p[0].label += "unsigned"
                p[0].node.attr["label"] = p[0].label

                flag = True
                for i in p0type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p0type
                    strp1 = "to_"
                    for single_type in p[1].totype:
                        strp1 += single_type
                    p1 = Node(strp1, [p[1]])
                else:
                    p1 = p[1]

                flag = True
                for i in p0type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p0type
                    strp3 = "to_"
                    for single_type in p[3].totype:
                        strp3 += single_type
                    p3 = Node(strp3, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p0label
                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Unable to perform bitwise AND operation between incompatible expression types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on Line No.: "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return
            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]

                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp
            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_exclusive_or_expression(self, p):
        """
        exclusive_or_expression : and_expression
                                | exclusive_or_expression '^' and_expression
        """
        temp_list_ii = ["bool", "char", "short", "int"]
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]
        if len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform bitwise xor on line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in temp_list_ii
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list_ii
            ):
                p0type = ["int"]
                p0label = str(p[2])

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p0type.append("unsigned")
                    p[0].label += "_unsigned"

                p0label = p0label.replace(" ", "_")

                isIn = 1
                for single_type in p0type:
                    if single_type not in p[1].type:
                        isIn = 0
                if isIn == 0:
                    p[1].totype = p0type
                    strp1 = "to_"
                    for single_type in p[1].totype:
                        strp1 += single_type
                    p1 = Node(strp1, [p[1]])
                else:
                    p1 = p[1]

                isIn = 1
                for single_type in p0type:
                    if single_type not in p[3].type:
                        isIn = 0
                if isIn == 0:
                    p[3].totype = p0type
                    strp3 = "to_"
                    for single_type in p[3].totype:
                        strp3 += single_type
                    p3 = Node(strp3, [p[3]])
                else:
                    p3 = p[3]
                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p0label
                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Bitwise xor operation between types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on line "
                    + str(p.lineno(2))
                    + " is incompatible."
                    + bcolors.ENDC
                )
            if self.symtab.error == True:
                return

            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]

                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_inclusive_or_expression(self, p):
        """
        inclusive_or_expression : exclusive_or_expression
                                | inclusive_or_expression '|' exclusive_or_expression
        """
        temp_list = ["bool", "char", "short", "int"]
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if (
                p[1] is None
                or p[3] is None
                or p[1].type is None
                or p[3].type is None
                or p[1].type == []
                or p[3].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform bitwise or between expressions on line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )

            elif (
                len(p[1].type) > 0
                and p[1].type[0] in temp_list
                and len(p[3].type) > 0
                and p[3].type[0] in temp_list
            ):
                p0type = ["int"]
                p0label = str(p[2])

                if "unsigned" in p[1].type or "unsigned" in p[3].type:
                    p[0].type.append("unsigned")
                    p[0].label += "_unsigned"
                p[0].node.attr["label"] = p[0].label

                flag = True
                for i in p0type:
                    if i not in p[1].type:
                        flag = False
                if flag == False:
                    p[1].totype = p0type
                    strp1 = "to_"
                    for single_type in p[1].totype:
                        strp1 += single_type
                    p1 = Node(strp1, [p[1]])
                else:
                    p1 = p[1]
                flag = True

                for i in p0type:
                    if i not in p[3].type:
                        flag = False
                if flag == False:
                    p[3].totype = p0type
                    strp3 = "to_"
                    for single_type in p[3].totype:
                        strp3 += single_type
                    p3 = Node(strp3, [p[3]])
                else:
                    p3 = p[3]

                p[0] = Node(str(p[2]), [p1, p3])
                p[0].type = p0type
                p[0].label = p0label
                p[0].node.attr["label"] = p[0].label

            else:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Bitwise or operation between types "
                    + str(p[1].type)
                    + " and "
                    + str(p[3].type)
                    + " on line "
                    + str(p.lineno(2))
                    + " is incompatible."
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return

            if p[1].totype is not None and p[1].totype != p[1].type:
                p1.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p1.temp, 0)
                self.symtab.modify_symbol(p1.temp, "data_type", p[1].totype)
                self.symtab.modify_symbol(p1.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[1].totype, p1.temp)
                if self.symtab.is_global(p1.temp):
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p1.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p1.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p1.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p1.temp = found["temp"]
                currtype = []
                for single_type in p[1].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p1.temp,
                    p[1].temp,
                    " ".join(p[1].totype).replace(" ", "_") + cstr,
                )
            else:
                p1.temp = p[1].temp
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]

                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp

            p[0].temp = self.three_address_code.create_temp_var()
            self.symtab.insert_symbol(p[0].temp, 0)
            self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
            self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
            self.symtab_size_update(p[0].type, p[0].temp)
            if self.symtab.is_global(p[0].temp):
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
            else:
                self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                var_size = found["allocated_size"]
                if found["variable_scope"] == "Local":

                    if found["offset"] > 0:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                        )
                    else:
                        self.symtab.modify_symbol(
                            p[0].temp,
                            "temp",
                            f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                        )
                p[0].temp = found["temp"]
            self.three_address_code.emit(p[0].label, p[0].temp, p1.temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def p_logical_and_expression(self, p):
        """logical_and_expression : inclusive_or_expression
        | logical_and_expression AND_OP marker_global inclusive_or_expression marker_global
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 6:
            if (
                p[1] is None
                or p[4] is None
                or p[1].type is None
                or p[4].type is None
                or p[1].type == []
                or p[4].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform logical and between expressions on line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif "struct" in p[1].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Need scalars to perform logical operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            else:
                p[0] = Node(str(p[2]), [p[1], p[4]])
                p[0].type = ["int"]
                if self.symtab.error == True:
                    return
                self.three_address_code.backpatch(p[1].true_list, p[3].quadruples)
                self.three_address_code.backpatch(p[1].false_list, p[5].quadruples)
                p[0].false_list = p[1].false_list + p[4].false_list
                p[0].true_list = p[4].true_list
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]
                self.three_address_code.emit("=_int", p[0].temp, "$0", "")
                self.three_address_code.emit(
                    "ifnz goto",
                    self.three_address_code.next_statement + 3,
                    p[1].temp,
                    "",
                )
                self.three_address_code.emit(
                    "goto", self.three_address_code.next_statement + 5, "", ""
                )
                self.three_address_code.emit(
                    "ifnz goto",
                    self.three_address_code.next_statement + 3,
                    p[4].temp,
                    "",
                )
                self.three_address_code.emit(
                    "goto", self.three_address_code.next_statement + 3, "", ""
                )
                self.three_address_code.emit("=_int", p[0].temp, "$1", "")

    def p_logical_or_expression(self, p):
        """logical_or_expression : logical_and_expression
        | logical_or_expression OR_OP marker_global logical_and_expression marker_global
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 6:
            if (
                p[1] is None
                or p[4] is None
                or p[1].type is None
                or p[4].type is None
                or p[1].type == []
                or p[4].type == []
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform logical or between expressions on line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            elif "struct" in p[1].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Need scalars to perform logical operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
            else:
                p[0] = Node(str(p[2]), [p[1], p[4]])
                p[0].type = ["int"]
                if self.symtab.error == True:
                    return
                self.three_address_code.backpatch(p[1].false_list, p[3].quadruples)
                self.three_address_code.backpatch(p[1].true_list, p[5].quadruples)
                p[0].true_list = p[1].true_list + p[4].true_list
                p[0].false_list = p[4].false_list
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                self.three_address_code.emit("=_int", p[0].temp, "$1", "")
                self.three_address_code.emit(
                    "ifnz goto",
                    self.three_address_code.next_statement + 4,
                    p[1].temp,
                    "",
                )
                self.three_address_code.emit(
                    "ifnz goto",
                    self.three_address_code.next_statement + 3,
                    p[4].temp,
                    "",
                )
                self.three_address_code.emit("=_int", p[0].temp, "$0", "")

    def p_conditional_expression(self, p):
        """conditional_expression : logical_or_expression
        | logical_or_expression '?' marker_global expression ':' marker_global conditional_expression marker_global
        """
        temp_list_aa = ["bool", "char", "short", "int", "float"]
        temp_list_ii = ["bool", "char", "short", "int"]
        temp_list_di = ["char", "short", "int"]
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 9:
            if p[1] is None or p[1].type is None or p[1].type == []:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform conditional operation at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            if "struct" in p[1].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Struct type variable not allowed as first operand of ternary operator"
                    + bcolors.ENDC
                )
                return
            elif p[4] is None or p[7] is None:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform conditional operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif p[4].type in [None, []] or p[7].type in [None, []]:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot perform conditional operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif "struct" in p[4].type and "struct" not in p[7].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Type mismatch between "
                    + str(p[4].type)
                    + " and "
                    + str(p[7].type)
                    + " for conditional operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif "struct" in p[7].type and "struct" not in p[4].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Type mismatch between "
                    + str(p[4].type)
                    + " and "
                    + str(p[7].type)
                    + " for conditional operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif (
                "struct" in p[4].type
                and "struct" in p[7].type
                and p[4].type[1] != p[7].type[1]
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible struct types to perform conditional operation at line"
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif (
                p[4].type[0] not in temp_list_aa
                and p[4].type[0][-1] != "*"
                and p[7].type[0] in temp_list_aa
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Type mismatch while performing conditional operation at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return

            elif (
                p[4].type[0][-1] == "*"
                and p[7].type[0][-1] != "*"
                and p[7].type[0] not in temp_list_ii
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible conditional operation between pointer and "
                    + str(p[7].type)
                    + " at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            elif (
                p[7].type[0][-1] == "*"
                and p[4].type[0][-1] != "*"
                and p[4].type[0] not in temp_list_ii
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible conditional operation between pointer and "
                    + str(p[7].type)
                    + " at line "
                    + str(p.lineno(2))
                    + bcolors.ENDC
                )
                return
            error_flag = False
            if p[4].type == p[7].type:
                p0type = p[4].type

            elif (
                len(p[4].type) > 0
                and p[4].type[0][-1] == "*"
                and len(p[7].type) > 0
                and p[7].type[0][-1] == "*"
            ):
                p0type = ["void *"]

            elif (
                len(p[4].type) > 0
                and p[4].type[0][-1] == "*"
                or len(p[7].type) > 0
                and p[7].type[0][-1] == "*"
            ):
                if p[4].type[0][-1] == "*":
                    p0type = p[4].type
                elif p[7].type[0][-1] == "*":
                    p0type = p[7].type

            elif "str" in p[4].type:
                p0type = p[7].type
            elif "str" in p[7].type:
                p0type = p[4].type

            elif (
                len(p[4].type) > 0
                and p[4].type[0] in temp_list_aa
                and len(p[7].type) > 0
                and p[7].type[0] in temp_list_aa
            ):
                p0type = []
                p0type.append(
                    temp_list_aa[
                        max(
                            temp_list_aa.index(p[4].type[0]),
                            temp_list_aa.index(p[7].type[0]),
                        )
                    ]
                )
                if (
                    "unsigned" in p[4].type
                    or "unsigned" in p[7].type
                    and p0type[0] in temp_list_di
                ):
                    p0type.append("unsigned")
            else:
                error_flag = True
            if not error_flag:
                if p0type != p[4].type:
                    p4str = "to"
                    for single_type in p0type:
                        p4str += "_" + single_type
                    p4str = p4str.replace(" ", "_")
                    p4 = Node(p4str, [p[4]])
                else:
                    p4 = p[4]
                if p0type != p[7].type:
                    p7str = "to"
                    for single_type in p0type:
                        p7str += "_" + single_type
                    p7str = p7str.replace(" ", "_")
                    p7 = Node(p7str, [p[7]])
                else:
                    p7 = p[7]
                p[0] = Node("TERNARY", [p[1], p4, p7])
                p[0].type = p0type
                if self.symtab.error == True:
                    return
                p[4].totype = p0type
                p4type = []
                for single_type in p[4].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        p4type.append(single_type)
                if p[4].totype is not None and p[4].totype != p4type:
                    p4.temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(p4.temp, 0)
                    self.symtab.modify_symbol(p4.temp, "data_type", p[4].totype)
                    self.symtab.modify_symbol(p4.temp, "identifier_type", "TEMP")
                    self.symtab_size_update(p[4].totype, p4.temp)
                    if self.symtab.is_global(p4.temp):
                        self.symtab.modify_symbol(p4.temp, "variable_scope", "Global")
                    else:
                        self.symtab.modify_symbol(p4.temp, "variable_scope", "Local")
                        found, entry = self.symtab.return_sym_tab_entry(p4.temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":

                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    p4.temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    p4.temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        p4.temp = found["temp"]
                    currtype = []
                    for single_type in p[4].type:
                        if (
                            single_type != "arr"
                            and single_type[0] != "["
                            and single_type[-1] != "]"
                        ):
                            currtype.append(single_type)
                    cstr = "," + " ".join(currtype).replace(" ", "_")
                    self.three_address_code.emit(
                        "cast",
                        p4.temp,
                        p[4].temp,
                        " ".join(p[4].totype).replace(" ", "_") + cstr,
                    )
                else:
                    p4.temp = p[4].temp
                p[7].totype = p0type
                p7type = []
                for single_type in p[7].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        p7type.append(single_type)
                if p[7].totype is not None and p[7].totype != p7type:
                    p7.temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(p7.temp, 0)
                    self.symtab.modify_symbol(p7.temp, "data_type", p[7].totype)
                    self.symtab.modify_symbol(p7.temp, "identifier_type", "TEMP")
                    self.symtab_size_update(p[7].totype, p7.temp)
                    if self.symtab.is_global(p7.temp):
                        self.symtab.modify_symbol(p7.temp, "variable_scope", "Global")
                    else:
                        self.symtab.modify_symbol(p7.temp, "variable_scope", "Local")
                        found, entry = self.symtab.return_sym_tab_entry(p7.temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":

                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    p7.temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    p7.temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        p7.temp = found["temp"]
                    currtype = []
                    for single_type in p[7].type:
                        if (
                            single_type != "arr"
                            and single_type[0] != "["
                            and single_type[-1] != "]"
                        ):
                            currtype.append(single_type)
                    cstr = "," + " ".join(currtype).replace(" ", "_")
                    self.three_address_code.emit(
                        "cast",
                        p7.temp,
                        p[7].temp,
                        " ".join(p[7].totype).replace(" ", "_") + cstr,
                    )
                else:
                    p7.temp = p[7].temp
                p[0].temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p[0].temp, 0)
                self.symtab.modify_symbol(p[0].temp, "data_type", p[0].type)
                self.symtab.modify_symbol(p[0].temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[0].type, p[0].temp)
                if self.symtab.is_global(p[0].temp):
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p[0].temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p[0].temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p[0].temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p[0].temp = found["temp"]

                self.three_address_code.emit(
                    "ifnz goto",
                    self.three_address_code.next_statement + 3,
                    p[1].temp,
                    "",
                )
                self.three_address_code.emit(
                    "goto", self.three_address_code.next_statement + 4, "", ""
                )
                self.three_address_code.emit(f"=_{p[0].type[0]}", p[0].temp, p4.temp)
                self.three_address_code.emit(
                    "goto", self.three_address_code.next_statement + 3, "", ""
                )
                self.three_address_code.emit(f"=_{p[0].type[0]}", p[0].temp, p7.temp)
                self.three_address_code.backpatch(p[1].true_list, p[3].quadruples)
                self.three_address_code.backpatch(p[1].false_list, p[6].quadruples)
                self.three_address_code.backpatch(p[4].true_list, p[8].quadruples)
                self.three_address_code.backpatch(p[4].false_list, p[8].quadruples)
                p[0].true_list = p[4].true_list + p[7].true_list
                p[0].false_list = p[4].false_list + p[7].false_list
                return
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Cannot perform conditional operation at line"
                + str(p.lineno(2))
                + bcolors.ENDC
            )

    def p_assignment_expression(self, p):
        """
        assignment_expression : conditional_expression
                            | unary_expression assignment_operator assignment_expression
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            p[0] = p[2]
            if (p[1] is not None) and (p[1].node is not None):
                if (p[3] is not None) and (p[3].node is not None):
                    if p[1].type in [None, []] or p[3].type in [None, []]:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot perform assignment at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif p[1].type[0][-1] == "*" and "arr" in p[1].type:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot perform assignment to type array at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif p[1].is_var == 0 and "struct" not in p[1].type[0]:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Left hand side must be a variable at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif "struct" in p[1].type and "struct" not in p[3].type:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot assign non-struct value "
                            + str(p[3].type)
                            + " to struct type "
                            + str(p[1].type)
                            + " at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif (
                        "struct" in p[1].type
                        and "struct" in p[3].type
                        and p[1].type[1] != p[3].type[1]
                    ):
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Incompatible struct types to perform assignment at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif p[1].type in [None, []] or p[3].type in [None, []]:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Type mismatch while assigning value at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif (
                        p[1].type[0] not in ["bool", "char", "short", "int", "float"]
                        and p[1].type[0][-1] != "*"
                        and p[3].type[0] in ["bool", "char", "short", "int", "float"]
                    ):
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Type mismatch while assigning value at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    elif (
                        p[1].type[0][-1] == "*"
                        and p[3].type[0][-1] != "*"
                        and p[3].type[0] not in ["bool", "char", "short", "int"]
                    ):
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Assignment between pointer and "
                            + str(p[3].type)
                            + " at line "
                            + str(p[2].lineno)
                            + " is incompatible."
                            + bcolors.ENDC
                        )

                    elif (
                        p[1].type[0][-1] == "*"
                        and p[3].type[0] in ["bool", "char", "short", "int"]
                        and p[2].label[0] not in ["+", "-", "="]
                    ):
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Incompatible operands to binary operator "
                            + str(p[2].label)
                            + " at line "
                            + str(p[2].lineno)
                            + bcolors.ENDC
                        )

                    else:
                        p[0].type = p[1].type
                        isin = True
                        for single_type in p[0].type:
                            if single_type != "arr" and (
                                single_type[0] != "[" and single_type[-1] != "]"
                            ):
                                if single_type not in p[3].type:
                                    isin = False
                        if isin == False:
                            p[3].totype = []
                            for single_type in p[0].type:
                                if single_type != "arr" and (
                                    single_type[0] != "[" and single_type[-1] != "]"
                                ):
                                    p[3].totype.append(single_type)
                            p3str = "to"
                            for single_type in p[0].type:
                                p3str += "_" + single_type
                            p3str = p3str.replace(" ", "_")
                            if "*" == p[0].type[0][-1]:
                                p3str = "to_int_unsigned"
                            p3 = Node(p3str, [p[3]])
                        else:
                            p3 = p[3]

                        p[0].insert_edge([p[1], p3])

                        if "struct" in p[0].type:
                            p[0].label += "_struct"
                        elif p[0].type[0][-1] == "*":
                            p[0].label += "_int_unsigned"
                        else:
                            p[0].label += "_" + p[0].type[0]
                            if "unsigned" in p[0].type:
                                p[0].label += "_unsigned"
                        p[0].label = p[0].label.replace(" ", "_")
                        p[0].node.attr["label"] = p[0].label
                else:
                    p[0].insert_edge([p[1]])
            else:
                if (p[3] is not None) and (p[3].node is not None):
                    p[0].insert_edge([p[3]])
            if self.symtab.error == True:
                return
            if p[3].totype is not None and p[3].totype != p[3].type:
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]

                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp
            p[0].var_name = p[1].var_name
            p[0].temp = p[1].temp
            self.equate(p[1].type, p[0].label, p[1].temp, p3.temp)
            p[0].true_list.append(self.three_address_code.next_statement)
            p[0].false_list.append(self.three_address_code.next_statement + 1)
            self.three_address_code.emit("ifnz goto", "", p[0].temp, "")
            self.three_address_code.emit("goto", "", "", "")

    def equate(self, p1type, p0label, p1temp, p3temp):
        if p0label == "=_struct":
            data_struc = self.symtab.return_type_tab_entry_su(p1type[1], p1type[0])
            currOffset = 0
            left_offset = 0
            right_offset = 0
            left_new_temp = ""
            right_new_temp = ""

            for var in data_struc["vars"].keys():

                if p1temp[0] == "(":
                    left_new_temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(left_new_temp, 0)
                    self.symtab.modify_symbol(
                        left_new_temp, "data_type", ["int", "unsigned"]
                    )
                    self.symtab.modify_symbol(left_new_temp, "identifier_type", "TEMP")
                    self.symtab_size_update(["int", "unsigned"], left_new_temp)
                    if self.symtab.is_global(left_new_temp):
                        self.symtab.modify_symbol(
                            left_new_temp, "variable_scope", "Global"
                        )
                    else:
                        self.symtab.modify_symbol(
                            left_new_temp, "variable_scope", "Local"
                        )
                        found, entry = self.symtab.return_sym_tab_entry(left_new_temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":
                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    left_new_temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    left_new_temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        left_new_temp = found["temp"]
                    self.three_address_code.emit(
                        "+_int", left_new_temp, p1temp[1:-1], f"${currOffset}"
                    )
                    left_new_temp = f"({left_new_temp})"
                else:
                    left_offset = int(p1temp.split("(")[0])
                    left_new_temp = f"{left_offset+currOffset}(%ebp)"

                if p3temp[0] == "(":
                    right_new_temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(right_new_temp, 0)
                    self.symtab.modify_symbol(
                        right_new_temp, "data_type", ["int", "unsigned"]
                    )
                    self.symtab.modify_symbol(right_new_temp, "identifier_type", "TEMP")
                    self.symtab_size_update(["int", "unsigned"], right_new_temp)
                    if self.symtab.is_global(right_new_temp):
                        self.symtab.modify_symbol(
                            right_new_temp, "variable_scope", "Global"
                        )
                    else:
                        self.symtab.modify_symbol(
                            right_new_temp, "variable_scope", "Local"
                        )
                        found, entry = self.symtab.return_sym_tab_entry(right_new_temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":

                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    right_new_temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    right_new_temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        right_new_temp = found["temp"]
                    self.three_address_code.emit(
                        "+_int", right_new_temp, p3temp[1:-1], f"${currOffset}"
                    )
                    right_new_temp = f"({right_new_temp})"
                else:
                    right_offset = int(p3temp.split("(")[0])
                    right_new_temp = f"{right_offset+currOffset}(%ebp)"

                if "*" in data_struc["vars"][var]["data_type"]:
                    self.three_address_code.emit(
                        "=_unsigned_int", left_new_temp, right_new_temp
                    )
                    if p0label == "=_struct":
                        currOffset += 4
                elif "struct" in data_struc["vars"][var]["data_type"]:
                    new_type = copy.deepcopy(data_struc["vars"][var]["data_type"])
                    new_type.reverse()
                    self.equate(new_type, "=_struct", left_new_temp, right_new_temp)
                    if p0label == "=_struct":
                        currOffset += data_struc["vars"][var]["allocated_size"]
                elif "int" in data_struc["vars"][var]["data_type"]:
                    self.three_address_code.emit("=_int", left_new_temp, right_new_temp)
                    if p0label == "=_struct":
                        currOffset += 4
                elif "char" in data_struc["vars"][var]["data_type"]:
                    self.three_address_code.emit(
                        "=_char", left_new_temp, right_new_temp
                    )
                    if p0label == "=_struct":
                        currOffset += 1
                elif "float" in data_struc["vars"][var]["data_type"]:
                    self.three_address_code.emit(
                        "=_float", left_new_temp, right_new_temp
                    )
                    if p0label == "=_struct":
                        currOffset += 4
                elif "bool" in data_struc["vars"][var]["data_type"]:
                    self.three_address_code.emit(
                        "=_bool", left_new_temp, right_new_temp
                    )
                    if p0label == "=_struct":
                        currOffset += 4
        else:
            self.three_address_code.emit(p0label, p1temp, p3temp, "")

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
        if self.error == True:
            return

        p[0] = Node(str(p[1]))
        p[0].lineno = p.lineno(1)

    def p_expression(self, p):
        """
        expression : assignment_expression
                | expression ',' assignment_expression
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node(",", [p[1], p[3]])
            if self.symtab.error == True:
                return
            p[0].temp = p[3].temp
            p[0].true_list = p[3].true_list
            p[0].false_list = p[3].false_list

    def p_constant_expression(self, p):
        """
        constant_expression	: conditional_expression
        """
        if self.error == True:
            return
        p[0] = p[1]

    # Initializers

    def p_initializer(self, p):
        """
        initializer : assignment_expression
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node("{}", [p[2]])
            p[0].type = ["init_list"]

    # Declarators

    def p_declaration(self, p):
        """declaration	: declaration_specifiers ';'
        | declaration_specifiers init_declarator_list ';'
        """
        if self.error == True:
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
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[1]
            if (p[2] is not None) and (p[2].node is not None):
                p[0].insert_edge([p[2]])
                if p[2].type and p[0].type:
                    p[0].type += p[2].type

            p[0].extraVals = p[2].extraVals + p[0].extraVals

        elif 0 < len(p[0].type) and "struct" in p[0].type and len(p[0].type) > 2:
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Cannot have type specifiers for struct type at line "
                + str(p[1].line)
                + bcolors.ENDC
            )

    def p_init_declarator_list(self, p):
        """init_declarator_list : init_declarator
        | init_declarator_list ',' marker_init init_declarator
        """
        if self.error == True:
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
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        p[0].extraVals = p[-2].extraVals

    def p_init_declarator(self, p):
        """init_declarator : declarator
        | declarator '=' initializer
        """
        temp_list_aa = ["bool", "char", "short", "int", "float"]
        temp_list_ii = ["bool", "char", "short", "int"]
        if self.error == True:
            return
        if len(p) == 2:
            p[1].remove_graph()
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = Node("=")
            p[0].variables = p[1].variables

        p[0].extraVals = p[-1].extraVals
        for val in p[0].extraVals:
            p[0].append_dict(val)

        for var_name in p[0].variables:
            if p[0].variables[var_name] and p[0].variables[var_name][-1] in [
                "struct",
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
                        var_name,
                        "identifier_type",
                        found["identifier_type"],
                        p.lineno(1),
                    )
                    self.symtab.modify_symbol(
                        var_name, "data_type", p[0].variables[var_name], p.lineno(1)
                    )
            else:
                self.symtab.modify_symbol(
                    var_name, "data_type", p[0].variables[var_name], p.lineno(1)
                )

            if p[0].variables[var_name]:
                is_global = self.symtab.is_global(var_name)
                if is_global:
                    self.symtab.modify_symbol(
                        var_name, "variable_scope", "Global", p.lineno(1)
                    )
                else:
                    self.symtab.modify_symbol(
                        var_name, "variable_scope", "Local", p.lineno(1)
                    )

            if p[0].variables[var_name]:
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
                        multiplier * datatype_size["ptr"],
                        p.lineno(1),
                    )

                elif "struct" in p[0].variables[var_name]:
                    if not self.symtab.is_global():
                        struct_size = 0
                        found = self.symtab.return_type_tab_entry_su(
                            p[0].variables[var_name][-2],
                            p[0].variables[var_name][-1],
                            p.lineno(1),
                        )
                        if found:
                            struct_size = found["allocated_size"]
                        self.symtab.modify_symbol(
                            var_name,
                            "allocated_size",
                            multiplier * struct_size,
                            p.lineno(1),
                        )
                    else:
                        print("Struct objects not allowed to be declared globally...")
                        self.symtab.error = True
                        return
                elif "float" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["float"],
                        p.lineno(1),
                    )
                elif "short" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["short"],
                        p.lineno(1),
                    )
                elif "int" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["int"],
                        p.lineno(1),
                    )
                elif "char" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["char"],
                        p.lineno(1),
                    )
                elif "bool" in p[0].variables[var_name]:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["bool"],
                        p.lineno(1),
                    )
                else:
                    self.symtab.modify_symbol(
                        var_name,
                        "allocated_size",
                        multiplier * datatype_size["void"],
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
                        print(
                            bcolors.FAIL
                            + "Cannot have empty indices for array declarations at line"
                            + str(entry["line"])
                            + bcolors.ENDC
                        )
                    elif int(single_type[1:-1]) <= 0:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot have non-positive integers for array declarations at line"
                            + str(entry["line"])
                            + bcolors.ENDC
                        )

            if len(temp2_type_list) != len(set(temp2_type_list)):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "variables cannot have duplicating type of declarations at line"
                    + str(entry["line"])
                    + bcolors.ENDC
                )

            if "unsigned" in entry["data_type"] and "signed" in entry["data_type"]:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "variable cannot be both signed and unsigned at line"
                    + str(entry["line"])
                    + bcolors.ENDC
                )
            elif "void" in entry["data_type"] and "*" not in entry["data_type"]:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot have a void type variable at line "
                    + str(entry["line"])
                    + bcolors.ENDC
                )
                return
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
                if data_type_count > 1:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Two or more conflicting data types specified for variable at line"
                        + str(entry["line"])
                        + bcolors.ENDC
                    )

            if len(p) == 4:
                isArr = 0
                for i in range(len(entry["data_type"])):
                    if (
                        entry["data_type"][i][0] == "["
                        and entry["data_type"][i][-1] == "]"
                    ):
                        isArr += 1

                type_list = entry["data_type"]
                if entry["identifier_type"] == "variable":
                    p[1].is_var = 1

                if set(type_list) == {"*"}:
                    type_list = []

                if "unsigned" in type_list or "signed" in type_list:
                    if (
                        "bool" not in type_list
                        and "char" not in type_list
                        and "short" not in type_list
                    ):
                        type_list.append("int")

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

                if "struct" in type_list:
                    p[1].type.append("struct")
                    for single_type in type_list:
                        if single_type != "struct":
                            p[1].type.append(single_type)

                if isArr > 0:
                    temp_type = []
                    temp_type.append(p[1].type[0])
                    for i in range(isArr):
                        temp_type[0] += " *"
                    for i in range(len(p[1].type)):
                        if i > isArr:
                            temp_type.append(p[1].type[i])
                    p[1].type = temp_type
                    p[1].type.append("arr")
                    for i in range(len(type_list)):
                        if (
                            type_list[len(type_list) - i - 1][0] == "["
                            and type_list[len(type_list) - i - 1][-1] == "]"
                        ):
                            p[1].type.append(type_list[len(type_list) - i - 1])

                if "void" in type_list:
                    p[1].type.append("void")
                    for single_type in type_list:
                        if single_type != "void":
                            p[1].type.append(single_type)

                if "*" in type_list:
                    temp_type = []
                    temp_type.append(p[1].type[0])
                    for i in range(1, len(p[1].type)):
                        if p[1].type[i] == "*":
                            temp_type[0] += " *"
                        else:
                            temp_type.append(p[1].type[i])

                    p[1].type = temp_type

                if (
                    p[1] is None
                    or p[3] is None
                    or p[1].type is None
                    or p[3].type is None
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Assignment cannot be performed at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )
                    return

                if "struct" in p[1].type[0]:
                    p[1].vars = entry["vars"]

                elif "struct *" in p[1].type:
                    p[1].vars = entry["vars"]

                elif "struct" in p[1].type[0]:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Multilevel pointer for structs not allowed at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                if "struct" in p[1].type and "struct" not in p[3].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Cannot assign non-struct value "
                        + str(p[3].type)
                        + " to struct type "
                        + str(p[1].type)
                        + " at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif (
                    "struct" in p[1].type
                    and "struct" in p[3].type
                    and p[1].type[1] != p[3].type[1]
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Incompatible struct types at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif (
                    p[1].type != []
                    and p[3].type != []
                    and p[1].type[0] in temp_list_aa
                    and p[3].type[0] not in temp_list_aa
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Type mismatch during assignment at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif (
                    p[1].type[0] not in temp_list_aa
                    and p[1].type[0][-1] != "*"
                    and p[3].type[0] in temp_list_aa
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Type mismatch during assignment at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif "arr" in p[1].type and "init_list" not in p[3].type:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Invalid array initialization at line "
                        + str(p.lineno(2))
                        + bcolors.ENDC
                    )

                elif (
                    "arr" not in p[1].type
                    and p[1].type[0][-1] == "*"
                    and p[3].type[0] not in temp_list_ii
                    and p[3].type[0][-1] != "*"
                    and "str" not in p[3].type
                ):
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Assignment between pointer and "
                        + str(p[3].type)
                        + " at line "
                        + str(p.lineno(2))
                        + "is incompatible"
                        + bcolors.ENDC
                    )

                p[0].type = p[1].type
                if p[0].type is None:
                    p[0].type = []

                isIn = True
                for single_type in p[0].type:
                    if single_type not in p[3].type:
                        isIn = False
                if (
                    isIn == False
                    and "arr" not in p[1].type
                    and "init_list" not in p[3].type
                ):
                    p[3].totype = p[0].type
                    p3str = "to"
                    for single_type in p[0].type:
                        p3str += "_" + single_type
                    p3str = p3str.replace(" ", "_")
                    if "*" == p[0].type[0][-1]:
                        p3str = "to_int_unsigned"
                    p3 = Node(p3str, [p[3]])

                else:
                    p3 = p[3]
                p[0].insert_edge([p[1], p3])

                if "struct" in p[0].type:
                    p[0].label += "_struct"
                elif (
                    len(p[0].type) > 0
                    and p[0].type[0][-1] == "*"
                    and "arr" not in p[0].type
                ):
                    p[0].label += "_int unsigned"
                else:
                    p[0].label += "_" + p[0].type[0]
                    if "unsigned" in p[0].type:
                        p[0].label += "_unsigned"
                p[0].label = p[0].label.replace(" ", "_")
                p[0].node.attr["label"] = p[0].label

        if self.symtab.error == True:
            return

        for var_name in p[0].variables:
            if (
                "struct" in p[0].variables[var_name]
                and "*" not in p[0].variables[var_name]
            ):
                found, entry = self.symtab.return_sym_tab_entry(var_name, p.lineno(1))
                if found and found["variable_scope"] == "Local":
                    for var in found["vars"]:
                        found["vars"][var][
                            "temp"
                        ] = f'-{-found["vars"][var]["offset"] + self.symtab.offset}(%ebp)'
            found, entry = self.symtab.return_sym_tab_entry(var_name)
            if found["variable_scope"] == "Local":

                if found["offset"] > 0:
                    self.symtab.modify_symbol(
                        var_name,
                        "temp",
                        f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                    )
                else:
                    self.symtab.modify_symbol(
                        var_name,
                        "temp",
                        f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                    )
            p[0].temp = found["temp"]
        if len(p) == 4:
            if self.symtab.error == True:
                return
            if (
                p[3].totype is not None
                and p[3].totype != p[3].type
                and "init_list" not in p[3].type
                and "arr" not in p[3].totype
            ):
                p3.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p3.temp, 0)
                self.symtab.modify_symbol(p3.temp, "data_type", p[3].totype)
                self.symtab.modify_symbol(p3.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[3].totype, p3.temp)
                if self.symtab.is_global(p3.temp):
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p3.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p3.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":

                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p3.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p3.temp = found["temp"]
                currtype = []
                for single_type in p[3].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p3.temp,
                    p[3].temp,
                    " ".join(p[3].totype).replace(" ", "_") + cstr,
                )
            else:
                p3.temp = p[3].temp
            if self.symtab.is_global():
                print(
                    bcolors.FAIL + "Cannot initialize global variables while declaring"
                )
                self.symtab.error = True
                return
            else:
                self.equate(p[1].type, p[0].label, p[0].temp, p3.temp)
        if len(p) == 2:
            for var_name in p[0].variables:
                if self.symtab.is_global():
                    found, entry = self.symtab.return_sym_tab_entry(var_name)
                    self.three_address_code.global_variables.append(
                        [p[1].temp, found["allocated_size"]]
                    )
                    found, entry = self.symtab.return_sym_tab_entry(var_name)
                    # found["temp"] = (
                    #     found["temp"] + "." + str(self.three_address_code.counter_static)
                    # )
                    self.three_address_code.counter_static += 1
                    self.three_address_code.static_variables.append(
                        [found["temp"], None, found["allocated_size"]]
                    )

    def p_type_specifier(self, p):
        """type_specifier : VOID
        | CHAR
        | SHORT
        | INT
        | FLOAT
        | SIGNED
        | UNSIGNED
        | struct_specifier
        | BOOL
        """
        if self.error == True:
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

    def p_struct_specifier(self, p):
        """struct_specifier : struct IDENTIFIER '{' marker_struct_1 struct_declaration_list '}' marker_struct_0
        | struct IDENTIFIER
        """
        if self.error == True:
            return
        p[0] = p[1]
        p[0].type += [p[2]["lexeme"]]

        if len(p) == 8:
            p2val = p[2]["lexeme"]
            p[2] = Node(str([p[2]["lexeme"]]))

            p[0].node.attr["label"] = p[0].node.attr["label"] + "{}"
            p[0].label = p[0].node.attr["label"]

            if (p[2] is not None) and (p[2].node is not None):
                if (p[5] is not None) and (p[5].node is not None):
                    p[0].insert_edge([p[2], p[5]])
                else:
                    p[0].insert_edge([p[2]])
            else:
                if (p[5] is not None) and (p[5].node is not None):
                    p[0].insert_edge([p[5]])

            data_struct_found = self.symtab.return_type_tab_entry_su(
                p2val, p[1].type[0], p.lineno(1)
            )
            struct_size = 0
            for var in data_struct_found["vars"]:
                if "allocated_size" in data_struct_found["vars"][var].keys():
                    if p[1].type[0] == "struct":
                        struct_size += data_struct_found["vars"][var]["allocated_size"]
                    else:
                        struct_size = max(
                            struct_size,
                            data_struct_found["vars"][var]["allocated_size"],
                        )

            self.symtab.modify_symbol_su(
                p2val, "allocated_size", struct_size, p.lineno(1), 1
            )
            datatype_size[f"{p[1].type[0]} {p2val}"] = struct_size

        elif len(p) == 3:
            pval = p[2]["lexeme"]
            p[2] = Node(str(pval))
            if (
                self.symtab.return_type_tab_entry_su(
                    p[2].label, p[0].label, p.lineno(2)
                )
                is None
            ):
                self.symtab.error = True
            else:
                p[0].extraVals.append(pval)
                p[0].extraVals.append(p[1].label)
                p[0].insert_edge([p[2]])

    def p_marker_struct_0(self, p):
        """
        marker_struct_0 :
        """
        if self.error == True:
            return
        self.symtab.flag = 0

    def p_marker_struct_1(self, p):
        """
        marker_struct_1 :
        """
        if self.error == True:
            return
        identity = p[-2]["lexeme"]
        type_name = p[-3].label.upper()
        line_num = p[-2]["additional"]["line"]
        self.symtab.flag = 1
        self.symtab.insert_symbol(identity, line_num, type_name)
        self.symtab.flag = 2

    def p_struct(self, p):
        """struct : STRUCT"""
        if self.error == True:
            return
        p[0] = Node(str(p[1]))
        p[0].type = [str(p[1]).lower()]
        p[0].line = p.lineno(1)

    def p_struct_declaration_list(self, p):
        """struct_declaration_list : struct_declaration
        | struct_declaration_list struct_declaration
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[2]
            if (p[1] is not None) and (p[1].node is not None):
                p[0].insert_edge([p[1]])

    def p_struct_declaration(self, p):
        """struct_declaration : specifier_qualifier_list struct_declarator_list ';'"""
        if self.error == True:
            return
        p[0] = Node("struct_declaration", [p[1], p[2]])
        if p[1].type is None:
            p[1].type = []
        temp_list = []
        for i in p[1].type:
            if i != "*":
                temp_list.append(i)

        length = len(set(temp_list))
        if len(temp_list) != length:
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Structure variable cannot have duplicating type of declarations at line "
                + str(p.lineno(3))
                + bcolors.ENDC
            )
            return

        if "signed" in p[1].type and "unsigned" in p[1].type:
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Function type cannot be both signed and unsigned at line "
                + str(p.lineno(3))
                + bcolors.ENDC
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

            if count > 1:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "There have been 2 or more conflicting data types specified for a variable at Line No.: "
                    + str(p.lineno(3))
                    + bcolors.ENDC,
                )

        if "struct" in p[1].type[0]:
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Nested structuress at line number "
                + str(p.lineno(3))
                + " not supported"
                + bcolors.ENDC
            )

    def p_specifier_qualifier_list(self, p):
        """specifier_qualifier_list : type_specifier
        | type_specifier specifier_qualifier_list
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = p[1]

            for i in p[2].type:
                p[0].type.append(i)
            if (p[2] is not None) and (p[2].node is not None):
                p[2].insert_edge([p[2]])
                p[0].extraVals += p[2].extraVals

    def p_struct_declarator_list(self, p):
        """struct_declarator_list : struct_declarator
        | struct_declarator_list ',' structDeclaratorMarkerStart struct_declarator
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            p[0] = Node(",", [p[1], p[4]])
        p[0].extraVals = p[-1].extraVals

    def p_structDeclaratorMarkerStart(self, p):
        """structDeclaratorMarkerStart :"""
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        p[0].extraVals = p[-2].extraVals

    def p_struct_declarator(self, p):
        """struct_declarator : declarator"""
        if self.error == True:
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
            p[0].append_dict(value)

        for name in p[0].variables.keys():
            self.symtab.modify_symbol(
                name, "data_type", p[0].variables[name], p.lineno(0)
            )
            self.symtab.modify_symbol(name, "variable_scope", "Local", p.lineno(0))

            if p[0].variables[name]:
                hold = 1
                for tname in p[0].variables[name]:
                    if tname[0] == "[" and tname[-1] == "]":
                        hold *= int(tname[1:-1])
                    else:
                        break

                if "*" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * datatype_size["ptr"], p.lineno(0)
                    )
                elif "struct" in p[0].variables[name]:
                    struct_size = 0
                    found = self.symtab.return_type_tab_entry_su(
                        p[0].variables[name][-2], p[0].variables[name][-1], p.lineno(1)
                    )
                    if found:
                        if "allocated_size" in found.keys():
                            struct_size = found["allocated_size"]
                        else:
                            struct_size = 0
                            print(
                                bcolors.FAIL
                                + "Defining object of the same struct within itself isn't allowed."
                                + bcolors.ENDC
                            )

                            self.symtab.error = True
                        self.symtab.modify_symbol(
                            name, "allocated_size", hold * struct_size, p.lineno(1)
                        )
                    else:
                        self.symtab.error = True
                elif "float" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name,
                        "allocated_size",
                        hold * datatype_size["float"],
                        p.lineno(0),
                    )
                elif "short" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name,
                        "allocated_size",
                        hold * datatype_size["short"],
                        p.lineno(0),
                    )
                elif "int" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name, "allocated_size", hold * datatype_size["int"], p.lineno(0)
                    )
                elif "char" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name,
                        "allocated_size",
                        hold * datatype_size["char"],
                        p.lineno(0),
                    )
                elif "bool" in p[0].variables[name]:
                    self.symtab.modify_symbol(
                        name,
                        "allocated_size",
                        hold * datatype_size["bool"],
                        p.lineno(0),
                    )
                else:
                    self.symtab.modify_symbol(
                        name,
                        "allocated_size",
                        hold * datatype_size["void"],
                        p.lineno(0),
                    )
            else:
                self.symtab.modify_symbol(name, "allocated_size", 0, p.lineno(0))

    def p_declarator(self, p):
        """declarator : pointer direct_declarator
        | direct_declarator
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node("Declarator", [p[1], p[2]])
            p[0].variables = p[2].variables
            for value in p[1].extraVals:
                p[0].append_dict(value)
            p[0].temp = p[2].temp

    def p_function_declarator(self, p):
        """function_declarator : pointer direct_declarator
        | direct_declarator
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = Node("Declarator", [p[1], p[2]])
            p[0].variables = p[2].variables
            p[0].extraVals += p[1].extraVals

    def p_direct_declarator_1(self, p):
        """direct_declarator : identifier
        | '(' declarator ')'
        | direct_declarator '[' ']'
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]

        elif len(p) == 4:
            if p[1] == "(":
                p[0] = p[2]
            elif p[2] == "[":
                p[0] = Node("DirectDeclaratorArraySubscript", [p[1]])
                p[0].variables = p[1].variables
                p[0].append_dict("[]")
                try:
                    p[0].array = p[1].array
                except:
                    p[0].array = []
                p[0].array.append("empty")

    def p_direct_declarator_2(self, p):
        """direct_declarator : direct_declarator '[' integer_constant ']'
        | direct_declarator '(' marker_function_push ')'
        """
        if self.error == True:
            return

        if p[2] == "(":
            if p[3] is None:
                p[0] = Node("DirectDeclaratorFunctionCall", [p[1]])
                p[0].variables = p[1].variables
                p[0].append_dict("Function Name")
            else:
                p[0] = Node("DirectDeclaratorFunctionCallWithIdList", [p[1], p[3]])

        elif p[2] == "[":
            p[0] = Node("DirectDeclaratorArraySubscript", [p[1], p[3]])
            store = "[" + str(p[3].label) + "]"
            p[0].variables = p[1].variables
            p[0].append_dict(store)

    def p_direct_declarator_3(self, p):
        """direct_declarator : direct_declarator '(' marker_function_push parameter_type_list ')'"""
        if self.error == True:
            return

        p[0] = Node("DirectDeclaratorFunctionCall", [p[1], p[4]])
        for variable in p[4].variables:
            if variable == p[1].label:
                self.symtab.error = True
                self.error = True
                print(
                    bcolors.FAIL
                    + f"Cannot have function parameter with same name as function at line {p.lineno(2)}"
                )
                return
        p[0].variables = p[4].variables
        p[0].variables[p[1].label] = ["Function Name"]

    def p_marker_function_push(self, p):
        """marker_function_push :"""
        if self.error == True:
            return
        p[0] = None
        self.symtab.push_scope(self.three_address_code)
        self.symtab.offset = 0

    def p_pointer(self, p):
        """pointer : '*'
        | '*' pointer
        """
        if self.error == True:
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
        if self.error == True:
            return
        p[0] = p[1]

    def p_parameter_list(self, p):
        """parameter_list : parameter_declaration
        | parameter_list ',' parameter_declaration
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = Node(",", [p[1], p[3]])
            p[0].variables = {**p[1].variables, **p[3].variables}

    def p_parameter_declaration(self, p):
        """parameter_declaration : declaration_specifiers declarator"""
        if self.error == True:
            return
        p[0] = Node("ParDecl", [p[1], p[2]], create_ast=False)
        p[0].variables = p[2].variables
        p[1].remove_graph()
        p[2].remove_graph()

        for val in p[1].extraVals:
            p[0].append_dict(val)

    def p_type_name(self, p):
        """type_name : specifier_qualifier_list
        | specifier_qualifier_list abstract_declarator
        """
        if self.error == True:
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
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = Node("Abstract Declarator", [p[1]])
            p[0].type = p[1].type

        else:
            p[0] = Node("Abstract Declarator", [p[1], p[2]])
            p[0].type = p[1].type
            if p[2].type:
                for single_type in p[2].type:
                    p[0].type.append(single_type)

    def p_direct_abstract_declarator(self, p):
        """direct_abstract_declarator : '(' abstract_declarator ')'
        | '[' ']'
        | '[' constant_expression ']'
        | direct_abstract_declarator '[' ']'
        | direct_abstract_declarator '[' integer_constant ']'
        | '(' ')'
        | '(' parameter_type_list ')'
        | direct_abstract_declarator '(' ')'
        | direct_abstract_declarator '(' parameter_type_list ')'
        """
        if self.error == True:
            return

        if len(p) == 3:
            if p[1] == "(":
                p[0] = Node("DirectAbstractDeclarator()")
            elif p[1] == "[":
                p[0] = Node("DirectAbstractDeclarator[]")

        elif len(p) == 4:
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
        if self.error == True:
            return
        p[0] = p[1]

    def p_labeled_statement_1(self, p):
        """
        labeled_statement : marker_case_1 CASE constant_expression marker_case_2 ':' statement
        """
        if self.error == True:
            return
        p[0] = Node("CASE:", [p[3], p[6]])
        p[0].numdef = p[6].numdef
        if self.symtab.error == True:
            return
        p[0].break_list = p[6].break_list
        p[0].next_list = p[6].next_list
        p[0].test_list.append([p[3].temp, p[1].quadruples, p[4].quadruples])

    def p_labeled_statement_2(self, p):
        """
        labeled_statement : marker_case_1 DEFAULT ':' statement
        """
        if self.error == True:
            return
        p[0] = Node("DEFAULT:", [p[4]])
        p[0].numdef = 1 + p[4].numdef
        if self.symtab.error == True:
            return
        p[0].break_list = p[4].break_list
        p[0].next_list = p[4].next_list
        p[0].test_list.append([None, p[1].quadruples, None])

    def p_marker_case_1(self, p):
        """
        marker_case_1 :
        """
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].quadruples = self.three_address_code.next_statement

    def p_marker_case_2(self, p):
        """
        marker_case_2 :
        """
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].quadruples = self.three_address_code.next_statement

    def p_compound_statement(self, p):
        """
        compound_statement  : '{' marker_compound_statement_push '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push statement_list '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push declaration_list '}' marker_compound_statement_pop
                            | '{' marker_compound_statement_push declaration_list marker_global statement_list '}' marker_compound_statement_pop
        """
        if self.error == True:
            return

        if len(p) == 5:
            p[0] = Node("Empty SCOPE", create_ast=False)

        elif len(p) == 6:
            p[0] = Node("SCOPE", [p[3]])
            if self.symtab.error == True:
                return
            p[0].numdef = p[3].numdef
            p[0].true_list = p[3].true_list
            p[0].false_list = p[3].false_list
            p[0].break_list = p[3].break_list
            p[0].continuelist = p[3].continuelist
            p[0].next_list = p[3].next_list
            p[0].test_list = p[3].test_list

        elif len(p) == 8:
            p[0] = Node(";", [p[3], p[5]])
            if self.symtab.error == True:
                return
            if p[3] is not None and p[5] is not None:
                p[0].numdef = p[3].numdef + p[5].numdef
            self.three_address_code.backpatch(p[3].next_list, p[4].quadruples)
            if p[3] != None:
                p[0].break_list = p[3].break_list + p[5].break_list
                p[0].continuelist = p[3].continuelist + p[5].continuelist
                p[0].next_list = p[5].next_list
                p[0].test_list = p[3].test_list + p[5].test_list
            else:
                p[0].break_list = p[3].break_list
                p[0].continuelist = p[3].continuelist
                p[0].test_list = p[3].test_list
            p[0] = Node("SCOPE", [p[0]])

    def p_statement_list(self, p):
        """
        statement_list  : statement
                        | statement_list marker_global statement
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]
            if p[1] is not None:
                p[0].numdef = p[1].numdef
            if p[1] != None and not self.symtab.error:
                p[0].true_list = p[1].true_list
                p[0].false_list = p[1].false_list
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].next_list = p[1].next_list
                p[0].test_list = p[1].test_list

        elif len(p) == 4:
            p[0] = Node(";", [p[1], p[3]])
            if self.symtab.error == True:
                return
            if p[1] is not None and p[3] is not None:
                p[0].numdef = p[1].numdef + p[3].numdef
            self.three_address_code.backpatch(p[1].next_list, p[2].quadruples)
            if p[3] != None:
                p[0].break_list = p[1].break_list + p[3].break_list
                p[0].continuelist = p[1].continuelist + p[3].continuelist
                p[0].next_list = p[3].next_list
                p[0].test_list = p[1].test_list + p[3].test_list
            else:
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].test_list = p[1].test_list

    def p_declaration_list(self, p):
        """
        declaration_list    : declaration
                            | declaration_list marker_global declaration
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = p[1]
            if p[1] is not None:
                p[0].numdef = p[1].numdef
            if p[1] != None and not self.symtab.error:
                p[0].true_list = p[1].true_list
                p[0].false_list = p[1].false_list
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].next_list = p[1].next_list
                p[0].test_list = p[1].test_list

        elif len(p) == 4:
            p[0] = Node(";", [p[1], p[3]])
            if self.symtab.error == True:
                return
            if p[1] is not None and p[3] is not None:
                p[0].numdef = p[1].numdef + p[3].numdef
            self.three_address_code.backpatch(p[1].next_list, p[2].quadruples)
            if p[3] != None:
                p[0].break_list = p[1].break_list + p[3].break_list
                p[0].continuelist = p[1].continuelist + p[3].continuelist
                p[0].next_list = p[3].next_list
                p[0].test_list = p[1].test_list + p[3].test_list
            else:
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].test_list = p[1].test_list

    def p_marker_compound_statement_push(self, p):
        """
        marker_compound_statement_push :
        """
        if self.error == True:
            return
        self.symtab.push_scope(self.three_address_code)

    def p_marker_compound_statement_pop(self, p):
        """
        marker_compound_statement_pop :
        """
        if self.error == True:
            return
        self.symtab.pop_scope(self.three_address_code)

    def p_block_item_list(self, p):
        """
        block_item_list : block_item
                        | block_item_list marker_global block_item
        """
        if self.error == True:
            return

        if len(p) == 2:
            p[0] = Node(";", [p[1]])
            if p[1] is not None:
                p[0].numdef = p[1].numdef
            if p[1] != None and not self.symtab.error:
                p[0].true_list = p[1].true_list
                p[0].false_list = p[1].false_list
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].next_list = p[1].next_list
                p[0].test_list = p[1].test_list

        elif len(p) == 4:
            p[0] = Node(";", [p[1], p[3]])
            if self.symtab.error == True:
                return
            if p[1] is not None and p[3] is not None:
                p[0].numdef = p[1].numdef + p[3].numdef
            self.three_address_code.backpatch(p[1].next_list, p[2].quadruples)
            if p[3] != None:
                p[0].break_list = p[1].break_list + p[3].break_list
                p[0].continuelist = p[1].continuelist + p[3].continuelist
                p[0].next_list = p[3].next_list
                p[0].test_list = p[1].test_list + p[3].test_list
            else:
                p[0].break_list = p[1].break_list
                p[0].continuelist = p[1].continuelist
                p[0].test_list = p[1].test_list

    def p_block_item(self, p):
        """
        block_item : declaration
                    | statement
        """
        if self.error == True:
            return

        p[0] = p[1]

    def p_expression_statement(self, p):
        """
        expression_statement    : ';'
                                | expression ';'
        """
        if self.error == True:
            return
        if len(p) == 2:
            p[0] = Node("EmptyExprStmt")
        if len(p) == 3:
            p[0] = p[1]

    def p_selection_statement(self, p):
        """
        selection_statement : IF '(' expression ')' marker_global statement marker_global_2 %prec IF_STATEMENTS
                            | IF '(' expression ')' marker_global statement marker_global_2 ELSE marker_global statement
                            | SWITCH '(' expression ')' marker_switch statement
        """
        if self.error == True:
            return

            return
        if len(p) == 7:
            p[0] = Node(str(p[1]).upper(), [p[3], p[6]])
            if p[6].numdef > 1:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + f"Cannot have multiple default labels in a single switch statement at line {p.lineno(1)}"
                )
            if self.symtab.error == True:
                return
            p[0].next_list = p[6].break_list + p[6].next_list
            p[0].next_list.append(self.three_address_code.next_statement)
            self.three_address_code.emit("goto", "", "", "")
            self.three_address_code.backpatch(
                p[5].next_list, self.three_address_code.next_statement
            )
            for item in p[6].test_list:
                if item[0] is not None:
                    for i in range(item[1], item[2]):
                        self.three_address_code.code.append(
                            self.three_address_code.code[i]
                        )
                        self.three_address_code.next_statement += 1
                    temp = self.three_address_code.create_temp_var()
                    self.symtab.insert_symbol(temp, 0)
                    self.symtab.modify_symbol(temp, "data_type", ["int"])
                    self.symtab.modify_symbol(temp, "identifier_type", "TEMP")
                    self.symtab_size_update(["int"], temp)
                    if self.symtab.is_global(temp):
                        self.symtab.modify_symbol(temp, "variable_scope", "Global")
                    else:
                        self.symtab.modify_symbol(temp, "variable_scope", "Local")
                        found, entry = self.symtab.return_sym_tab_entry(temp)
                        var_size = found["allocated_size"]
                        if found["variable_scope"] == "Local":
                            if found["offset"] > 0:
                                self.symtab.modify_symbol(
                                    temp,
                                    "temp",
                                    f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                                )
                            else:
                                self.symtab.modify_symbol(
                                    temp,
                                    "temp",
                                    f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                                )
                        temp = found["temp"]
                    self.three_address_code.emit("==", temp, p[3].temp, item[0])
                    tmplist = [self.three_address_code.next_statement]
                    self.three_address_code.emit("ifnz goto", "", temp, "")
                    self.three_address_code.backpatch(tmplist, item[1])

            for item in p[6].test_list:
                if item[0] is None:
                    tmplist = [self.three_address_code.next_statement]
                    self.three_address_code.emit("goto", "", "", "")
                    self.three_address_code.backpatch(tmplist, item[1])
        elif len(p) == 8:
            p[0] = Node("IF-ELSE", [p[3], p[6]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[3].true_list, p[5].quadruples)
            p[0].next_list = p[3].false_list + p[6].next_list
            p[0].continuelist = p[6].continuelist
            p[0].break_list = p[6].break_list
            p[0].test_list = p[6].test_list
        else:
            p[0] = Node("IF-ELSE", [p[3], p[6], p[10]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[3].true_list, p[5].quadruples)
            self.three_address_code.backpatch(p[3].false_list, p[9].quadruples)
            p[0].next_list = p[6].next_list + p[7].next_list + p[10].next_list
            p[0].continuelist = p[6].continuelist + p[10].continuelist
            p[0].break_list = p[6].break_list + p[10].break_list
            p[0].test_list = p[6].test_list + p[10].test_list

    def p_marker_switch(self, p):
        """
        marker_switch :
        """
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].next_list.append(self.three_address_code.next_statement)
        self.three_address_code.emit("goto", "", "", "")

    def p_marker_global(self, p):
        """
        marker_global :
        """
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].quadruples = self.three_address_code.next_statement

    def p_marker_global_2(self, p):
        """
        marker_global_2 :
        """
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].next_list.append(self.three_address_code.next_statement)
        self.three_address_code.emit("goto", "", "", "")

    def p_iteration_statement_1(self, p):
        """
        iteration_statement : WHILE marker_global '(' expression ')' marker_global statement
                            | DO marker_global statement WHILE '(' marker_global expression ')' ';'
        """

        if True == self.error:
            return

        if len(p) == 8:
            p[0] = Node("WHILE", [p[4], p[6]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[7].next_list, p[2].quadruples)
            self.three_address_code.backpatch(p[7].continuelist, p[2].quadruples)
            self.three_address_code.backpatch(p[4].true_list, p[6].quadruples)
            p[0].next_list = p[4].false_list + p[7].break_list
            self.three_address_code.emit("goto", int(p[2].quadruples) + 1, "", "")

        elif len(p) == 10:
            p[0] = Node("DO-WHILE", [p[3], p[7]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[7].true_list, p[2].quadruples)
            p[0].next_list = p[7].false_list + p[3].break_list
            self.three_address_code.backpatch(p[3].next_list, p[6].quadruples)
            self.three_address_code.backpatch(p[3].continuelist, p[6].quadruples)
            self.three_address_code.emit("goto", p[2].quadruples + 1, "", "")

    def p_iteration_statement_2(self, p):
        """
        iteration_statement : FOR '(' expression_statement marker_global expression_statement ')' marker_global statement
                            | FOR '(' expression_statement marker_global expression_statement marker_global expression ')' marker_global statement
        """

        if True == self.error:
            return

        if len(p) == 9:
            p[0] = Node("FOR", [p[3], p[5], p[8]])

            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[8].next_list, p[4].quadruples)
            self.three_address_code.backpatch(p[8].continuelist, p[4].quadruples)
            self.three_address_code.backpatch(p[3].true_list, p[4].quadruples)
            self.three_address_code.backpatch(p[3].false_list, p[4].quadruples)
            self.three_address_code.backpatch(p[5].true_list, p[7].quadruples)
            p[0].next_list = p[8].break_list + p[5].false_list
            self.three_address_code.emit("goto", p[4].quadruples + 1, "", "")

        elif len(p) == 11:
            p[0] = Node("FOR", [p[3], p[5], p[7], p[10]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[3].true_list, p[4].quadruples)
            self.three_address_code.backpatch(p[3].false_list, p[4].quadruples)
            self.three_address_code.backpatch(p[10].next_list, p[6].quadruples)
            self.three_address_code.backpatch(p[10].continuelist, p[6].quadruples)
            self.three_address_code.backpatch(p[5].true_list, p[9].quadruples)
            self.three_address_code.backpatch(p[7].true_list, p[4].quadruples)
            self.three_address_code.backpatch(p[7].false_list, p[4].quadruples)
            p[0].next_list = p[10].break_list + p[5].false_list
            self.three_address_code.emit("goto", p[6].quadruples + 1, "", "")

    def p_iteration_statement_3(self, p):
        """iteration_statement : FOR '(' push_marker_loops declaration marker_global expression_statement ')' marker_global statement pop_marker_loops
        | FOR '(' push_marker_loops declaration marker_global expression_statement marker_global expression ')' marker_global statement pop_marker_loops
        """

        if self.error == True:
            return
        if len(p) == 11:
            p[0] = Node("FOR", [p[4], p[6], p[9]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[6].true_list, p[8].quadruples)
            self.three_address_code.backpatch(p[9].continuelist, p[5].quadruples)
            self.three_address_code.backpatch(p[9].next_list, p[5].quadruples)
            p[0].next_list = p[9].break_list + p[6].false_list
            self.three_address_code.emit("goto", p[5].quadruples + 1, "", "")
        else:
            p[0] = Node("FOR", [p[4], p[6], p[8], p[11]])
            if self.symtab.error == True:
                return
            self.three_address_code.backpatch(p[11].next_list, p[7].quadruples)
            self.three_address_code.backpatch(p[11].continuelist, p[7].quadruples)
            self.three_address_code.backpatch(p[6].true_list, p[10].quadruples)
            self.three_address_code.backpatch(p[8].true_list, p[5].quadruples)
            self.three_address_code.backpatch(p[8].false_list, p[5].quadruples)
            p[0].next_list = p[11].break_list + p[6].false_list
            self.three_address_code.emit("goto", p[7].quadruples + 1, "", "")

    def p_push_marker_loops(self, p):
        """
        push_marker_loops :
        """
        if self.error == True:
            return
        else:
            self.symtab.push_scope(self.three_address_code)

    def p_pop_marker_loops(self, p):
        """
        pop_marker_loops :
        """
        if True == self.error:
            return
        else:
            if self.symtab.error == True:
                return
            self.symtab.pop_scope(self.three_address_code, 1)

    def p_jump_statement(self, p):
        """
        jump_statement  : CONTINUE ';'
                        | BREAK ';'
                        | RETURN ';'
                        | RETURN expression ';'
        """
        if self.error == True:
            return

        if len(p) == 3:
            p[0] = Node(str(p[1]).upper())
            if self.symtab.error == True:
                return
            if p[1] == "continue":
                p[0].continuelist.append(self.three_address_code.next_statement)
                self.three_address_code.emit("goto", "", "", "")
            elif p[1] == "break":
                p[0].break_list.append(self.three_address_code.next_statement)
                self.three_address_code.emit("goto", "", "", "")
            elif p[1] == "return":
                found = list(self.symtab.table[0])
                functype = self.symtab.table[0][found[-1]]["data_type"]

                if functype != ["void"]:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Cannot return"
                        + str(functype)
                        + " at line "
                        + str(p.lineno(1))
                        + bcolors.ENDC
                    )
                if self.symtab.error == True:
                    return
                self.three_address_code.emit("retq", "", "", "")
        else:
            p[0] = Node("RETURN")
            found = list(self.symtab.table[0])
            if not "data_type" in self.symtab.table[0][found[-1]].keys():
                self.symtab.error = True
                return
            functype = self.symtab.table[0][found[-1]]["data_type"]
            if functype is None:
                functype = []

            if p[2] is None or p[2].type is None or p[2].type == []:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Cannot return expression at line  "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                "*" in functype
                and len(p[2].type) > 0
                and "*" not in p[2].type[0]
                and p[2].type[0] not in ["bool", "char", "short", "int"]
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Incompatible types while returning "
                    + str(p[2].type)
                    + "."
                    + str(functype)
                    + " was expected at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif (
                len(p[2].type) > 0
                and len(functype) > 0
                and functype[0] in ["bool", "char", "short", "int", "float"]
                and p[2].type[0] not in ["bool", "char", "short", "int", "float"]
                and p[2].type[0][-1] != "*"
            ):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Mismatch in type while returning value at line "
                    + str(p.lineno(1))
                    + bcolors.ENDC
                )

            elif functype == ["void"] and len(p[2].type) > 0 and p[2].type[0] != "void":
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Non void type at line number "
                    + str(p.lineno(1))
                    + ". Cannot return."
                    + bcolors.ENDC
                )

            if self.symtab.error == True:
                return
            isarr = 0
            type_list = functype
            if type_list is None:
                type_list = []
            for i in range(len(functype)):
                if functype[i][0] == "[" and functype[i][-1] == "]":
                    isarr += 1
            if "unsigned" in type_list or "signed" in type_list:
                if (
                    "bool" not in type_list
                    and "char" not in type_list
                    and "short" not in type_list
                ):
                    type_list.append("int")
                p[0].type = []
            elif "int" in type_list:
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

            if "struct" in type_list:
                p[0].type.append("struct")
                for single_type in type_list:
                    if single_type != "struct":
                        p[0].type.append(single_type)
            if isarr > 0:
                temp_type = []
                temp_type.append(p[0].type[0])
                for i in range(isarr):
                    temp_type[0] += " *"
                for i in range(len(p[0].type)):
                    if i > isarr:
                        temp_type.append(p[0].type[i])
                p[0].type = temp_type
                p[0].type.append("arr")
                for i in range(len(type_list)):
                    if (
                        type_list[len(type_list) - i - 1][0] == "["
                        and type_list[len(type_list) - i - 1][-1] == "]"
                    ):
                        p[0].type.append(type_list[len(type_list) - i - 1])

            if "void" in type_list:
                p[0].type.append("void")
                for single_type in type_list:
                    if single_type != "void":
                        p[0].type.append(single_type)

            if "*" in type_list:
                temp_type = []
                temp_type.append(p[0].type[0])
                for i in range(1, len(p[0].type)):
                    if p[0].type[i] == "*":
                        temp_type[0] += " *"
                    else:
                        temp_type.append(p[0].type[i])
                p[0].type = temp_type
            if ("struct" in p[0].type) and p[0].type != p[2].type:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Need struct of type"
                    + str(p[0].type)
                    + ", instead got return type "
                    + str(p[2].type)
                    + "at line"
                    + str(p.lineno(1))
                    + "."
                    + bcolors.ENDC
                )
                return

            isin = True
            for single_type in p[0].type:
                if single_type not in p[2].type:
                    isin = False
            if isin == False:
                p[2].totype = p[0].type
                p2str = "to"
                for single_type in p[0].type:
                    p2str += "_" + single_type
                p2str = p2str.replace(" ", "_")
                if "*" == p[0].type[0][-1]:
                    p2str = "to_int_unsigned"
                p2 = Node(p2str, [p[2]])
            else:
                p2 = p[2]
            p[0].insert_edge([p2])
            if self.symtab.error == True:
                return
            if p[2].totype is not None and p[2].totype != p[2].type:
                p2.temp = self.three_address_code.create_temp_var()
                self.symtab.insert_symbol(p2.temp, 0)
                self.symtab.modify_symbol(p2.temp, "data_type", p[2].totype)
                self.symtab.modify_symbol(p2.temp, "identifier_type", "TEMP")
                self.symtab_size_update(p[2].totype, p2.temp)
                if self.symtab.is_global(p2.temp):
                    self.symtab.modify_symbol(p2.temp, "variable_scope", "Global")
                else:
                    self.symtab.modify_symbol(p2.temp, "variable_scope", "Local")
                    found, entry = self.symtab.return_sym_tab_entry(p2.temp)
                    var_size = found["allocated_size"]
                    if found["variable_scope"] == "Local":
                        if found["offset"] > 0:
                            self.symtab.modify_symbol(
                                p2.temp,
                                "temp",
                                f'-{found["offset"] + found["allocated_size"] }(%ebp)',
                            )
                        else:
                            self.symtab.modify_symbol(
                                p2.temp,
                                "temp",
                                f'{-found["offset"] - found["allocated_size"] }(%ebp)',
                            )
                    p2.temp = found["temp"]
                currtype = []
                for single_type in p[2].type:
                    if (
                        single_type != "arr"
                        and single_type[0] != "["
                        and single_type[-1] != "]"
                    ):
                        currtype.append(single_type)
                cstr = "," + " ".join(currtype).replace(" ", "_")
                self.three_address_code.emit(
                    "cast",
                    p2.temp,
                    p[2].temp,
                    " ".join(p[2].totype).replace(" ", "_") + cstr,
                )
            else:
                p2.temp = p[2].temp
            if ("struct" in p[0].type) and ("*" not in p[0].type):
                temp_type = " ".join(p[0].type)
                self.three_address_code.emit(
                    "retq_struct", p[2].temp, datatype_size[temp_type], ""
                )
            else:
                self.three_address_code.emit("retq", p2.temp, "", "")

    def p_translation_unit(self, p):
        """translation_unit : translation_unit external_declaration
        | external_declaration
        """
        if self.error == True:
            return

        p[0] = self.ast_root
        if len(p) == 2:
            if (p[1] is not None) and (p[1].node is not None):
                p[0].insert_edge([p[1]])
        elif len(p) == 3:
            if (p[2] is not None) and (p[2].node is not None):
                p[0].insert_edge([p[2]])

    def p_external_declaration(self, p):
        """external_declaration : function_definition
        | declaration
        """
        if self.error == True:
            return
        p[0] = p[1]

    def p_function_definition(self, p):
        """function_definition :  declaration_specifiers function_declarator '{' marker_function_start '}' marker_function_end
        | declaration_specifiers function_declarator '{' marker_function_start block_item_list '}' marker_function_end
        """
        if self.error == True:
            return
        line = 0
        if len(p) == 7:
            p[0] = Node("function", [p[2]])
            line = 3

        elif len(p) == 8:
            p[0] = Node("function", [p[2], Node("SCOPE", [p[5]])])
            line = 3
            if not self.symtab.error:
                self.three_address_code.backpatch(p[5].next_list, p[7].quadruples)
                self.three_address_code.backpatch(p[5].break_list, p[7].quadruples)
        p[1].remove_graph()

        temp_list = []
        if p[1].type is None:
            p[1].type = []

        for i in p[1].type:
            if i != "*":
                temp_list.append(i)

        val = len(set(temp_list))
        if len(temp_list) != val:
            self.symtab.error = True
            print(
                bcolors.FAIL
                + "Function type cannot have duplicating type of declarations at line "
                + str(p.lineno(line))
                + bcolors.ENDC
            )

        if "unsigned" in p[1].type and "signed" in p[1].type:
            self.symtab.error = True
            print(
                bcolors.fail
                + "Function type cannot be both signed and unsigned at line "
                + str(p.lineno(line))
                + bcolors.ENDC
            )

        else:
            cnt = 0
            if (
                "signed" in p[1].type
                or "unsigned" in p[1].type
                or "int" in p[1].type
                or "short" in p[1].type
            ):
                cnt = cnt + 1
            if "char" in p[1].type:
                cnt = cnt + 1
            if "bool" in p[1].type:
                cnt = cnt + 1
            if "void" in p[1].type:
                cnt = cnt + 1
            if "float" in p[1].type:
                cnt = cnt + 1
            if "struct" in p[1].type:
                cnt = cnt + 1

            if cnt > 1:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "Two or more conflicting data types specified for function at line "
                    + str(p.lineno(line))
                    + bcolors.ENDC
                )

        if self.symtab.error == True:
            return

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
                        print(
                            bcolors.FAIL
                            + "Multidimensional array must have bound for all dimensions except first at line "
                            + str(p.lineno(line))
                            + bcolors.ENDC
                        )

                    if int(temp_arr[i]) <= 0 and temp_arr[i] != "":
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Array bound cannot be non-positive at line "
                            + str(p.lineno(line))
                            + bcolors.ENDC
                        )

        if self.symtab.error == True:
            return

        for key in p[2].variables.keys():
            if p[2].variables[key][0] == "Function Name":
                function_name = key
                break

        if self.symtab.error == True:
            return

        func, entry = self.symtab.return_sym_tab_entry(function_name)
        func_type = func["data_type"]

        if "void" in func_type and len(func_type) == 1:
            self.three_address_code.emit("retq", "", "", "")
        else:
            self.three_address_code.emit("retq", "$0", "", "")
        self.three_address_code.emit("", "", "", "")
        for var in entry["scope"][0]:
            if var == "struct":
                continue
            if var == "scope":
                continue
            if var == "scope_num":
                continue
            if var[0] == "$":
                continue
            param = entry["scope"][0][var]

            temp_type_list = []
            temp2_type_list = []
            nums_arr = []
            ctrpar = -1
            for single_type in param["data_type"]:
                ctrpar += 1
                if single_type != "*":
                    temp_type_list.append(single_type)
                    if single_type[0] != "[" or single_type[-1] != "]":
                        temp2_type_list.append(single_type)

                if single_type[0] == "[" and single_type[-1] == "]":
                    if single_type[1:-1] == "" and ctrpar != 0:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot have empty indices for array declarations at line "
                            + str(param["line"])
                            + bcolors.ENDC
                        )
                        return
                    elif single_type[1:-1] != "" and int(single_type[1:-1]) <= 0:
                        self.symtab.error = True
                        print(
                            bcolors.FAIL
                            + "Cannot have non-positive integers for array declarations at line "
                            + str(param["line"])
                            + bcolors.ENDC
                        )
                        return

            if len(temp2_type_list) >= 2 and temp2_type_list[1] == "unsigned":
                temp2_type_list = temp2_type_list[:2]
            if len(temp2_type_list) != len(set(temp2_type_list)):
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "variables cannot have duplicating type of declarations at line",
                    param["line"],
                )
                return

            if "unsigned" in param["data_type"] and "signed" in param["data_type"]:
                self.symtab.error = True
                print(
                    bcolors.FAIL
                    + "variable cannot be both signed and unsigned at line",
                    param["line"],
                )
                return
            elif "void" in param["data_type"] and "*" not in param["data_type"]:
                self.symtab.error = True
                print(
                    bcolors.FAIL + "Cannot have a void type variable at line ",
                    param["line"],
                )
                return
            else:
                data_type_count = 0
                if (
                    "int" in param["data_type"]
                    or "short" in param["data_type"]
                    or "unsigned" in param["data_type"]
                    or "signed" in param["data_type"]
                ):
                    data_type_count += 1
                if "char" in param["data_type"]:
                    data_type_count += 1
                if "bool" in param["data_type"]:
                    data_type_count += 1
                if "float" in param["data_type"]:
                    data_type_count += 1
                if "void" in param["data_type"]:
                    data_type_count += 1
                if "struct" in param["data_type"]:
                    data_type_count += 1
                if data_type_count > 1:
                    self.symtab.error = True
                    print(
                        bcolors.FAIL
                        + "Two or more conflicting data types specified for variable at line "
                        + str(param["line"])
                        + bcolors.ENDC
                    )
                    return

    def p_marker_function_start(self, p):
        """marker_function_start :"""
        if self.error == True:
            return
        p[0] = Node("", create_ast=False)
        p[0].variables = p[-2].variables
        function_name = str()
        tosearch = "Function Name"
        valtype = "function"

        for key in p[0].variables.keys():
            if p[0].variables[key] is None or p[0].variables[key] == []:
                self.error = True
                print(bcolors.FAIL + "Invalid syntax" + bcolors.ENDC)
                return
            if p[0].variables[key][0] == tosearch:
                function_name = key
                break

        p[0].variables[key] = p[0].variables[key] + p[-3].extraVals + p[-2].extraVals

        self.symtab.modify_symbol(
            function_name, "identifier_type", valtype, p.lineno(0)
        )
        param_nums = 0

        for var_name in p[0].variables.keys():
            if not var_name == function_name:

                if p[0].variables[var_name] and (
                    p[0].variables[var_name][-1] == "struct"
                ):
                    found = self.symtab.return_type_tab_entry_su(
                        p[0].variables[var_name][-2],
                        p[0].variables[var_name][-1],
                        p.lineno(0),
                    )
                    if found:
                        self.symtab.modify_symbol(
                            var_name,
                            "identifier_type",
                            found["identifier_type"],
                            p.lineno(0),
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
                self.symtab.modify_symbol(
                    var_name, "identifier_type", "parameter", p.lineno(0)
                )
                param_nums = param_nums + 1

                if p[0].variables[var_name]:
                    is_global = self.symtab.is_global(var_name)
                    if is_global:
                        self.symtab.modify_symbol(
                            var_name, "variable_scope", "Global", p.lineno(0)
                        )
                    else:
                        self.symtab.modify_symbol(
                            var_name, "variable_scope", "Local", p.lineno(0)
                        )

                if p[0].variables[var_name]:
                    prod = 1

                    szstr = "allocated_size"
                    vct = [
                        "struct",
                        "float",
                        "short",
                        "int",
                        "char",
                        "bool",
                        "void",
                    ]

                    if "*" in p[0].variables[var_name]:
                        self.symtab.modify_symbol(
                            var_name, szstr, prod * datatype_size["ptr"], p.lineno(0)
                        )

                    else:
                        for vc in vct:
                            if vc == "struct":
                                if vc in p[0].variables[var_name]:
                                    struct_size = 0
                                    found, tmp = self.symtab.return_type_tab_entry_su(
                                        p[0].variables[var_name][-2],
                                        p[0].variables[var_name][-1],
                                        p.lineno(0),
                                    )
                                    if found:
                                        struct_size = found[szstr]
                                    self.symtab.modify_symbol(
                                        var_name, szstr, prod * struct_size, p.lineno(0)
                                    )

                            else:
                                if vc in p[0].variables[var_name]:
                                    self.symtab.modify_symbol(
                                        var_name,
                                        szstr,
                                        prod * datatype_size[vc],
                                        p.lineno(0),
                                    )
            else:
                self.symtab.modify_symbol(
                    var_name, "data_type", p[0].variables[key][1:]
                )

        found, entry = self.symtab.return_sym_tab_entry(function_name)
        self.symtab.offset = 8
        if ("struct" in found["data_type"]) and ("*" not in found["data_type"]):
            self.symtab.offset = 12
        for var_name in p[0].variables.keys():
            if not var_name == function_name:
                if (
                    "struct" in p[0].variables[var_name]
                    and "*" not in p[0].variables[var_name]
                ):
                    found, entry = self.symtab.return_sym_tab_entry(var_name)
                    if found:
                        for var in found["vars"]:
                            found["vars"][var][
                                "temp"
                            ] = f'{found["vars"][var]["offset"] + self.symtab.offset}(%ebp)'

                found, entry = self.symtab.return_sym_tab_entry(var_name)
                alignedSz = self.symtab.top_scope[var_name][szstr]
                self.symtab.offset += alignedSz
                self.symtab.modify_symbol(
                    var_name, "offset", -(self.symtab.offset), p.lineno(0)
                )
                if found["offset"] > 0:
                    self.symtab.modify_symbol(
                        var_name, "temp", f'-{found["offset"] + alignedSz}(%ebp)'
                    )
                else:
                    self.symtab.modify_symbol(
                        var_name, "temp", f'{-found["offset"] - alignedSz}(%ebp)'
                    )

        self.symtab.modify_symbol(function_name, "num_parameters", param_nums)
        self.symtab.offset = 0
        if self.symtab.error == True:
            return

        self.three_address_code.emit(str(function_name) + ":", "", "", "")

    def p_marker_function_end(self, p):
        """marker_function_end :"""
        if self.error == True:
            return
        self.symtab.pop_scope(self.three_address_code)
        p[0] = Node("", create_ast=False)
        if self.symtab.error == True:
            return
        p[0].quadruples = self.three_address_code.next_statement

    def p_push_lib_functions(self, p):
        """
        push_lib_functions :
        """
        if self.error == True:
            return
        # printf with 2 arguments (string, placeholder value)
        self.symtab.insert_symbol("printf", -1)
        self.symtab.modify_symbol("printf", "identifier_type", "function")
        self.symtab.modify_symbol("printf", "data_type", ["void"])
        self.symtab.modify_symbol("printf", "num_parameters", 2)

        # scanf with 2 arguments (string, placeholder value)
        self.symtab.insert_symbol("scanf", -1)
        self.symtab.modify_symbol("scanf", "identifier_type", "function")
        self.symtab.modify_symbol("scanf", "data_type", ["void"])
        self.symtab.modify_symbol("scanf", "num_parameters", 2)

        # abs with a single argument
        self.symtab.insert_symbol("abs", -1)
        self.symtab.modify_symbol("abs", "identifier_type", "function")
        self.symtab.modify_symbol("abs", "data_type", ["int"])
        self.symtab.modify_symbol("abs", "num_parameters", 1)

        # sqrt with a single argument
        self.symtab.insert_symbol("sqrt", -1)
        self.symtab.modify_symbol("sqrt", "identifier_type", "function")
        self.symtab.modify_symbol("sqrt", "data_type", ["float"])
        self.symtab.modify_symbol("sqrt", "num_parameters", 1)

        # ceil with a single argument
        self.symtab.insert_symbol("ceil", -1)
        self.symtab.modify_symbol("ceil", "identifier_type", "function")
        self.symtab.modify_symbol("ceil", "data_type", ["float"])
        self.symtab.modify_symbol("ceil", "num_parameters", 1)

        # floor with a single argument
        self.symtab.insert_symbol("floor", -1)
        self.symtab.modify_symbol("floor", "identifier_type", "function")
        self.symtab.modify_symbol("floor", "data_type", ["float"])
        self.symtab.modify_symbol("floor", "num_parameters", 1)

        # pow with  2 arguments
        self.symtab.insert_symbol("pow", -1)
        self.symtab.modify_symbol("pow", "identifier_type", "function")
        self.symtab.modify_symbol("pow", "data_type", ["float"])
        self.symtab.modify_symbol("pow", "num_parameters", 2)

        # fabs with a single argument
        self.symtab.insert_symbol("fabs", -1)
        self.symtab.modify_symbol("fabs", "identifier_type", "function")
        self.symtab.modify_symbol("fabs", "data_type", ["float"])
        self.symtab.modify_symbol("fabs", "num_parameters", 1)

        # log with a single argument
        self.symtab.insert_symbol("log", -1)
        self.symtab.modify_symbol("log", "identifier_type", "function")
        self.symtab.modify_symbol("log", "data_type", ["float"])
        self.symtab.modify_symbol("log", "num_parameters", 1)

        # log10 with a single argument
        self.symtab.insert_symbol("log10", -1)
        self.symtab.modify_symbol("log10", "identifier_type", "function")
        self.symtab.modify_symbol("log10", "data_type", ["float"])
        self.symtab.modify_symbol("log10", "num_parameters", 1)

        # fmod with  2 arguments
        self.symtab.insert_symbol("fmod", -1)
        self.symtab.modify_symbol("fmod", "identifier_type", "function")
        self.symtab.modify_symbol("fmod", "data_type", ["float"])
        self.symtab.modify_symbol("fmod", "num_parameters", 2)

        # exp with a single argument
        self.symtab.insert_symbol("exp", -1)
        self.symtab.modify_symbol("exp", "identifier_type", "function")
        self.symtab.modify_symbol("exp", "data_type", ["float"])
        self.symtab.modify_symbol("exp", "num_parameters", 1)

        # cos with a single argument
        self.symtab.insert_symbol("cos", -1)
        self.symtab.modify_symbol("cos", "identifier_type", "function")
        self.symtab.modify_symbol("cos", "data_type", ["float"])
        self.symtab.modify_symbol("cos", "num_parameters", 1)

        # sin with a single argument
        self.symtab.insert_symbol("sin", -1)
        self.symtab.modify_symbol("sin", "identifier_type", "function")
        self.symtab.modify_symbol("sin", "data_type", ["float"])
        self.symtab.modify_symbol("sin", "num_parameters", 1)

        # acos with a single argument
        self.symtab.insert_symbol("acos", -1)
        self.symtab.modify_symbol("acos", "identifier_type", "function")
        self.symtab.modify_symbol("acos", "data_type", ["float"])
        self.symtab.modify_symbol("acos", "num_parameters", 1)

        # asin with a single argument
        self.symtab.insert_symbol("asin", -1)
        self.symtab.modify_symbol("asin", "identifier_type", "function")
        self.symtab.modify_symbol("asin", "data_type", ["float"])
        self.symtab.modify_symbol("asin", "num_parameters", 1)

        # tan with a single argument
        self.symtab.insert_symbol("tan", -1)
        self.symtab.modify_symbol("tan", "identifier_type", "function")
        self.symtab.modify_symbol("tan", "data_type", ["float"])
        self.symtab.modify_symbol("tan", "num_parameters", 1)

        # atan with a single argument
        self.symtab.insert_symbol("atan", -1)
        self.symtab.modify_symbol("atan", "identifier_type", "function")
        self.symtab.modify_symbol("atan", "data_type", ["float"])
        self.symtab.modify_symbol("atan", "num_parameters", 1)

        # strlen with a single argument
        self.symtab.insert_symbol("strlen", -1)
        self.symtab.modify_symbol("strlen", "identifier_type", "function")
        self.symtab.modify_symbol("strlen", "data_type", ["int"])
        self.symtab.modify_symbol("strlen", "num_parameters", 1)

        # strlwr with a single argument
        self.symtab.insert_symbol("strlwr", -1)
        self.symtab.modify_symbol("strlwr", "identifier_type", "function")
        self.symtab.modify_symbol("strlwr", "data_type", ["char", "*"])
        self.symtab.modify_symbol("strlwr", "num_parameters", 1)

        # strupr with a single argument
        self.symtab.insert_symbol("strupr", -1)
        self.symtab.modify_symbol("strupr", "identifier_type", "function")
        self.symtab.modify_symbol("strupr", "data_type", ["char", "*"])
        self.symtab.modify_symbol("strupr", "num_parameters", 1)

        # strcpy with a single argument
        self.symtab.insert_symbol("strcpy", -1)
        self.symtab.modify_symbol("strcpy", "identifier_type", "function")
        self.symtab.modify_symbol("strcpy", "data_type", ["char", "*"])
        self.symtab.modify_symbol("strcpy", "num_parameters", 2)

        # strcat with a single argument
        self.symtab.insert_symbol("strcat", -1)
        self.symtab.modify_symbol("strcat", "identifier_type", "function")
        self.symtab.modify_symbol("strcat", "data_type", ["char", "*"])
        self.symtab.modify_symbol("strcat", "num_parameters", 2)

        # strcmp with a single argument
        self.symtab.insert_symbol("strcmp", -1)
        self.symtab.modify_symbol("strcmp", "identifier_type", "function")
        self.symtab.modify_symbol("strcmp", "data_type", ["int"])
        self.symtab.modify_symbol("strcmp", "num_parameters", 2)

        self.symtab.insert_symbol("strrev", -1)
        self.symtab.modify_symbol("strrev", "identifier_type", "function")
        self.symtab.modify_symbol("strrev", "data_type", ["char", "*"])
        self.symtab.modify_symbol("strrev", "num_parameters", 1)

        # malloc with 1 arguments
        self.symtab.insert_symbol("malloc", -1)
        self.symtab.modify_symbol("malloc", "identifier_type", "function")
        self.symtab.modify_symbol("malloc", "data_type", ["void", "*"])
        self.symtab.modify_symbol("malloc", "num_parameters", 1)

        # calloc with 1 arguments
        self.symtab.insert_symbol("calloc", -1)
        self.symtab.modify_symbol("calloc", "identifier_type", "function")
        self.symtab.modify_symbol("calloc", "data_type", ["void", "*"])
        self.symtab.modify_symbol("calloc", "num_parameters", 2)

        # realloc with 1 arguments
        self.symtab.insert_symbol("realloc", -1)
        self.symtab.modify_symbol("realloc", "identifier_type", "function")
        self.symtab.modify_symbol("realloc", "data_type", ["void", "*"])
        self.symtab.modify_symbol("realloc", "num_parameters", 2)

        # free with 1 arguments
        self.symtab.insert_symbol("free", -1)
        self.symtab.modify_symbol("free", "identifier_type", "function")
        self.symtab.modify_symbol("free", "data_type", ["void"])
        self.symtab.modify_symbol("free", "num_parameters", 1)

    def printTree(self):
        self.ast_root.print_val()


def new_node(G=None, node_num=None, edge=None):
    global num_nodes
    num_nodes = num_nodes + 1
    graph.add_node(num_nodes - 1)
    node = graph.get_node(num_nodes - 1)
    return node


def remove_node(node, node_num=None):
    graph.remove_node(node)


aparser = argparse.ArgumentParser()
aparser.add_argument(
    "-d", "--debug", action="store_true", help="Parser Debug Mode", default=False
)
aparser.add_argument(
    "-o", "--out", help="Store output of parser in a file", default=None
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

fname = args.infile.split("/")[-1].split(".")[0]
ast = "dot/" + fname + ".dot"

if parser.error:
    print(
        bcolors.FAIL
        + "Error found. Aborting parsing of "
        + str(sys.argv[1])
        + "...."
        + bcolors.ENDC
    )
    sys.exit(0)
elif parser.symtab.error:
    print(bcolors.FAIL + "Error in semantic analysis." + bcolors.ENDC)
    sys.exit(0)
else:
    # print("Output Symbol Table CSV is at out/symtab/" + fname + ".csv")
    # print("Output AST is at dot/" + fname + ".dot")
    # print("Output TAC is at out/tac/" + fname + ".txt")

    symtab_csv = open("out/symtab/" + fname + ".csv", "w")
    graph.write(ast)
    orig_stdout = sys.stdout
    sys.stdout = symtab_csv
    parser.symtab.print_table()
    symtab_csv.close()
    tac = open("out/tac/" + fname + ".txt", "w")
    sys.stdout = tac
    parser.three_address_code.print_code()
    tac.close()
