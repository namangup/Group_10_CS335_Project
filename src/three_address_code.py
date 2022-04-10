import copy


class three_address_code:
    def __init__(self):
        self.code = []
        self.counter_temp = 0
        self.counter_label = 0
        self.next_statement = 0
        self.string_list = []
        self.float_values = []
        self.scope_list = {}
        self.counter_scope = 0
        self.global_variables = []

    def create_label(self):
        self.counter_label += 1
        label_name = "label_" + str(self.counter_label)

    def create_temp_var(self):
        self.counter_temp += 1
        temp_name = "temp_var_" + str(self.counter_temp)
        return temp_name

    def backpatch(self, p_list, lno):
        for i in p_list:
            if "goto" in self.code[i][0].split():
                self.code[i][1] = lno + 1

    def emit(self, operator, destination, operand_1=None, operand_2=None):
        if (operand_1 is None) and (operand_2 is None):
            self.code.append([operator, destination])
        elif operand_2 is None:
            self.code.append([operator, destination, operand_1])
        else:
            self.code.append([operator, destination, operand_1, operand_2])
        self.next_statement += 1

    def find_symbol_in_symtab(self, symtab, identifier):
        if identifier is None:
            return None
        else:
            found, entry = symtab.return_sym_tab_entry(identifier)
            if "temp" in found.keys():
                return found["temp"]
            else:
                new_temp = self.create_temp_var()
                symtab.modify_symbol(identifier, "temp", new_temp)
                return new_temp

    def print_code(self):
        temp_code = copy.deepcopy(self.code)
        lines_dict = dict()
        self.code = []
        deleted = 0
        for i in range(0, len(temp_code)):
            code = temp_code[i]
            lines_dict[i + 1] = i + 1 - deleted
            if "goto" in code[0].split():
                if code[1] == "" or code[1] == None:
                    deleted += 1
                else:
                    self.code.append(code)
            elif "retq" in code[0].split() and (
                "retq" in temp_code[i - 1][0].split()
                or "retq_struct" in temp_code[i - 1][0].split()
            ):
                deleted += 1
            else:
                self.code.append(code)

        for i in range(0, len(self.code)):
            code = self.code[i]
            if "goto" in code[0].split():
                self.code[i][1] = lines_dict[self.code[i][1]]

        for i in range(0, len(self.code)):
            code = self.code[i]
            if (
                i != 0
                and len(code[0]) > 0
                and code[0][0] != "."
                and code[0][-1] == ":"
                and "." not in code[0]
            ):
                for j in reversed(range(i)):
                    prev_code = self.code[j]
                    if len(prev_code[0]) <= 0:
                        break
                    elif prev_code[0] == "UNARY&":
                        self.code[j] = code
                        self.code[j + 1] = prev_code
                        break
                    else:
                        self.code[j] = code
                        self.code[j + 1] = prev_code
        for i in range(0, len(self.code)):
            code = self.code[i]
            for i in range(0, len(code)):
                print(code[i], end=" ")
            print("")

    def add_strings(self):
        for i in range(0, len(self.string_list)):
            self.emit(f".LC{i}:", "", "", "")
            self.emit(".string", self.string_list[i])
        for i in range(0, len(self.float_values)):
            self.emit(f".LF{i}:", "", "", "")
            self.emit(".long", self.float_values[i])
        self.add_global()

    def add_global(self):
        for val in self.global_variables:
            self.emit(f".comm", "", str(val[0]) + "," + str(val[1]), "")
        self.emit(".data", "", "", "")
