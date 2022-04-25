import copy, sys

math_func_list = [
    "scanf",
    "printf",
    "sqrt",
    "ceil",
    "floor",
    "pow",
    "fabs",
    "log",
    "log10",
    "fmod",
    "exp",
    "cos",
    "sin",
    "acos",
    "asin",
    "tan",
    "atan",
]


class CodeGenerator:
    def __init__(self):
        self.register_list = ["%ebx", "%eax", "%ecx", "%esi", "%edi", "%edx"]
        self.eight_bit_register = {
            "%eax": "%al",
            "%ebx": "%bl",
            "%ecx": "%cl",
            "%edx": "%dl",
        }
        check_ran = range(len(self.register_list))
        self.register_stack = [i for i in check_ran]
        iter_list = [(self.register_list[i], i) for i in self.register_stack]
        self.reverse_mapping = dict(iter_list)
        iter_list = [(i, self.register_list[i]) for i in self.register_stack]
        self.register_mapping = dict(iter_list)

        self.label_list = {}
        self.label_num = 1

        self.final_code = []
        append_list = [".data", ".text", ".globl main", ".type main, @function", "\n"]
        for i in range(len(append_list)):
            self.final_code.append(append_list[i])

    def emit_code(self, s1="", s2="", s3=""):
        temp_code = s1
        if s3 != "":
            if isinstance(s3, int):
                s3 = self.register_mapping[s3]
        if s2 != "":
            if isinstance(s2, int):
                s2 = self.register_mapping[s2]
        len_chk = len(s2)
        if len_chk > 0:
            temp_code = temp_code + " " + s2
            len_chk_3 = len(s3)
            if len_chk_3 > 0:
                temp_code = temp_code + ", " + s3
        self.final_code.append(temp_code)

    def request_register(self, reg=None, instr=None):
        if not self.register_stack:
            return None
        elif reg is not None:
            if self.reverse_mapping[reg] not in self.register_stack:
                register_index = self.reverse_mapping[reg]
                swap_register_index = self.request_register()
                if swap_register_index is not None:
                    emit_instruction = "movl"
                    swap_reg = self.register_mapping[swap_register_index]
                    tmp = self.reverse_mapping[swap_reg]
                    self.reverse_mapping[swap_reg] = self.reverse_mapping[reg]
                    self.reverse_mapping[reg] = tmp
                    tmp = self.register_mapping[swap_register_index]
                    self.register_mapping[swap_register_index] = self.register_mapping[
                        register_index
                    ]
                    self.register_mapping[register_index] = tmp
                    ret_val = self.reverse_mapping[reg]
                    self.emit_code(emit_instruction, reg, swap_reg)
                    return ret_val
            else:
                self.register_stack.remove(self.reverse_mapping[reg])
                return self.reverse_mapping[reg]
            return None
        else:
            return self.register_stack.pop()

    def move_variable(self, source, destination):
        emit_instruction = "movl"
        if destination != source:
            self.emit_code(emit_instruction, source, destination)
        return

    def free_register(self, register_index, start=None):
        if register_index == None:
            return
        else:
            check_inst = isinstance(register_index, int)
            check_ran = self.register_list
            off = 0
            if check_inst:
                register = self.register_mapping[register_index]
            else:
                register = register_index
            if register not in check_ran:
                return
            if not check_inst:
                register_index = self.reverse_mapping[register_index]
            if register_index in self.register_stack:
                return
            if start is None:
                self.register_stack.append(register_index)
            else:
                self.register_stack.insert(off, register_index)

    def check_type(
        self,
        instruction,
        request_register1=None,
        request_register2=None,
        eight_bit1=False,
        eight_bit2=False,
        one_byte=None,
    ):
        source1 = instruction[2]
        source2 = ""
        req_rg = "%edx"

        if not eight_bit1:
            reg1_idx = self.request_register(request_register1)
        else:
            reg1_idx = self.request_register(req_rg)

        if reg1_idx is None:
            return False

        reg2_idx = None
        check_list = ["%", "("]
        if source1[0] == check_list[0] and len(source1) > 4:
            pos = source1[4:]
            emit_instruction = "leal"
            offset = int(pos)
            if reg1_idx is not None:
                self.emit_code(emit_instruction, f"{offset}(%ebp)", reg1_idx)
        elif source1[0] == check_list[1]:
            pos = source1[1:-1]
            self.move_variable(pos, reg1_idx)
            emit_instruction = "movzbl"
            emit_instruction_2 = "movl"
            if reg1_idx is not None and one_byte is not None:
                self.emit_code(
                    emit_instruction, f"({self.register_mapping[reg1_idx]})", reg1_idx
                )
            else:
                self.emit_code(
                    emit_instruction_2, f"({self.register_mapping[reg1_idx]})", reg1_idx
                )
        else:
            emit_instruction = "movzbl"
            if one_byte is None:
                self.move_variable(source1, reg1_idx)
            else:
                self.emit_code(emit_instruction, source1, reg1_idx)

        instruction[2] = reg1_idx
        instruction_length = len(instruction)
        if instruction_length >= 4:
            req_rg = "%ebx"
            source2 = instruction[3]
            if eight_bit2 is False:
                reg2_idx = self.request_register(request_register2)
            else:
                reg2_idx = self.request_register(req_rg)

            if reg2_idx is None:
                return False

            if source2[0] == "(":
                emit_instruction = "movzbl"
                self.move_variable(source2[1:-1], reg2_idx)
                emit_instruction_2 = "movl"
                reg_mpd = self.register_mapping[reg2_idx]
                if one_byte is not None and reg2_idx is not None:
                    self.emit_code(emit_instruction, f"({reg_mpd})", reg2_idx)
                else:
                    self.emit_code(emit_instruction_2, f"({reg_mpd})", reg2_idx)
            else:
                emit_instruction = "movzbl"
                if one_byte is not None and reg2_idx is not None:
                    self.emit_code(emit_instruction, source2, reg2_idx)
                else:
                    self.move_variable(source2, reg2_idx)

            instruction[3] = reg2_idx

        return True

    def create_label(self, line):
        if int(line) in self.label_list:
            return self.label_list[int(line)]
        label = f".L{self.label_num}"
        self.label_list[int(line)] = label
        self.label_num = self.label_num + 1
        return label

    def dereference(self, destination, one_byte=None, reg=None):
        check_char = ["(", "%"]
        destination_length = len(destination)
        if destination[0] == check_char[0]:
            emit_instruction = "movl"
            destination = destination[1:-1]
            register = self.request_register(reg)
            self.emit_code(emit_instruction, destination, register)
            register = self.register_mapping[register]
            string_ret = "(" + str(register) + ")"
            return string_ret
        elif destination[0] == check_char[1] and destination_length > 4:
            first = destination[0:4]
            second = destination[4:]
            new_destination = f"{int(second)}({first})"
            emit_instruction = "leal"
            register = self.request_register(reg)
            self.emit_code(emit_instruction, new_destination, register)
            register = self.register_mapping[register]
            return str(register)
        else:
            return destination

    def float_dereference(self, instruction, rege1=None, rege2=None, rege3=None):
        flag1 = 0
        flag2 = flag1
        reg1 = instruction[1]
        flag3 = flag2
        if instruction[1][0] == "(":
            emit_instruction = "movl"
            ins_rng = instruction[1][1:-1]
            reg1 = self.request_register(rege1)
            self.emit_code(emit_instruction, ins_rng, reg1)
            reg1 = self.register_mapping[reg1]
            if flag1 != 1:
                flag1 = 1
            reg1 = "(" + str(reg1) + ")"

        instruc_len = len(instruction)
        reg2 = None
        if instruc_len > 2:
            reg2 = instruction[2]
        if instruc_len > 2 and instruction[2][0] == "(":
            emit_instruction = "movl"
            ins_rng = instruction[2][1:-1]
            reg2 = self.request_register(rege2)
            self.emit_code(emit_instruction, ins_rng, reg2)
            reg2 = self.register_mapping[reg2]
            if flag2 != 1:
                flag2 = 1
            reg2 = "(" + str(reg2) + ")"

        reg3 = None
        if instruc_len > 3:
            reg3 = instruction[3]
        if instruc_len > 3 and instruction[3][0] == "(":
            emit_instruction = "movl"
            ins_rng = instruction[3][1:-1]
            reg3 = self.request_register(rege3)
            self.emit_code(emit_instruction, ins_rng, reg3)
            reg3 = self.register_mapping[reg3]
            if flag3 != 1:
                flag3 = 1
            reg3 = "(" + str(reg3) + ")"
        if flag1 == 1:
            self.free_register(reg1[1:-1])
        if flag2 == 1:
            self.free_register(reg2[1:-1])
        if flag3 == 1:
            self.free_register(reg3[1:-1])

        return reg1, reg2, reg3

    def op_addition(self, instruction):
        """
        This function is currently only implemented
        for integer addition and float
        """
        check = instruction[0][2:]
        type_chk = ["char", "float"]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%edx", "%eax", False, False, True)
            emit_instruction1 = "addl"
            emit_instruction2 = "movb"
            instruction[1] = self.dereference(instruction[1])
            self.emit_code(emit_instruction1, instruction[3], instruction[2])
            self.emit_code(emit_instruction2, "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            char_ins0 = instruction[1][0]
            char_ins1 = instruction[1][1]
            if char_ins0 == "%":
                self.free_register(instruction[1])
            elif char_ins0 == "(" and char_ins1 == "%":
                self.free_register(instruction[1][1:-1])

        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = "flds"
            emit_instruction2 = "fadds"
            emit_instruction3 = "fstps"
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code(emit_instruction1, reg2)
            self.emit_code(emit_instruction2, reg3)
            self.emit_code(emit_instruction3, reg1)

        else:
            self.check_type(instruction)
            emit_instruction1 = "addl"
            emit_instruction2 = "movl"
            instruction[1] = self.dereference(instruction[1])
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            if (
                instruction[1] is not None
                and instruction[1][0] is not None
                and instruction[1][0] == "("
                and instruction[1][1] is not None
                and instruction[1][1] == "%"
            ):
                self.free_register(instruction[1][1:-1])
            elif (
                instruction[1] is not None
                and instruction[1][0] is not None
                and instruction[1][0] == "%"
            ):
                self.free_register(instruction[1])

    def op_subtraction(self, instruction):
        """
        This function is currently only implemented
        for integer and float
        """
        check = instruction[0][2:]
        type_chk = ["char", "float"]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%edx", "%eax", False, False, True)
            emit_instruction1 = "subl"
            emit_instruction2 = "movb"
            instruction[1] = self.dereference(instruction[1])
            self.emit_code(emit_instruction1, instruction[3], instruction[2])
            self.emit_code(emit_instruction2, "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            char_ins0 = instruction[1][0]
            char_ins1 = instruction[1][1]
            if char_ins0 == "%":
                self.free_register(instruction[1])
            elif char_ins0 == "(" and char_ins1 == "%":
                self.free_register(instruction[1][1:-1])

        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = "flds"
            emit_instruction2 = "fsubs"
            emit_instruction3 = "fstps"
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code(emit_instruction1, reg2)
            self.emit_code(emit_instruction2, reg3)
            self.emit_code(emit_instruction3, reg1)
        else:
            self.check_type(instruction)
            emit_instruction1 = "subl"
            emit_instruction2 = "movl"
            instruction[1] = self.dereference(instruction[1])
            self.emit_code(emit_instruction1, instruction[3], instruction[2])
            self.emit_code(emit_instruction2, instruction[2], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            if (
                instruction[1] is not None
                and instruction[1][0] is not None
                and instruction[1][0] == "("
            ):
                self.free_register(instruction[1])
                instruction_sliced = instruction[1][1:-1]
                instruction[1] = instruction_sliced

    def op_eq(self, instruction):
        """
        This function is currently only implemented
        for integer and float
        """
        check = instruction[0][2:]
        type_chk = ["char", "float"]
        if type_chk[0] == instruction[0][2:]:
            if instruction[2] and instruction[2][0] == "$":
                emit_instruction1 = "movb"
                instruction[1] = self.dereference(instruction[1])
                self.emit_code(emit_instruction1, instruction[2], instruction[1])
                char_ins0 = instruction[1][0]
                char_ins1 = instruction[1][1]
                if char_ins0 == "%":
                    self.free_register(instruction[1])
                elif char_ins0 == "(" and char_ins1 == "%":
                    self.free_register(instruction[1][1:-1])
            else:
                req_reg = "%eax"
                deref_reg = ["%edx", "%ecx"]
                for i in range(2):
                    instruction[i] = self.dereference(
                        instruction[i], None, deref_reg[i]
                    )
                reg = self.request_register(req_reg)
                emit_instruction1 = "movzbl"
                emit_instruction2 = "movb"
                self.emit_code(emit_instruction1, instruction[2], req_reg)
                self.emit_code(emit_instruction2, "%al", instruction[1])
                self.free_register(req_reg)
                char_ins0 = instruction[1][0]
                char_ins1 = instruction[1][1]
                if char_ins0 == "%":
                    self.free_register(instruction[1])
                elif char_ins0 == "(" and char_ins1 == "%":
                    self.free_register(instruction[1][1:-1])

                char_ins0 = instruction[2][0]
                char_ins1 = instruction[2][1]
                if char_ins0 == "%":
                    self.free_register(instruction[2])
                elif char_ins0 == "(" and char_ins1 == "%":
                    self.free_register(instruction[2][1:-1])

        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = "flds"
            emit_instruction2 = "fadds"
            emit_instruction3 = "fstps"
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code(emit_instruction1, reg2)
            self.emit_code(emit_instruction3, reg1)

        else:
            self.check_type(instruction)
            emit_instruction2 = "movl"
            instruction[1] = self.dereference(instruction[1])
            self.emit_code(emit_instruction2, instruction[2], instruction[1])
            self.free_register(instruction[2])
            if (
                instruction[1] is not None
                and instruction[1][0] is not None
                and instruction[1][0] == "("
            ):
                self.free_register(instruction[1])
                instruction_sliced = instruction[1][1:-1]
                instruction[1] = instruction_sliced

    def op_multiplication(self, instruction):

        check = instruction[0][2:]
        type_chk = ["char", "float", "int"]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%eax", "%edx", False, False, True)
            emit_instruction1 = "imull"
            emit_instruction2 = "movb"
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = "flds"
            emit_instruction2 = "fmuls"
            emit_instruction3 = "fstps"
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code(emit_instruction1, reg2)
            self.emit_code(emit_instruction2, reg3)
            self.emit_code(emit_instruction3, reg1)

        elif type_chk[2] == instruction[0][2:]:
            self.check_type(instruction)
            emit_instruction1 = "imull"
            emit_instruction2 = "movl"
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        else:
            self.check_type(instruction)
            emit_instruction1 = "imull"
            emit_instruction2 = "movl"
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

    def op_division(self, instruction):
        check = instruction[0][2:]
        type_chk = ["char", "float", "int"]
        if type_chk[0] == instruction[0][2:]:
            edx = self.request_register("%edx")
            eax = self.request_register("%eax")
            if not edx:
                return
            if not eax:
                return
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movb"
            tg1 = "%edx"
            tg2 = "%eax"
            self.check_type(instruction, "%ecx", "%ebx", False, False, True)
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            self.emit_code(emit_instruction4, "%al", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            self.free_register(tg1, True)
            self.free_register(tg2, True)

        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = "flds"
            emit_instruction2 = "fdivs"
            emit_instruction3 = "fstps"
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code(emit_instruction1, reg2)
            self.emit_code(emit_instruction2, reg3)
            self.emit_code(emit_instruction3, reg1)

        elif type_chk[2] == instruction[0][2:]:
            edx = self.request_register("%edx")
            eax = self.request_register("%eax")
            if not edx:
                return
            if not eax:
                return
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movl"
            tg1 = "%edx"
            tg2 = "%eax"
            self.check_type(instruction)
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            self.emit_code(emit_instruction4, "%eax", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            self.free_register(tg1, True)
            self.free_register(tg2, True)
        else:
            edx = self.request_register("%edx")
            eax = self.request_register("%eax")
            if not edx:
                return
            if not eax:
                return
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movl"
            tg1 = "%edx"
            tg2 = "%eax"
            self.check_type(instruction)
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            self.emit_code(emit_instruction4, "%eax", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
            self.free_register(tg1, True)
            self.free_register(tg2, True)

    def op_modulo(self, instruction):

        edx = self.request_register("%edx")
        eax = self.request_register("%eax")
        type_chk = ["char", "int"]
        if not edx:
            return
        if not eax:
            return
        tg1 = "%edx"
        tg2 = "%eax"
        check = instruction[0][2:]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%ebx", "%ecx", False, False, True)
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movb"
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            self.emit_code(emit_instruction4, "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

        elif type_chk[1] == instruction[0][2:]:
            self.check_type(instruction)
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movl"
            emit_instruction1_reg = "%eax"
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            emit_instruction4_reg = "%edx"
            self.emit_code(emit_instruction4, emit_instruction4_reg, instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

        else:
            self.check_type(instruction)
            emit_instruction1 = "movl"
            emit_instruction2 = "cltd"
            emit_instruction3 = "idivl"
            emit_instruction4 = "movl"
            self.emit_code(emit_instruction1, instruction[2], "%eax")
            self.emit_code(emit_instruction2)
            self.emit_code(emit_instruction3, instruction[3])
            self.emit_code(emit_instruction4, "%edx", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        self.free_register(tg1)
        self.free_register(tg2)

    def op_and(self, instruction):
        check = instruction[0][2:]
        type_chk = ["char", "int"]
        emit_inst = ["andl", "movb", "movl"]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%eax", "%edx", False, False, True)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[1], "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        elif type_chk[1] == instruction[0][2:]:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[2], instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        else:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[2], instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

    def op_inclusive_or(self, instruction):
        check = instruction[0][2:]
        type_chk = ["char", "int"]
        emit_inst = ["orl", "movb", "movl"]
        if type_chk[0] == instruction[0][2:]:
            emit_instruction1 = emit_inst[0]
            emit_instruction2 = emit_inst[1]
            self.check_type(instruction, "%eax", "%edx", False, False, True)
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        elif type_chk[1] == instruction[0][2:]:
            emit_instruction1 = emit_inst[0]
            emit_instruction2 = emit_inst[2]
            self.check_type(instruction)
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        else:
            emit_instruction1 = emit_inst[0]
            emit_instruction2 = emit_inst[2]
            self.check_type(instruction)
            self.emit_code(emit_instruction1, instruction[2], instruction[3])
            self.emit_code(emit_instruction2, instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

    def op_exclusive_or(self, instruction):

        check = instruction[0][2:]
        type_chk = ["char", "int"]
        emit_inst = ["xorl", "movb", "movl"]
        if type_chk[0] == instruction[0][2:]:
            self.check_type(instruction, "%eax", "%edx", False, False, True)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[1], "%dl", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

        elif type_chk[1] == instruction[0][2:]:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[2], instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])
        else:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2], instruction[3])
            self.emit_code(emit_inst[2], instruction[3], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3])

    def op_shift_left(self, instruction):
        """
        This function is currently only implemented
        for integer left bit shift
        Float not needed
        """
        check = instruction[0][3:]
        type_chk = ["char", "int"]
        emit_inst = ["shl", "movb", "movl"]
        if check == type_chk[0]:
            self.check_type(instruction, "%eax", "%ecx", False, False, True)
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[1], "%al", instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3], True)

        elif check == type_chk[1]:
            self.check_type(instruction, None, "%ecx")
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3], True)

        else:
            check_register = "%ecx"
            self.check_type(instruction, None, check_register)
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])
            self.free_register(instruction[3], True)

    def op_shift_right(self, instruction):
        """
        This function is currently only implemented
        for integer right bit shift
        Float not needed
        """
        check = instruction[0][3:]
        type_chk = ["int", "char"]
        emit_inst = ["shr", "movb", "movl"]
        if check == type_chk[1]:
            self.check_type(instruction, "%eax", "%ecx", False, False, True)
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[1], "%al", instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3], True)
        elif check == type_chk[0]:
            check_reg = "%ecx"
            self.check_type(instruction, None, check_reg)
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3], True)
        else:
            self.check_type(instruction, None, "%ecx")
            self.emit_code(emit_inst[0], "%cl", instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3], True)
        self.free_register(instruction[2])
        self.free_register(instruction[3], True)

    def op_function_start(self, instruction):
        instr_list = ["mov %esp, %ebp", "push %ebp", instruction[0]]
        for i in range(len(instr_list)):
            self.final_code.append(instr_list[len(instr_list) - 1 - i])

    def op_return(self, instruction):
        mov_inst = "mov %ebp, %esp"
        pop_inst = "pop %ebp"
        ret_inst = "ret "
        if instruction[0] == "retq":
            instruction_length = len(instruction)
            if instruction_length == 2:
                register = self.request_register("%eax")
                instruction_dereference = self.dereference(instruction[1])
                instruction[1] = instruction_dereference
                emit_instruction1 = "movl"
                self.emit_code(emit_instruction1, instruction[1], register)
                self.free_register(register, True)
                if instruction[1][0]:
                    if instruction[1][0] == "(":
                        instruction_sliced = instruction[1][1:-1]
                        instruction[1] = instruction_sliced
                        self.free_register(instruction[1])
        else:
            requested_register = self.request_register()
            register = self.register_mapping[requested_register]
            emit_instruction1 = "movl"
            base_pointer_offset = "8(%ebp)"
            self.emit_code(emit_instruction1, base_pointer_offset, register)
            number_of_variables = int(instruction[2])
            num_div = int(number_of_variables / 4)
            num_mod = int(number_of_variables % 4)
            instruction_sliced = instruction[1][1:-1]
            instruction_temp = copy.deepcopy(instruction[1])
            reg1 = None
            if instruction[1][0] == "(":
                reg1 = self.request_register()
                self.emit_code("movl", instruction_sliced, reg1)
                val = 0
                reg1 = self.register_mapping[reg1]
                for i in range(num_div):
                    address = val + i * 4
                    if address != 0:
                        address = str(address) + f"({reg1})"
                    else:
                        address = f"({reg1})"
                    destination = "(" + str(register) + ")"
                    source = address
                    reg2 = self.register_mapping[self.request_register()]
                    if i == 0:
                        pass
                    else:
                        destination = str(int(i * 4)) + destination
                    self.move_variable(source, reg2)
                    self.move_variable(reg2, destination)
                    self.free_register(reg2)

                val = val + number_of_variables - num_mod
                for i in range(num_mod):
                    address = val + i
                    if address != 0:
                        address = str(address) + f"({reg1})"
                    else:
                        address = f"({reg1})"
                    source = address
                    destination = "(" + str(register) + ")"
                    val2 = number_of_variables - num_mod
                    if val2 == 0:
                        pass
                    elif i == 0:
                        pass
                    else:
                        destination = str(val2 + i) + destination
                    reg2 = self.register_mapping[self.request_register("%ebx")]
                    emit1 = "movzbl"
                    emit2 = "movb"
                    self.emit_code(emit1, source, reg2)
                    self.emit_code(emit2, "%bl", destination)
                    self.free_register(reg2, True)

                self.free_register(reg1)
            else:
                instruction_part = instruction_temp.split("(")[0]
                val = int(instruction_part)
                for i in range(num_div):
                    address = val + i * 4
                    addr_reg = "(%ebp)"
                    if address != 0:
                        address = str(address) + addr_reg
                    else:
                        address = addr_reg
                    source = address
                    destination = "(" + str(register) + ")"
                    if i == 0:
                        pass
                    else:
                        destination = str(int(i * 4)) + destination
                    reg2 = self.register_mapping[self.request_register()]
                    self.move_variable(source, reg2)
                    self.move_variable(reg2, destination)
                    self.free_register(reg2)

                val = val + number_of_variables - num_mod
                for i in range(num_mod):
                    address = val + i
                    addr_reg = "(%ebp)"
                    if address != 0:
                        address = str(address) + addr_reg
                    else:
                        address = addr_reg
                    source = address
                    destination = "(" + str(register) + ")"
                    val2 = number_of_variables - num_mod
                    if val2 == 0:
                        pass
                    elif i == 0:
                        pass
                    else:
                        destination = str(val2 + i) + destination
                    reg2 = self.register_mapping[self.request_register("%ebx")]
                    emit1 = "movzbl"
                    emit2 = "movb"
                    self.emit_code(emit1, source, reg2)
                    self.emit_code(emit2, "%bl", destination)
                    self.free_register(reg2, True)

            self.free_register(register)
        self.final_code.append(mov_inst)
        self.final_code.append(pop_inst)
        self.final_code.append(ret_inst)
        # self.final_code.append("mov %ebp, %esp")
        # self.final_code.append("pop %ebp")
        # self.final_code.append("ret ")

    def op_param(self, instruction):
        if len(instruction) == 2:
            instruction[1] = self.dereference(instruction[1])
            instruction_length1 = len(instruction[1])
            if instruction[1][0] == "%" and instruction_length1 > 4:
                offset = int(instruction[1][4:])
                reg1 = self.request_register()
                emit_inst = ["leal", "push"]
                self.emit_code(emit_inst[0], f"{offset}(%ebp)", reg1)
                self.emit_code(emit_inst[1], reg1)
                self.free_register(reg1)
            elif instruction[1][0] != "(":
                reg = self.request_register()
                emit_inst = ["movl", "push"]
                self.emit_code(emit_inst[0], instruction[1], reg)
                self.emit_code(emit_inst[1], reg)
                self.free_register(reg)
            else:
                self.final_code.append("push " + instruction[1])
            if instruction[1][0] == "%":
                self.free_register(instruction[1])
            elif instruction[1][0] == "(" and instruction[1][1] == "%":
                self.free_register(instruction[1][1:-1])
        else:
            instruction_length1 = len(instruction[1])
            if instruction[1][0] == "%" and instruction_length1 > 4:
                offset = int(instruction[1][4:])
                reg1 = self.request_register()
                emit_inst = ["leal", "push"]
                self.emit_code(emit_inst[0], f"{offset}(%ebp)", reg1)
                self.emit_code(emit_inst[1], reg1)
                self.free_register(reg1)
                return

            if "(" not in instruction[1]:
                reg = self.request_register()
                emit_inst = ["movl", "push"]
                self.emit_code(emit_inst[0], instruction[1], reg)
                self.emit_code(emit_inst[1], reg)
                self.free_register(reg)
                return

            elif instruction[1].count("(") > 1:
                if instruction[2] != "$4":
                    reg = self.request_register()
                    reg = self.register_mapping[reg]
                    self.emit_code("movl", instruction[1][1:-1], reg)
                    number_of_variables = int(instruction[2][1:])
                    num = number_of_variables // 4
                    self.emit_code("addl", f"${(num-1)*4}", reg)
                    emit_inst = ["push", "subl"]
                    for i in range(num):
                        self.emit_code(emit_inst[0], f"({reg})")
                        self.emit_code(emit_inst[1], "$4", reg)
                else:
                    instruction[1] = self.dereference(instruction[1])
                    self.final_code.append("push " + instruction[1])
                    instruction[1] = instruction[1][1:-1]
                    self.free_register(instruction[1])

            else:
                number_of_variables = int(instruction[2][1:])
                num_div = int(number_of_variables / 4)
                instruction_temp = copy.deepcopy(instruction[1])
                val = int(instruction_temp.split("(")[0])
                temp_code_list = []

                # for i in range(num_div):
                i = 0
                while i < num_div:
                    address = val + i * 4
                    if address != 0:
                        address = str(address) + "(%ebp)"
                    else:
                        address = "(%ebp)"
                    source = address
                    temp_code_list.append("push " + source)
                    i = i + 1

                for line in reversed(temp_code_list):
                    self.final_code.append(line)

    def op_function_call(self, instruction):
        # four arguemnts are present in function call
        if len(instruction) == 4:
            # function calls can have 3 arguments
            # isntruction[0] = call
            # instruction[1] = variable where return value is stored
            # instruction[2] = function name
            # instruction[3] = number of arguments

            self.emit_code("call ", instruction[2])
            if instruction[2] in math_func_list:
                emit1 = "fstps"
                emit2 = "addl"
                self.emit_code(emit1, instruction[1])
                self.emit_code(emit2, "$16", "%esp")

            else:
                emit1 = "movb"
                emit2 = "movl"
                if instruction[0] == "callq_char":
                    self.emit_code(emit1, "%al", instruction[1])
                    return
                self.emit_code(emit2, "%eax", instruction[1])
        else:
            self.emit_code("call ", instruction[1])

    def op_function_call_struct(self, instruction):
        # Function calls can have 4 arguments
        # isntruction[0] = call
        # instruction[1] = variable where return value is stored
        # instruction[2] = function name
        # instruction[3] = number of arguments
        register = self.request_register()
        emit = "leal"
        self.emit_code(emit, instruction[1], register)
        emit = "push "
        self.emit_code(emit, register)
        self.free_register(register)
        emit = "call "
        self.emit_code(emit, instruction[2])

    def op_negation(self, instruction):
        """
        This function is currently only implemented
        for integer negation (2's complement)
        Float implemented
        """
        check = instruction[0][7:]
        typ_check = ["int", "char", "float"]
        emit_inst = ["negl", "movb", "movl"]
        if check == typ_check[0]:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])
        elif check == typ_check[1]:
            self.check_type(instruction, "%eax", None, False, False, True)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[1], "%al", instruction[1])
            self.free_register(instruction[2])
        elif check == typ_check[2]:
            reg1, reg2, reg3 = self.float_dereference(instruction)
            self.emit_code("flds", reg2)
            self.emit_code("fchs", "")
            self.emit_code("fstps", reg1)
        else:  # kept same as int
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])

    def op_not(self, instruction):
        """
        This function is currently only implemented
        for integer bitwise not (1's complement)
        Float not needed
        """
        check = instruction[0][7:]
        typ_chk = ["int", "char"]
        emit_inst = ["notl", "movb", "movl"]
        if check == typ_chk[1]:
            self.check_type(instruction, "%eax", None, False, False, True)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[1], "%al", instruction[1])
            self.free_register(instruction[2])
        elif check == typ_chk[0]:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])
        else:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], instruction[2])
            self.emit_code(emit_inst[2], instruction[2], instruction[1])
            self.free_register(instruction[2])

    def op_if_not_zero_goto(self, instruction):
        reg = self.request_register()
        source = instruction[3]
        emit_inst = ["movl", "cmp", "jne"]
        if source[0] == "(":
            self.move_variable(source[1:-1], reg)
            self.emit_code(emit_inst[0], f"({self.register_mapping[reg]})", reg)
        else:
            self.move_variable(source, reg)
        self.emit_code(emit_inst[1], "$0", reg)
        label = self.create_label(instruction[2])
        self.emit_code(emit_inst[2], label)
        self.free_register(reg)

    def op_goto(self, instruction):
        self.emit_code("jmp", self.create_label(instruction[1]))

    def op_comparator(self, instruction):
        """
        This function is currently only implemented
        for integer comparator
        """
        comp_op = ["<=", ">=", "==", "!=", "<", ">"]
        comp_inst = "cmpl"
        typ_chk = ["int", "char", "float"]
        mov_inst = ["movl", "movb"]

        if instruction[0][3:] == typ_chk[0] or instruction[0][2:] == typ_chk[0]:
            self.check_type(instruction)
            self.emit_code(comp_inst, instruction[3], instruction[2])

            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            eight_reg = self.eight_bit_register[reg]
            if instruction[0][0:2] == comp_op[0]:
                self.emit_code("setle", eight_reg)
            elif instruction[0][0:2] == comp_op[1]:
                self.emit_code("setge", eight_reg)
            elif instruction[0][0:2] == comp_op[2]:
                self.emit_code("sete", eight_reg)
            elif instruction[0][0:2] == comp_op[3]:
                self.emit_code("setne", eight_reg)
            elif instruction[0][0] == comp_op[4]:
                self.emit_code("setl", eight_reg)
            elif instruction[0][0] == comp_op[5]:
                self.emit_code("setg", eight_reg)
            self.emit_code("movzbl", eight_reg, instruction[3])
            self.emit_code(mov_inst[0], instruction[3], instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3])
            # self.free_register(reg)
        elif instruction[0][2:6] == typ_chk[1] or instruction[0][3:7] == typ_chk[1]:

            self.check_type(instruction, "%eax", "%ecx", False, False, True)
            self.emit_code(comp_inst, instruction[3], instruction[2])

            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            eight_reg = self.eight_bit_register[reg]
            if instruction[0][0:2] == comp_op[0]:
                self.emit_code("setle", eight_reg)
            elif instruction[0][0:2] == comp_op[1]:
                self.emit_code("setge", eight_reg)
            elif instruction[0][0:2] == comp_op[2]:
                self.emit_code("sete", eight_reg)

            elif instruction[0][0:2] == comp_op[3]:
                self.emit_code("setne", eight_reg)
            elif instruction[0][0] == comp_op[4]:
                self.emit_code("setl", eight_reg)
            elif instruction[0][0] == comp_op[5]:
                self.emit_code("setg", eight_reg)
            self.emit_code("movzbl", eight_reg, instruction[3])
            self.emit_code(mov_inst[1], "%cl", instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3])
            # self.free_register(reg)

        elif instruction[0][3:] == typ_chk[2] or instruction[0][2:] == typ_chk[2]:

            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]

            rege1, rege2, rege3 = self.float_dereference(
                instruction, "%ebx", "%eax", "%esi"
            )

            if instruction[0][0:2] == comp_op[0]:
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("setnb", self.eight_bit_register[reg])
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)
            elif instruction[0][0:2] == comp_op[1]:
                self.emit_code("flds", rege3)
                self.emit_code("flds", rege2)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("setnb", self.eight_bit_register[reg])
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)
            elif instruction[0][0:2] == comp_op[2]:
                reg1 = self.request_register("%ecx")
                reg1 = self.register_mapping[reg1]
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("setnp", self.eight_bit_register[reg])
                self.emit_code(mov_inst[0], "$0", reg1)
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("cmovne", reg1, reg)
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)
                self.free_register(reg1)
            elif instruction[0][0:2] == comp_op[3]:
                reg1 = self.request_register("%ecx")
                reg1 = self.register_mapping[reg1]
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("setp", self.eight_bit_register[reg])
                self.emit_code(mov_inst[0], "$1", reg1)
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("cmovne", reg1, reg)
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)
                self.free_register(reg1)
            elif instruction[0][0] == comp_op[4]:
                self.emit_code("flds", rege2)
                self.emit_code("flds", rege3)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")
                self.emit_code("seta", self.eight_bit_register[reg])
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)
            elif instruction[0][0] == comp_op[5]:
                self.emit_code("flds", rege3)
                self.emit_code("flds", rege2)
                self.emit_code("fucomip", "%st(1)", "%st")
                self.emit_code("fstp", "%st(0)")

                self.emit_code("seta", self.eight_bit_register[reg])
                self.emit_code("movzbl", self.eight_bit_register[reg], reg)
                self.emit_code(mov_inst[0], reg, rege1)

            self.free_register(reg)
            return
        else:
            self.check_type(instruction)
            self.emit_code(comp_inst, instruction[3], instruction[2])
            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            eight_reg = self.eight_bit_register[reg]
            if instruction[0][0:2] == comp_op[0]:
                self.emit_code("setle", eight_reg)
            elif instruction[0][0:2] == comp_op[1]:
                self.emit_code("setge", eight_reg)
            elif instruction[0][0:2] == comp_op[2]:
                self.emit_code("sete", eight_reg)
            elif instruction[0][0:2] == comp_op[3]:
                self.emit_code("setne", eight_reg)
            elif instruction[0][0] == comp_op[4]:
                self.emit_code("setl", eight_reg)
            elif instruction[0][0] == comp_op[5]:
                self.emit_code("setg", eight_reg)
            self.emit_code("movzbl", eight_reg, instruction[3])
            self.emit_code(mov_inst[0], instruction[3], instruction[1])
            # self.free_register(instruction[2])
            # self.free_register(instruction[3])
            # self.free_register(reg)
        self.free_register(instruction[2])
        self.free_register(instruction[3])
        self.free_register(reg)

    def op_logical_not(self, instruction):
        typ_chk = ["int", "char"]
        emit_inst = ["cmpl", "sete", "movzbl", "movb", "movl"]
        if instruction[0][7:] == typ_chk[1]:
            self.check_type(instruction, "%eax", None, False, False, True)
            self.emit_code(emit_inst[0], "$0", instruction[2])
            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            reg = self.eight_bit_register[reg]
            self.emit_code(emit_inst[1], reg)
            self.emit_code(emit_inst[2], reg, instruction[2])
            self.emit_code(emit_inst[3], "%al", instruction[1])
            self.free_register(instruction[2])
            self.free_register("%edx")

        elif instruction[0][7:] == typ_chk[0]:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], "$0", instruction[2])
            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            reg = self.eight_bit_register[reg]
            self.emit_code(emit_inst[1], reg)
            self.emit_code(emit_inst[2], reg, instruction[2])
            self.emit_code(emit_inst[4], instruction[2], instruction[1])
            self.free_register(instruction[2])
            self.free_register("%edx")

        else:
            self.check_type(instruction)
            self.emit_code(emit_inst[0], "$0", instruction[2])
            reg = self.request_register("%edx")
            reg = self.register_mapping[reg]
            reg = self.eight_bit_register[reg]
            self.emit_code(emit_inst[1], reg)
            self.emit_code(emit_inst[2], reg, instruction[2])
            self.emit_code(emit_inst[4], instruction[2], instruction[1])
            self.free_register(instruction[2])
            self.free_register("%edx")

    def op_assignment(self, instruction):
        """
        This function is currently only implemented
        for integer assignment operators
        """
        instruction.insert(1, instruction[1])
        instruction[1] = self.dereference(instruction[1])

        op_ass = ["<", ">", "*", "/", "%", "+", "-", "&", "^", "|"]
        if instruction[0][0] == op_ass[0] or instruction[0][0] == op_ass[1]:
            instruction[0] = instruction[0][0:2] + instruction[0][3:]
        else:
            instruction[0] = instruction[0][0] + instruction[0][2:]
        if instruction[0][0] == op_ass[2]:
            self.op_multiplication(instruction)
        if instruction[0][0] == op_ass[3]:
            self.op_division(instruction)
        if instruction[0][0] == op_ass[4]:
            self.op_modulo(instruction)
        if instruction[0][0] == op_ass[5]:
            self.op_addition(instruction)
        if instruction[0][0] == op_ass[6]:
            self.op_subtraction(instruction)
        if instruction[0][0] == op_ass[7]:
            self.op_and(instruction)
        if instruction[0][0] == op_ass[8]:
            self.op_exclusive_or(instruction)
        if instruction[0][0] == op_ass[9]:
            self.op_inclusive_or(instruction)
        if instruction[0][0] == op_ass[0]:
            self.op_shift_left(instruction)
        if instruction[0][0] == op_ass[1]:
            self.op_shift_right(instruction)

        if instruction[1][0] == op_ass[4]:
            self.free_register(instruction[1])
        elif instruction[1][0] == "(" and instruction[1][1] == op_ass[4]:
            self.free_register(instruction[1][1:-1])

    def op_load_float(self, instruction):
        """
        This function is for generating floats
        """
        self.emit_code("flds", instruction[1])
        self.emit_code("fstps", instruction[2])

    def op_printf_push_float(self, instruction):
        """
        This function handles pushing of float arguments for printf
        """
        reg1, reg2, reg3 = self.float_dereference(instruction)
        emit_inst = ["flds", "subl", "leal", "fstpl"]
        self.emit_code(emit_inst[0], reg1)
        self.emit_code(emit_inst[1], "$4", "%esp")
        self.emit_code(emit_inst[2], "-8(%esp)", "%esp")
        self.emit_code(emit_inst[3], "(%esp)")

    def op_math_func_push_float(self, instruction):
        """
        This function handles pushing of float arguments for math funcs
        """

        emit_inst = ["flds", "subl", "leal", "fstpl"]
        reg1, reg2, reg3 = self.float_dereference(instruction)
        self.emit_code(emit_inst[0], reg1)
        self.emit_code(emit_inst[1], "$4", "%esp")
        self.emit_code(emit_inst[2], "-8(%esp)", "%esp")
        self.emit_code(emit_inst[3], "(%esp)")
        # reg1, reg2, reg3 = self.float_dereference(instruction)
        # self.emit_code("flds", reg1)
        # self.emit_code("subl", "$8", "%esp")
        # self.emit_code("leal", "-8(%esp)", "%esp")
        # self.emit_code("fstpl", "(%esp)")

    def op_math_func_push_int(self, instruction):
        """
        This function handles pushing of int arguments for math funcs
        """

        emit_inst = ["fildl", "subl", "leal", "fstpl"]
        reg1, reg2, reg3 = self.float_dereference(instruction)
        self.emit_code(emit_inst[0], reg1)
        self.emit_code(emit_inst[1], "$4", "%esp")
        self.emit_code(emit_inst[2], "-8(%esp)", "%esp")
        self.emit_code(emit_inst[3], "(%esp)")
        # reg1, reg2, reg3 = self.float_dereference(instruction)
        # self.emit_code("fildl", reg1)
        # self.emit_code("subl", "$8", "%esp")
        # self.emit_code("leal", "-8(%esp)", "%esp")
        # self.emit_code("fstpl", "(%esp)")

    def op_pow_func_push_int(self, instruction):
        """
        This function handles pushing of int arguments for pow func
        """

        reg1, reg2, reg3 = self.float_dereference(instruction)
        emit_inst = ["fildl", "leal", "fstpl"]
        self.emit_code(emit_inst[0], reg1)
        self.emit_code(emit_inst[1], "-8(%esp)", "%esp")
        self.emit_code(emit_inst[2], "(%esp)")

    def op_pow_func_push_float(self, instruction):
        """
        This function handles pushing of int arguments for pow func
        """

        reg1, reg2, reg3 = self.float_dereference(instruction)
        emit_inst = ["flds", "leal", "fstpl"]
        self.emit_code(emit_inst[0], reg1)
        self.emit_code(emit_inst[1], "-8(%esp)", "%esp")
        self.emit_code(emit_inst[2], "(%esp)")

    def op_printf_push_char(self, instruction):
        reg1 = self.request_register("%eax")
        instruction[1] = self.dereference(instruction[1], None, "%edx")
        emit_inst = ["movzbl", "movsbl", "push"]
        self.emit_code(emit_inst[0], instruction[1], "%eax")
        self.emit_code(emit_inst[1], "%al", "%eax")
        self.emit_code(emit_inst[2], "%eax")
        self.free_register(reg1)
        if instruction[1][0] == "%":
            self.free_register(instruction[1])
        elif instruction[1][0] == "(" and instruction[1][1] == "%":
            self.free_register(instruction[1][1:-1])

    def op_push_char(self, instruction):
        reg1 = self.request_register("%eax")
        instruction[1] = self.dereference(instruction[1], None, "%edx")
        emit_inst = ["movzbl", "subl", "movb"]
        self.emit_code(emit_inst[0], instruction[1], "%eax")
        self.emit_code(emit_inst[1], "$1", "%esp")
        self.emit_code(emit_inst[2], "%al", "0(%esp)")
        self.free_register(reg1)
        if instruction[1][0] == "%":
            self.free_register(instruction[1])
        elif instruction[1][0] == "(" and instruction[1][1] == "%":

            self.free_register(instruction[1][1:-1])

    def op_cast(self, instruction):
        # type[0] is destination, types[1] is source, instruction[1] is destination, instruction[2] is source
        types = instruction[3].split(",")
        reg = ["%ecx", "%edx"]
        for i in range(1, 3):
            instruction[i] = self.dereference(instruction[i], None, reg[i - 1])

        typ_chk = ["int", "char", "float"]
        mov_inst = ["movl", "movb"]
        if types[0] == typ_chk[2] and (
            types[1] == typ_chk[0] or types[1] == "unsigned_int"
        ):
            self.emit_code("fildl", instruction[2])
            self.emit_code("fstps", instruction[1])

        elif (types[0] == typ_chk[0] or types[0] == "unsigned_int") and types[
            1
        ] == typ_chk[2]:
            self.emit_code("flds", instruction[2])
            self.emit_code("fisttpl", instruction[1])

        elif types[0] == typ_chk[1] and types[1] == typ_chk[0]:
            reg = self.request_register("%eax")
            self.emit_code(mov_inst[0], instruction[2], "%eax")
            self.emit_code(mov_inst[1], "%al", instruction[1])
            self.free_register(reg)

        elif types[0] == typ_chk[0] and types[1] == typ_chk[1]:
            reg = self.request_register("%eax")
            self.emit_code("movzbl", instruction[2], "%eax")
            self.emit_code(mov_inst[0], "%eax", instruction[1])
            self.free_register(reg)

        elif types[0] == typ_chk[1] and types[1] == typ_chk[2]:
            reg = self.request_register("%eax")
            self.emit_code("flds", instruction[2])
            self.emit_code("subl", "$4", "%esp")
            self.emit_code("fisttpl", "0(%esp)")
            self.emit_code(mov_inst[0], "0(%esp)", reg)
            self.emit_code(mov_inst[1], "%al", instruction[1])
            self.emit_code("addl", "$4", "%esp")
            self.free_register(reg, True)

        elif types[0] == typ_chk[2] and types[1] == typ_chk[1]:
            reg = self.request_register("%eax")
            self.emit_code("movsbl", instruction[2], "%eax")
            self.emit_code("push", "%eax")
            self.emit_code("filds", "0(%esp)")
            self.emit_code("fstps", instruction[1])
            self.emit_code("pop", "%eax")

        elif types[1] == typ_chk[1]:
            reg = self.request_register("%eax")
            emit_inst = ["movzbl", "movl"]
            self.emit_code(emit_inst[0], instruction[2], "%eax")
            self.emit_code(emit_inst[1], "%eax", instruction[1])
            self.free_register("%eax")
        else:
            reg = self.request_register()
            self.emit_code(mov_inst[0], instruction[2], reg)
            self.emit_code(mov_inst[0], reg, instruction[1])
            self.free_register(reg)

        if instruction[1][0] == "%":
            self.free_register(instruction[1])
        elif instruction[1][0] == "(" and instruction[1][1] == "%":

            self.free_register(instruction[1][1:-1])
        if instruction[2][0] == "%":
            self.free_register(instruction[2])
        elif instruction[2][0] == "(" and instruction[2][1] == "%":

            self.free_register(instruction[2][1:-1])

    def op_ampersand(self, instruction):
        """
        This function handles the & operator
        """

        reg = self.request_register()
        instruction[2] = self.dereference(instruction[2])
        emit_inst = ["leal", "movl"]
        self.emit_code(emit_inst[0], instruction[2], reg)
        self.emit_code(emit_inst[1], reg, instruction[1])
        self.free_register(reg)
        if instruction[2][0] == "(":
            instruction[2] = instruction[2][1:-1]
            self.free_register(instruction[2])

    def gen_code(self, instruction):
        if instruction != []:
            if len(self.register_stack) != 6:
                for reg in self.register_list:
                    self.free_register(reg)

            if (instruction[0] is not None) and instruction[0][0:2] in [
                "*=",
                "/=",
                "%=",
                "+=",
                "-=",
                "&=",
                "^=",
                "|=",
            ]:
                self.op_assignment(instruction)
            elif len(instruction[0]) > 2 and (
                instruction[0][0:3] == "<<=" or instruction[0][0:3] == ">>="
            ):
                self.op_assignment(instruction)
            elif instruction[0][0] in ["+", "-"] or instruction[0][0:2] in ["<<", ">>"]:
                ins = instruction[0][0]
                ins2 = instruction[0][0:2]
                if ins == "+":
                    self.op_addition(instruction)
                elif ins == "-":
                    self.op_subtraction(instruction)
                elif ins2 == "<<":
                    self.op_shift_left(instruction)
                elif ins2 == ">>":
                    self.op_shift_right(instruction)
            elif instruction[0][0:2] in ["<=", ">=", "==", "!="] or instruction[0][
                0
            ] in ["<", ">"]:
                self.op_comparator(instruction)
            elif (
                instruction[0][0] == "="
                or instruction[0][0:6] == "UNARY+"
                or instruction[0][0:6] == "UNARY*"
            ):
                unary_ops = ["UNARY+", "UNARY*"]
                if (
                    instruction[0][0:6] == unary_ops[0]
                    or instruction[0][0:6] == unary_ops[1]
                ):
                    instruction[0] = "=" + instruction[0][6:]
                self.op_eq(instruction)
            elif (instruction[0] is not None) and instruction[0][0] in [
                "*",
                "|",
                "^",
                "&",
            ]:
                ins = instruction[0][0]
                if ins == "*":
                    self.op_multiplication(instruction)
                elif ins == "|":
                    self.op_inclusive_or(instruction)
                elif ins == "^":
                    self.op_exclusive_or(instruction)
                elif ins == "&":
                    self.op_and(instruction)
            elif (
                (len(instruction) == 1)
                and (instruction[0][-1] == ":")
                and (instruction[0][0] != ".")
                and ("." not in instruction[0])
            ):
                self.op_function_start(instruction)
            elif instruction[0] == "param":
                self.op_param(instruction)
            elif instruction[0] == "callq" or instruction[0] == "callq_char":
                self.op_function_call(instruction)
            elif instruction[0] == "callq_struct":
                self.op_function_call_struct(instruction)
            elif instruction[0] == "retq" or instruction[0] == "retq_struct":
                self.op_return(instruction)
                self.final_code.append("")
            elif instruction[0][0] == "/":
                self.op_division(instruction)
            elif instruction[0][0] == "%":
                self.op_modulo(instruction)
            elif instruction[0][0:6] in ["UNARY-", "UNARY~", "UNARY!", "UNARY&"]:
                if instruction[0][0:6] == "UNARY~":
                    self.op_not(instruction)
                elif instruction[0][0:6] == "UNARY-":
                    self.op_negation(instruction)
                elif instruction[0][0:6] == "UNARY&":
                    self.op_ampersand(instruction)
                elif instruction[0][0:6] == "UNARY!":
                    self.op_logical_not(instruction)
            elif instruction[0][0:4] == "ifnz" and instruction[1][0:4] == "goto":
                self.op_if_not_zero_goto(instruction)
            elif instruction[0][0:4] == "goto":
                self.op_goto(instruction)
            elif instruction[0] == "load_float":
                self.op_load_float(instruction)
            elif instruction[0] == "printf_push_float":
                self.op_printf_push_float(instruction)
            elif instruction[0] == "push_char":
                self.op_push_char(instruction)
            elif instruction[0] == "math_func_push_float":
                self.op_math_func_push_float(instruction)
            elif instruction[0] == "math_func_push_int":
                self.op_math_func_push_int(instruction)
            elif instruction[0] == "pow_func_push_int":
                self.op_pow_func_push_int(instruction)
            elif instruction[0] == "pow_func_push_float":
                self.op_pow_func_push_float(instruction)
            elif instruction[0] == "printf_push_char":
                self.op_printf_push_char(instruction)
            elif instruction[0] == "cast":
                self.op_cast(instruction)
            else:
                self.final_code.append(" ".join(instruction))

        else:
            return


if __name__ == "__main__":
    file = open(sys.argv[1], "r")
    fname = sys.argv[1].split("/")[-1].split(".")[0]
    code = file.readlines()
    codegen = CodeGenerator()
    for lineno, instr in enumerate(code):
        string_label = "label " + str(lineno + 1) + ":"
        codegen.final_code.append(string_label)
        instr = instr.split()[1:]
        codegen.gen_code(instr)
        codegen.final_code.append("")

    for_print = []
    for line in codegen.final_code:
        if len(line) >= 5:
            if line[0:5] == "label":
                if int(line[6:-1]) in codegen.label_list:
                    for_print.append(codegen.label_list[int(line[6:-1])] + ":")
            else:
                for_print.append(line)
        else:
            for_print.append(line)
    codegen.final_code = for_print
    # print("Output Assembly is at out/assembly/" + fname + ".s")
    with open("out/assembly/" + fname + ".s", "w") as sys.stdout:
        for line in codegen.final_code:
            print(line)
