# inspired from https://github.com/dabeaz/ply/blob/master/doc/ply.md

import ply.lex as lex
from tabulate import tabulate
import sys
import argparse

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
    "NULL",
]

# ply requires keywords to be placed inside a dict
keywords_dict = {}
for i in keywords:
    keywords_dict[i] = i.upper()

# List of token names.
tokens = [
    # Comment
    "COMMENT",
    # ID
    "IDENTIFIER",
    # Constant
    "BOOL_CONSTANT",
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

# Regular Expressions for Constants

# Regex defined inside functions are added first in the master regex


def t_COMMENT(t):
    # https://stackoverflow.com/a/16165598
    r"(//.*|/\*(\*(?!/)|[^*])*\*/)"
    t.lexer.lineno += t.value.count("\n")


def t_IDENTIFIER(t):
    r"[\_a-zA-Z]+[a-zA-Z0-9\_]*"
    t.type = keywords_dict.get(t.value, "IDENTIFIER")  # Check for reserved words
    return t


# Define a rule so we can track line numbers
def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


# exponent can be a positive/negative integer
EXPONENT = r"[eE][+-]?\d+"

# handle hex and octal into integer constant
INTEGER_DECIMAL_LIT = r"[1-9][0-9]*"
INTEGER_HEX_LIT = r"0[xX][0-9a-fA-F]+"
INTEGER_OCTAL_LIT = r"0[0-7]*"

# float can be with or without exponent
@lex.TOKEN(r"([+-]?[0-9]+(\.[0-9]*)?" + "(" + EXPONENT + "))|([+-]?[0-9]*\.[0-9]+)")
def t_FLOAT_CONSTANT(t):
    return t


# hex, octal, decimal all belong to a single token class
@lex.TOKEN(
    "((" + ")|(".join([INTEGER_DECIMAL_LIT, INTEGER_HEX_LIT, INTEGER_OCTAL_LIT]) + "))"
)
def t_INTEGER_CONSTANT(t):
    return t


# one character within single quotes, can also be an escape character
# [^\'\\\n] - excludes single quote, backslash and newline
# \\[\\\?\'\"btn] - handle escape characters listed in specs

t_CHAR_CONSTANT = r"(\'([^\'\\\n]|(\\[\\\?\'\"btn0]))\')|(\'\')"
t_STRING_CONSTANT = r"\"([^\"\\\n]|(\\[\\\?\'\"btn0]))*\""

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

# Error function
def t_error(t):
    print(
        f"Illegal character {t.value[0]} at line {t.lineno} column {find_column(inp, t)}"
    )
    t.lexer.skip(1)


# To retrieve column number
def find_column(input, token):
    line_start = input.rfind("\n", 0, token.lexpos)
    return token.lexpos - line_start


# Made changes, pehle exact tha
def main_lexer(lexer, input_file):
    lexer.input(input_file)
    list_of_tokens = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        else:
            col_val = find_column(inp, tok)
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

    lexer = lex.lex(debug=int(args.debug))

    if args.out is not None:
        sys.stdout = open(args.out, "w")

    main_lexer(lexer, inp)
