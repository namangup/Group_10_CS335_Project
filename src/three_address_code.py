import copy


class three_address_code:
    def __init__(self):
        self.code = []
        self.float_values = []
        self.string_list = []
        self.global_variables = []
        self.static_variables = []
        self.scope_list = {}
        self.counter_temp = 0
        self.counter_label = 0
        self.counter_static = 1
        self.next_statement = 0
        self.counter_scope = 0

    def create_label(self):
        self.counter_label = self.counter_label + 1
        label_name = "label_" + str(self.counter_label)

    def create_temp_var(self):
        self.counter_temp += 1
        temp_name = "$temp_var_" + str(self.counter_temp)
        return temp_name

    def backpatch(self, p_list, lno):
        updated_lno = lno + 1
        for i in p_list:
            compare_str = "goto"
            to_check_list = self.code[i][0].split()
            if compare_str in to_check_list:
                self.code[i][1] = updated_lno

    def emit(self, operator, destination, operand_1=None, operand_2=None):
        if (operand_1 is None) and (operand_2 is None):
            self.code.append([operator, destination])
        elif operand_2 is None:
            self.code.append([operator, destination, operand_1])
        else:
            self.code.append([operator, destination, operand_1, operand_2])
        self.next_statement = self.next_statement + 1

    def find_symbol_in_symtab(self, symtab, identifier):
        if identifier is not None:
            found, entry = symtab.return_sym_tab_entry(identifier)
            compare_str = "temp"
            to_check_list = found.keys()
            if compare_str in to_check_list:
                return found["temp"]
            else:
                new_temp = self.create_temp_var()
                symtab.modify_symbol(identifier, compare_str, new_temp) 
                return new_temp
        return None 

    def print_code(self):

        for i in range(0, len(self.string_list)):
            self.emit(f".LC{i}:", "", "", "")
            self.emit(".string", self.string_list[i])
        for i in range(0, len(self.float_values)):
            self.emit(f".LF{i}:", "", "", "")
            self.emit(".long", self.float_values[i])
        for val in self.global_variables:
            self.emit(f".comm", "", str(val[0]) + "," + str(val[1]), "")
        self.emit(".data", "", "", "")

        deleted = 0 
        lines_dict = dict()
        temp_code = copy.deepcopy(self.code)
        check_ran = range(0, len(temp_code)) 
        self.code = []
        for i in check_ran:
            code = temp_code[i]
            lines_dict[i + 1] = i - deleted + 1
            compare_str = "goto" 
            compare_str_2 = "retq"
            to_check_list = code[0].split()
            to_check_list_2 = temp_code[i - 1][0].split()
            if compare_str in to_check_list:
                if code[1] == "" or code[1] == None:
                    deleted = deleted + 1
                else:
                    self.code.append(code)
            elif compare_str_2 in to_check_list and (
                compare_str_2 in to_check_list_2 or "retq_struct" in to_check_list_2
            ):
                deleted = deleted + 1
            else:
                self.code.append(code)
        check_ran = range(0, len(self.code))
        for i in check_ran:
            code = self.code[i]
            compare_str = "goto"
            if compare_str in code[0].split(): 
                spec_elem = self.code[i][1]
                self.code[i][1] = lines_dict[spec_elem]
        check_ran = range(0, len(self.code))
        for i in check_ran:
            code = self.code[i]
            code_lvl = code[0]
            if len(code_lvl) > 0:
                el0 = code_lvl[0]
                el1 = code_lvl[-1]
            if (
                i != 0
                and len(code_lvl) > 0
                and el0 != "."
                and el1 == ":"
                and "." not in code_lvl
            ):
                check_ran = reversed(range(i))
                for j in check_ran:
                    prev_code = self.code[j]
                    check_code = "UNARY&"
                    if len(prev_code[0]) <= 0:
                        break
                    elif prev_code[0] == check_code:
                        self.code[j + 1] = prev_code 
                        self.code[j] = code
                        break
                    else:
                        self.code[j + 1] = prev_code
                        self.code[j] = code
        check_ran = range(0, len(self.code))
        for i in check_ran:
            print(i + 1, end=" ")
            code = self.code[i]
            check_ran2 = range(0, len(code))
            for j in check_ran2:
                print(code[j], end=" ")
            print("")
