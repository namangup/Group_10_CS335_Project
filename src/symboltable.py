from collections import OrderedDict
import copy, sys
import pandas as pd

ST = 0  # Symbol table branch
SN = 1  # Adding Struct Name
IS = 2  # Adding var inside a Struct


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[33m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class SymbolTable:
    def __init__(self):
        self.table_su = []
        self.top_scope_su = OrderedDict()
        self.table = []
        self.top_scope = OrderedDict()
        self.error = False
        self.offset = 0
        self.offset_list = []
        self.flag = ST

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

    def insert_symbol_su(self, id, tname, lno, path):
        if path == SN:
            present = self.top_scope_su.get(id, False)
            if not present:
                self.top_scope_su[id] = {}
                self.top_scope_su[id]["identifier_type"] = tname
                self.top_scope_su[id]["line"] = lno
                self.top_scope_su[id]["vars"] = dict()
                return True
            else:
                print(
                    bcolors.FAIL
                    + "Error: Redeclaration of existing data structure on "
                    + str(lno)
                    + ". Prior declaration at "
                    + str(present["line"])
                    + bcolors.ENDC
                )
                self.error = True
                return False
        else:
            temp = list(self.top_scope_su.items())
            if not temp:
                print(
                    bcolors.FAIL
                    + "No such data structure inside which this variable "
                    + str(id)
                    + " on line "
                    + str(lno)
                    + " can be inserted"
                    + bcolors.ENDC
                )
            else:
                name = temp[-1][0]
                if id not in self.top_scope_su[name]["vars"].keys():
                    self.top_scope_su[name]["vars"][id] = dict()
                    self.top_scope_su[name]["vars"][id]["line"] = lno
                    return True
                else:
                    print(
                        bcolors.FAIL
                        + "Error: Redeclaration of variable "
                        + str(id)
                        + " on line "
                        + str(lno)
                        + ". Prior declaration at line "
                        + str(self.top_scope_su[name]["vars"][id]["line"])
                        + bcolors.ENDC
                    )
                    self.error = True
                    return False

    def find_symbol_in_table_su(self, id, path):
        lvl = 1
        if path == SN:
            for elems in reversed(self.table_su):
                if elems is not None and elems.__contains__(id):
                    return abs(len(self.table_su) - lvl), elems.get(id)
                lvl = lvl + 1
        elif path == IS:
            for elems in reversed(self.table_su):
                if elems is not None and elems.__contains__(id):
                    return elems.get(id)
        return False

    def find_symbol_in_current_scope_su(self, id):
        return self.top_scope_su.get(id, False)

    def push_scope_su(self):
        self.table_su.append(self.top_scope_su)
        self.top_scope_su = OrderedDict()
        return

    def pop_scope_su(self):
        self.top_scope_su = self.table_su.pop()

    def modify_symbol_su(self, id, field, val, sline, path):
        if path == SN:
            present = self.find_symbol_in_current_scope_su(id)
            if present:
                self.top_scope_su[id][field] = val
                return True
            else:
                if sline:
                    print(
                        bcolors.FAIL
                        + "Error : Tried to modify field "
                        + str(field)
                        + " of the undeclared symbol "
                        + str(id)
                        + " on line "
                        + str(sline)
                        + bcolors.ENDC
                    )
                else:
                    print(
                        bcolors.FAIL
                        + "Error : Tried to modify field "
                        + str(field)
                        + " of the undeclared symbol "
                        + str(id)
                        + bcolors.ENDC
                    )
                self.error = True
                return False
        else:
            temp = list(self.top_scope_su.items())
            if not temp:
                print(
                    bcolors.FAIL
                    + "The variable "
                    + str(id)
                    + " on line "
                    + str(sline)
                    + " cannot be inserted into any data structure"
                    + bcolors.ENDC
                )
            else:
                name = temp[-1][0]
                if id in self.top_scope_su[name]["vars"].keys():
                    self.top_scope_su[name]["vars"][id][field] = val
                else:
                    print(
                        bcolors.FAIL
                        + "Error : Tried to modify undeclared variable "
                        + str(id)
                        + " in the data structure "
                        + str(name)
                        + " on line "
                        + str(sline)
                        + bcolors.ENDC
                    )
                    self.error = True
                    return False

    def return_type_tab_entry_su(self, id, tname, sline=None):
        present = self.find_symbol_in_current_scope_su(id)
        if not present:
            present = self.find_symbol_in_table_su(id, IS)

            if present:
                if tname == present["identifier_type"].lower():
                    return copy.deepcopy(present)
                else:
                    print(
                        bcolors.FAIL
                        + "Error: The data structure "
                        + str(tname)
                        + " "
                        + str(id)
                        + "+ on line "
                        + str(sline)
                        + " is not declared."
                        + bcolors.ENDC
                    )
                    self.error = True
                    return None

        else:
            if present["identifier_type"].lower() != tname:
                print(
                    bcolors.FAIL
                    + "Error : The data structure "
                    + str(tname)
                    + " "
                    + str(id)
                    + " on line {statement_line} is not declared."
                    + bcolors.ENDC
                )
                self.error = True
                return None
            else:
                return copy.deepcopy(present)

    def insert_symbol(self, id, lno, tname=None):
        if self.flag == ST:
            present, entry = self.find_symbol_in_current_scope(id)
            if not present:
                present = self.find_symbol_in_table(id, SN)
                if present:
                    print(
                        bcolors.WARNING
                        + "Warning: "
                        + str(id)
                        + ", on line"
                        + str(lno)
                        + ", is already declared at line"
                        + str(present[1]["line"])
                        + bcolors.ENDC
                    )
                self.top_scope[id] = OrderedDict()
                self.top_scope[id]["line"] = lno
            else:
                print(
                    bcolors.FAIL
                    + "Error: Redeclaration of existing variable "
                    + str(id)
                    + " at line number "
                    + str(lno)
                    + ". Prior declaration is at line "
                    + str(present["line"])
                    + bcolors.ENDC
                )
                self.error = True
        elif self.flag == SN:
            self.insert_symbol_su(id, tname, lno, self.flag)
        else:
            self.insert_symbol_su(id, None, lno, self.flag)

    def find_symbol_in_table(self, id, path):
        lvl = 1
        if path == SN:
            for tree in reversed(self.table):
                if tree is not None and tree.__contains__(id):
                    return abs(len(self.table) - lvl), tree.get(id)
                lvl += 1
        elif path == IS:
            for tree in reversed(self.table):
                if tree is not None and tree.__contains__(id):
                    return tree.get(id), tree[id]

        if path == 2:
            return False, []
        elif path == 1:
            return False

    def find_symbol_in_current_scope(self, id):
        present = self.top_scope.get(id, False)
        if present:
            return present, self.top_scope[id]
        else:
            return present, []

    def push_scope(self, three_address_code):
        self.offset_list.append(self.offset)
        self.offset = 0

        temporary_ptr = -20
        for item in self.top_scope.keys():
            if (
                item != "scope"
                and item != "struct_or_union"
                and item != "scope_num"
                and "temp" in self.top_scope[item].keys()
                and self.top_scope[item]["temp"][0] == "-"
            ):
                temporary_ptr = min(
                    temporary_ptr, int(self.top_scope[item]["temp"].split("(")[0])
                )
        self.lastScopeTemp = temporary_ptr

        if len(self.table) == 0:
            self.table.append(self.top_scope)
            TopScopeName = list(self.top_scope.items())[-1][0]
            if TopScopeName != "struct_or_union":
                self.top_scope = list(self.top_scope.items())[-1][1]
                if "scope" not in self.top_scope:
                    self.top_scope["scope"] = []
                parentScopeList = self.top_scope["scope"]
                parentScopeList.append(OrderedDict())
                self.top_scope = parentScopeList[-1]
        else:
            if "scope" not in self.top_scope:
                self.top_scope["scope"] = []

            parentScopeList = self.top_scope["scope"]
            self.table.append(self.top_scope)
            parentScopeList.append(OrderedDict())
            self.top_scope = parentScopeList[-1]

        self.push_scope_su()

        three_address_code.counter_scope += 1
        three_address_code.scope_list[three_address_code.counter_scope] = []
        self.top_scope["scope_num"] = three_address_code.counter_scope
        three_address_code.scope_list[self.top_scope["scope_num"]].append(
            three_address_code.next_statement
        )
        three_address_code.emit("PushScope", "", "", "")

        return

    def store_results(self, three_address_code):
        self.top_scope["struct_or_union"] = dict(self.top_scope_su)
        self.push_scope(three_address_code)
        three_address_code.code.pop()
        return

    #### make changes

    def pop_scope(self, three_address_code, flag=None):

        temp_of_lastScope = self.lastScopeTemp
        if self.top_scope:
            for i in self.top_scope.keys():
                if (
                    i != "scope"
                    and i != "struct_or_union"
                    and i != "scope_num"
                    and "temp" in self.top_scope[i].keys()
                    and self.top_scope[i]["temp"][0] == "-"
                ):
                    # print("Start")
                    # print(temp_of_lastScope)
                    # print(self.top_scope[i]["temp"])
                    temp_of_lastScope = min(
                        temp_of_lastScope, int(self.top_scope[i]["temp"].split("(")[0])
                    )
                    # print("Start 2")
                    # print(temp_of_lastScope)
                    # print(self.top_scope[i]["temp"])

            for lines in three_address_code.scope_list[self.top_scope["scope_num"]]:
                three_address_code.code[lines] = [
                    "UNARY&",
                    "%esp",
                    f"{temp_of_lastScope}(%ebp)",
                    "",
                ]

            if len(self.table) > 1 and flag is None:
                prev_scope_num = self.table[-1]["scope_num"]
                three_address_code.scope_list[prev_scope_num].append(
                    three_address_code.next_statement
                )
                three_address_code.emit("PushScope", "", "", "")

        self.top_scope["struct_or_union"] = dict(self.top_scope_su)
        self.pop_scope_su()
        TScope = self.top_scope
        self.offset = self.offset_list[-1]
        self.offset_list.pop()

        if len(self.table) > 0:
            self.top_scope = self.table.pop()
        else:
            self.top_scope = None
        return TScope

    def del_struct_or_union(self, temp):
        list_copy = []
        for item in temp["scope"]:
            item.pop("struct_or_union", None)
            if "scope" in item:
                self.del_struct_or_union(item)
            if not item:
                continue
            list_copy.append(item)
        if len(list_copy) == 0:
            temp.pop("scope", None)
        else:
            temp["scope"] = list_copy

    def scope_rows(self, fname, val, ver):
        data_rows = []
        for scope_ctr, scope in enumerate(val):
            for k, v in scope.items():
                if k == "scope":
                    data_rows += self.scope_rows(
                        fname, v, ver + str(scope_ctr + 1) + "."
                    )
                elif k != "scope_num":

                    if "vars" in v.keys():
                        for varname, stvars in v["vars"].items():
                            cur_row = [varname, fname, "", "", "", "", "", "", "", ""]
                            cur_row[8] = k
                            for key2, value2 in stvars.items():
                                if key2 == "line":
                                    cur_row[2] = value2
                                elif key2 == "identifier_type":
                                    cur_row[3] = value2
                                elif key2 == "data_type":
                                    str1 = ""
                                    if value2[-1] == "*":
                                        for i in range(len(value2) - 2):
                                            str1 += value2[i]
                                        cur_row[4] = (
                                            str(value2[-2])
                                            + " "
                                            + str(value2[-1])
                                            + " "
                                            + str1
                                        ).strip()
                                    else:
                                        for i in range(len(value2) - 1):
                                            str1 += value2[i]
                                        cur_row[4] = (
                                            str(value2[-1]) + " " + str1
                                        ).strip()
                                elif key2 == "allocated_size":
                                    cur_row[6] = value2
                                elif key2 == "offset":
                                    cur_row[7] = value2
                                cur_row[9] = ver + str(scope_ctr + 1)
                            data_rows.append(cur_row)

                    cur_row = [k, fname, "", "", "", "", "", "", "", ""]
                    for key2, value2 in v.items():
                        if key2 == "line":
                            cur_row[2] = value2
                        elif key2 == "identifier_type":
                            cur_row[3] = value2
                        elif key2 == "data_type":
                            str1 = ""
                            if value2[-1] == "*":
                                for i in range(len(value2) - 2):
                                    str1 += value2[i]
                                cur_row[4] = (
                                    str(value2[-2]) + " " + str(value2[-1]) + " " + str1
                                ).strip()
                            else:
                                for i in range(len(value2) - 1):
                                    str1 += value2[i]
                                cur_row[4] = (str(value2[-1]) + " " + str1).strip()
                        elif key2 == "allocated_size":
                            cur_row[6] = value2
                        elif key2 == "offset":
                            cur_row[7] = value2
                        cur_row[9] = ver + str(scope_ctr + 1)
                    data_rows.append(cur_row)

        return data_rows

    def print_table(self):
        col = [
            "Identifier",
            "Local/Global        ",
            "Line Number",
            "Identifier Type",
            "Data Type",
            "Parameter Count",
            "Allocated Size",
            "Offset",
            "Struct/Union",
            "Scope",
        ]
        #     0              1                   2          3         4      5                   6                      7          8                9
        data_rows = []

        for key, value in self.table[0].items():
            cur_row = [key, "Global", "", "", "", "", "", "", "", ""]
            if key != "struct_or_union" and key != "scope_num":
                for key2, value2 in value.items():
                    if key2 == "line":
                        cur_row[2] = value2
                    elif key2 == "identifier_type":
                        cur_row[3] = value2
                    elif key2 == "data_type":
                        str1 = ""
                        if value2[-1] == "*":
                            for i in range(len(value2) - 2):
                                str1 += value2[i]
                            cur_row[4] = (
                                str(value2[-2]) + " " + str(value2[-1]) + " " + str1
                            ).strip()
                        else:
                            for i in range(len(value2) - 1):
                                str1 += value2[i]
                            cur_row[4] = (str(value2[-1]) + " " + str1).strip()
                    elif key2 == "num_parameters":
                        cur_row[5] = value2
                data_rows.append(cur_row)

        # (print)(self.table[0].items())
        for key, value in self.table[0].items():
            if key != "scope_num" and "scope" in value:
                tmp = copy.deepcopy(value["scope"][0])
                # print(tmp)
                del tmp["struct_or_union"]
                if "scope" in tmp:
                    self.del_struct_or_union(tmp)

                if len(tmp) > 0:
                    # print(tmp)
                    for k, v in tmp.items():
                        if k == "scope":
                            data_rows += self.scope_rows(key, v, "")
                        elif k != "scope_num":

                            if "vars" in v.keys():
                                for varname, stvars in v["vars"].items():
                                    cur_row = [
                                        varname,
                                        key,
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                    ]
                                    cur_row[8] = k
                                    for key2, value2 in stvars.items():
                                        if key2 == "line":
                                            cur_row[2] = value2
                                        elif key2 == "identifier_type":
                                            cur_row[3] = value2
                                        elif key2 == "data_type":
                                            str1 = ""
                                            if value2[-1] == "*":
                                                for i in range(len(value2) - 2):
                                                    str1 += value2[i]
                                                cur_row[4] = (
                                                    str(value2[-2])
                                                    + " "
                                                    + str(value2[-1])
                                                    + " "
                                                    + str1
                                                ).strip()
                                            else:
                                                for i in range(len(value2) - 1):
                                                    str1 += value2[i]
                                                cur_row[4] = (
                                                    str(value2[-1]) + " " + str1
                                                ).strip()
                                        elif key2 == "allocated_size":
                                            cur_row[6] = value2
                                        elif key2 == "offset":
                                            cur_row[7] = value2
                                    data_rows.append(cur_row)

                            cur_row = [k, key, "", "", "", "", "", "", "", ""]
                            for key2, value2 in v.items():
                                if key2 == "line":
                                    cur_row[2] = value2
                                elif key2 == "identifier_type":
                                    cur_row[3] = value2
                                elif key2 == "data_type":
                                    str1 = ""
                                    if value2[-1] == "*":
                                        for i in range(len(value2) - 2):
                                            str1 += value2[i]
                                        cur_row[4] = (
                                            str(value2[-2])
                                            + " "
                                            + str(value2[-1])
                                            + " "
                                            + str1
                                        ).strip()
                                    else:
                                        for i in range(len(value2) - 1):
                                            str1 += value2[i]
                                        cur_row[4] = (
                                            str(value2[-1]) + " " + str1
                                        ).strip()
                                elif key2 == "allocated_size":
                                    cur_row[6] = value2
                                elif key2 == "offset":
                                    cur_row[7] = value2
                            data_rows.append(cur_row)

        data_rows = [col] + data_rows
        df = pd.DataFrame(data_rows)
        print(df.to_string(index=False, header=False))

    def modify_symbol(self, id, field, val, sline=None):
        if self.flag == ST:
            present, tmp = self.find_symbol_in_current_scope(id)
            if not present:

                present, tmp = self.find_symbol_in_table(id, IS)
                if present:
                    present[field] = val

                    if field == "vars":
                        if 0 < len(self.table):
                            curOffset = 0
                            for term in self.top_scope[id][field]:
                                self.top_scope[id][field][term]["offset"] = curOffset
                                curOffset = (
                                    curOffset
                                    + self.top_scope[id][field][term]["allocated_size"]
                                )

                    elif field == "allocated_size":
                        if 0 < len(self.table):
                            self.top_scope[id]["offset"] = self.offset
                            self.offset = val + self.offset

                    return True

                else:
                    if sline:
                        print(
                            bcolors.FAIL
                            + "Error : Tried to modify the "
                            + str(field)
                            + " of the undeclared symbol "
                            + str(id)
                            + " on line "
                            + str(sline)
                            + bcolors.ENDC
                        )
                    else:
                        print(
                            bcolors.FAIL
                            + "Error : Tried to modify the "
                            + str(field)
                            + " of the undeclared symbol "
                            + str(id)
                            + bcolors.ENDC
                        )
                    self.error = True
                    return False

            else:

                self.top_scope[id][field] = val
                if field == "vars":
                    if 0 < len(self.table):
                        curOffset = 0
                        for term in self.top_scope[id][field]:
                            self.top_scope[id][field][term]["offset"] = curOffset
                            curOffset = (
                                self.top_scope[id][field][term]["allocated_size"]
                                + curOffset
                            )
                elif field == "allocated_size":
                    if 0 < len(self.table):
                        self.top_scope[id]["offset"] = self.offset
                        self.offset = self.offset + val

                return True
        else:
            self.modify_symbol_su(id, field, val, sline, self.flag)

    def return_sym_tab_entry(self, id, sline=None):
        present, entry = self.find_symbol_in_current_scope(id)
        if present:
            return present, entry
        else:
            present, entry = self.find_symbol_in_table(id, 2)
            if present:
                return present, entry
            else:
                print(
                    bcolors.FAIL
                    + "Error : The variable "
                    + str(id)
                    + " on line "
                    + str(sline)
                    + " is not declared."
                    + bcolors.ENDC
                )
                self.error = True
                return None, None

    def is_global(self, id=None):
        if len(self.table) == 0:
            return True
        else:
            return False
