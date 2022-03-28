# inspired from https://github.com/dabeaz/ply/blob/master/doc/ply.md
# added object oriented classes

import ply.lex as lex
from tabulate import tabulate
import sys, os
import argparse


class Lexer:

    # Add docstrings if necessary
    def __init__(self, error_func):
        self.error_func = error_func
        ## NOT ADDED : self.last_token

    def build(self, **kwargs):
        self.lexer = lex.lex(object=self, **kwargs)

    def _error(self, msg, token):
        # helper function to show an extra error message
        row = token.lineno
        line_start = self.lexer.lexdata.rfind("\n", 0, token.lexpos)
        col = token.lexpos - line_start

        self.error_func(msg, row, col)
        self.lexer.skip(1)

    keywords = [
        "bool",
        "break",
        "case",
        "char",
        "continue",
        "default",
        "do",
        "float",
        "for",
        "if",
        "else",
        "int",
        "return",
        "short",
        "signed",
        "struct",
        "switch",
        "union",
        "unsigned",
        "void",
        "while",
        "true",
        "false",
        "sizeof",
    ]

    # ply requires keywords to be placed inside a dict
    keywords_dict = {}
    for i in keywords:
        keywords_dict[i] = i.upper()

    # List of token names.
    tokens = [
        "IDENTIFIER",
        # Constant
        "INTEGER_CONSTANT",
        "FLOAT_CONSTANT",
        "CHAR_CONSTANT",
        "STRING_CONSTANT",
        # Arithmetic Assignment
        "ADD_ASSIGN",  # +=
        "SUB_ASSIGN",  # -=
        "MUL_ASSIGN",  # *=
        "DIV_ASSIGN",  # /=
        "MOD_ASSIGN",  # %=
        # Logical Operator
        "AND_OP",  # &&
        "OR_OP",  # ||
        "LEFT_OP",  # <<
        "RIGHT_OP",  # >>
        # Comparison Operator
        "EQ_OP",  # ==
        "GE_OP",  # >=
        "LE_OP",  # <=
        "NE_OP",  # !=
        # Bit Assignment
        "AND_ASSIGN",  # &=
        "OR_ASSIGN",  # |=
        "XOR_ASSIGN",  # ^=
        "LEFT_ASSIGN",  # <<=
        "RIGHT_ASSIGN",  # >>=
        # Miscellaneous Operator
        "INC_OP",  # ++
        "DEC_OP",  # --
        "PTR_OP",  # ->
    ] + list(keywords_dict.values())

    literals = [
        # Parenthesis
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        # Arithemetic Operator
        "+",
        "-",
        "*",
        "/",
        "=",
        "%",
        # Comparison Operator
        ">",
        "<",
        # Bit Operator
        "&",
        "~",
        "|",
        "!",
        "^",
        # Other
        ";",
        ",",
        ".",
        ":",
        "?",
    ]

    # Regex defined inside functions are added first in the master regex

    def t_COMMENT(self, t):
        # https://stackoverflow.com/a/16165598
        r"(//.*|/\*(\*(?!/)|[^*])*\*/)"
        t.lexer.lineno += t.value.count("\n")

    def t_IDENTIFIER(self, t):
        r"[\_a-zA-Z]+[a-zA-Z0-9\_]*"
        t.type = self.keywords_dict.get(
            t.value, "IDENTIFIER"
        )  # Check for reserved words
        if t.type == "IDENTIFIER":
            contents = {"line": t.lineno}
            t.value = {"lexeme": t.value, "additional": contents}
        return t

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)

    # exponent can be a positive/negative integer
    EXPONENT = r"[eE][+-]?\d+"

    # handle hex and octal into integer constant
    INTEGER_DECIMAL_LIT = r"[1-9][0-9]*"
    INTEGER_HEX_LIT = r"0[xX][0-9a-fA-F]+"
    INTEGER_OCTAL_LIT = r"0[0-7]*"

    # Character constants
    char_const = r"(\'([^\'\\\n]|(\\[\\\?\'\"btn0]))\')"

    @lex.TOKEN(char_const)
    def t_CHAR_CONSTANT(self, t):
        t.type = "CHAR_CONSTANT"
        t.value = t.value[1:-1]

        if len(t.value) == 1:
            t.value = ord(t.value)
        else:
            if t.value == "\b":
                t.value = ord("\b")
            elif t.value == "\t":
                t.value = ord("\t")
            elif t.value == "\n":
                t.value = ord("\n")
            elif t.value == "\0":
                t.value = ord("\0")

        return t

    # Float constants
    # float can be with or without exponent
    @lex.TOKEN(r"([+-]?[0-9]+(\.[0-9]*)?" + "(" + EXPONENT + "))|([+-]?[0-9]*\.[0-9]+)")
    def t_FLOAT_CONSTANT(self, t):
        t.value = float(t.value)
        t.type = "FLOAT_CONSTANT"
        return t

    # hex, octal, decimal all belong to a single token class
    @lex.TOKEN(
        "(("
        + ")|(".join([INTEGER_DECIMAL_LIT, INTEGER_HEX_LIT, INTEGER_OCTAL_LIT])
        + "))"
    )
    def t_INTEGER_CONSTANT(self, t):
        base = 10  # default base 10
        # octal
        if t.value[0] == "0" and (
            len(t.value) > 1 and t.value[1] >= "0" and t.value[1] <= "7"
        ):
            base = 8
        # hexadecimal
        elif t.value[0] == "0" and (
            len(t.value) > 1 and (t.value[1] == "x" or t.value[1] == "X")
        ):
            base = 16

        t.value = int(t.value, base)
        t.type = "INTEGER_CONSTANT"
        return t

    # one character within single quotes, can also be an escape character
    # [^\'\\\n] - excludes single quote, backslash and newline
    # \\[\\\?\'\"btn] - handle escape characters listed in specs

    STRING_CONSTANT = r"\"([^\"\\\n]|(\\[\\\?\'\"btn0]))*\""

    @lex.TOKEN(STRING_CONSTANT)
    def t_STRING_CONSTANT(self, t):
        return t

    # Regular Expressions for Arithmetic Assignment

    t_ADD_ASSIGN = r"\+="
    t_SUB_ASSIGN = r"-="
    t_MUL_ASSIGN = r"\*="
    t_DIV_ASSIGN = r"/="
    t_MOD_ASSIGN = r"%="

    # Regular Expressions for Logical Operators
    t_AND_OP = r"&&"
    t_OR_OP = r"\|\|"
    t_LEFT_OP = r"<<"
    t_RIGHT_OP = r">>"

    # Regular Expressions for Comparison Operator
    t_EQ_OP = r"=="
    t_GE_OP = r">="
    t_LE_OP = r"<="
    t_NE_OP = r"!="

    # Regular Expressions for Bit Assignment
    t_AND_ASSIGN = r"&="
    t_OR_ASSIGN = r"\|="
    t_XOR_ASSIGN = r"\^="
    t_LEFT_ASSIGN = r"<<="
    t_RIGHT_ASSIGN = r">>="

    # Regular Expressions for Misc Operator
    t_INC_OP = r"\+\+"
    t_DEC_OP = r"--"
    t_PTR_OP = r"->"

    t_ignore = " \t"

    unending_block_comment = r"/\*(.|\n)*$"

    @lex.TOKEN(unending_block_comment)
    def t_UNENDING_BLOCK_COMMENT(self, t):
        msg = "Block comment does not end"
        self._error(msg, t)

    unmatched_single_quote = r"(\'(\\.|[^\\\'])+$)"

    @lex.TOKEN(unmatched_single_quote)
    def t_UNMATCHED_SINGLE_QUOTE(self, t):
        msg = "Unmatched ' encountered"
        self._error(msg, t)

    unmatched_double_quote = r'(\"(\\.|[^\\"])*$)'

    @lex.TOKEN(unmatched_double_quote)
    def t_UNMATCHED_DOUBLE_QUOTE(self, t):
        msg = 'Unmatched " encountered'
        self._error(msg, t)

    # Error function
    def t_error(self, t):
        msg = "Illegal token found"
        self._error(msg, t)


####################################################3


errorPresent = False


def error_func(msg, row, col):
    global errorPresent
    print(f"Error found in line number {row}, column {col}:")
    print(msg)
    errorPresent = True


# Defining an object of the lexer
lexer = Lexer(error_func)

lexer.build()

# To retrieve column number
def find_column(input, token):
    line_start = input.rfind("\n", 0, token.lexpos)
    return token.lexpos - line_start


def main_lexer(lexer, input_file):
    global errorPresent
    lexer.input(input_file)
    list_of_tokens = []
    while True:
        tok = lexer.token()
        # if errorPresent:
        #     print(f'Errors found. Aborting scanning of {sys.argv[1]}....')
        #     sys.exit(1) # does this find only 1 error (how to solve multiple err case)
        if not tok:
            break
        else:
            col_val = find_column(input_file, tok)
            column_num = str(col_val)
            line_num = str(tok.lineno)
            list_of_tokens.append([tok.type, tok.value, line_num, column_num])

    final_list = tabulate(
        list_of_tokens, headers=["Token", "Lexeme", "Line#", "Column#"]
    )
    print(final_list)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug Mode", default=False
    )
    parser.add_argument(
        "-o", "--out", help="Store output of lexer in a file", default=None
    )
    parser.add_argument("infile", help="Input File")
    args = parser.parse_args()

    with open(args.infile, "r") as f:
        inp = f.read()

    if args.out is not None:
        sys.stdout = open(args.out, "w")

    lexer.lexerinp = inp
    main_lexer(lexer.lexer, inp)
