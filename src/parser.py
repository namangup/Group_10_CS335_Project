# https://www.lysator.liu.se/c/ANSI-C-grammar-y.html
# https://github.com/dabeaz/ply/blob/master/doc/ply.md

import ply.yacc as yacc
from lexer import lexer, tokens, keywords
import argparse
import sys


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


precedence = (("nonassoc", "IF_STATEMENTS"), ("nonassoc", "ELSE"))


def p_start(p):
    """
    start : translation_unit
    """
    p[0] = ["start"] + p[1:]


def p_error(p):
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


def p_constant(p):
    """
    constant : INTEGER_CONSTANT
            | FLOAT_CONSTANT
            | CHAR_CONSTANT
            | TRUE
            | FALSE
            | NULL
    """
    p[0] = ["constant"] + p[1:]


def p_primary_expression(p):
    """
    primary_expression : IDENTIFIER
                    | constant
                    | STRING_CONSTANT
                    | '(' expression ')'
    """
    p[0] = ["primary_expression"] + p[1:]


def p_postfix_expression(p):
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
    p[0] = ["postfix_expr"] + p[1:]


def p_argument_expression_list(p):
    """
    argument_expression_list : assignment_expression
                            | argument_expression_list ',' assignment_expression
    """
    p[0] = ["argument_expression_list"] + p[1:]


def p_unary_expression(p):
    """
    unary_expression : postfix_expression
                    | INC_OP unary_expression
                    | DEC_OP unary_expression
                    | unary_operator cast_expression
                    | SIZEOF unary_expression
                    | SIZEOF '(' type_name ')'
    """

    p[0] = ["unary_expression"] + p[1:]


def p_unary_operator(p):
    """
    unary_operator : '&'
                | '*'
                | '+'
                | '-'
                | '~'
                | '!'
    """
    p[0] = ["unary_operator"] + p[1:]


def p_cast_expression(p):
    """
    cast_expression : unary_expression
                    | '(' type_name ')' cast_expression
    """
    p[0] = ["cast_expression"] + p[1:]


def p_multiplicative_expression(p):
    """
    multiplicative_expression : cast_expression
                            | multiplicative_expression '*' cast_expression
                            | multiplicative_expression '/' cast_expression
                            | multiplicative_expression '%' cast_expression
    """
    p[0] = ["multiplicative_expression"] + p[1:]


def p_additive_expression(p):
    """
    additive_expression : multiplicative_expression
                        | additive_expression '+' multiplicative_expression
                        | additive_expression '-' multiplicative_expression
    """
    p[0] = ["additive_expression"] + p[1:]


def p_shift_expression(p):
    """
    shift_expression : additive_expression
                    | shift_expression LEFT_OP additive_expression
                    | shift_expression RIGHT_OP additive_expression
    """
    p[0] = ["shift_expression"] + p[1:]


def p_relational_expression(p):
    """
    relational_expression : shift_expression
                        | relational_expression '<' shift_expression
                        | relational_expression '>' shift_expression
                        | relational_expression LE_OP shift_expression
                        | relational_expression GE_OP shift_expression
    """
    p[0] = ["relational_expression"] + p[1:]


def p_equality_expression(p):
    """
    equality_expression : relational_expression
                        | equality_expression EQ_OP relational_expression
                        | equality_expression NE_OP relational_expression
    """
    p[0] = ["equality_expression"] + p[1:]


def p_and_expression(p):
    """
    and_expression : equality_expression
                | and_expression '&' equality_expression
    """
    p[0] = ["and_expression"] + p[1:]


def p_exclusive_or_expression(p):
    """
    exclusive_or_expression : and_expression
                            | exclusive_or_expression '^' and_expression
    """
    p[0] = ["exclusive_or_expression"] + p[1:]


def p_inclusive_or_expression(p):
    """
    inclusive_or_expression : exclusive_or_expression
                            | inclusive_or_expression '|' exclusive_or_expression
    """
    p[0] = ["inclusive_or_expression"] + p[1:]


def p_logical_and_expression(p):
    """logical_and_expression : inclusive_or_expression
    | logical_and_expression AND_OP inclusive_or_expression
    """
    p[0] = ["logical_and_expression"] + p[1:]


def p_logical_or_expression(p):
    """logical_or_expression : logical_and_expression
    | logical_or_expression OR_OP logical_and_expression
    """
    p[0] = ["logical_or_expression"] + p[1:]


def p_conditional_expression(p):
    """conditional_expression : logical_or_expression
    | logical_or_expression '?' expression ':' conditional_expression
    """
    p[0] = ["conditional_expression"] + p[1:]


def p_assignment_expression(p):
    """
    assignment_expression : conditional_expression
                        | unary_expression assignment_operator assignment_expression
    """
    p[0] = ["assignment_expression"] + p[1:]


def p_assignment_operator(p):
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
    p[0] = ["assignment_operator"] + p[1:]


def p_expression(p):
    """
    expression : assignment_expression
            | expression ',' assignment_expression
    """
    p[0] = ["expression"] + p[1:]


def p_constant_expression(p):
    """
    constant_expression	: conditional_expression
    """
    p[0] = ["constant_expression"] + p[1:]


# Initializers


def p_initializer(p):
    """
    initializer : assignment_expression
                | '{' initializer_list '}'
                | '{' initializer_list ',' '}'
    """
    p[0] = ["initializer"] + p[1:]


def p_initializer_list(p):
    """
    initializer_list : initializer
                    | initializer_list ',' initializer
    """
    p[0] = ["initializer_list"] + p[1:]


# Declarators
def p_declaration(p):
    """declaration	: declaration_specifiers ';'
    | declaration_specifiers init_declarator_list ';'
    """
    p[0] = ["declaration"] + p[1:]


def p_declaration_specifiers(p):
    """declaration_specifiers : type_specifier
    | type_specifier declaration_specifiers
    """

    p[0] = ["declaration_specifiers"] + p[1:]


def p_init_declarator_list(p):
    """init_declarator_list : init_declarator
    | init_declarator_list ',' init_declarator
    """
    p[0] = ["init_declarator_list"] + p[1:]


def p_init_declarator(p):
    """init_declarator : declarator
    | declarator '=' initializer
    """
    p[0] = ["init_declarator"] + p[1:]


def p_type_specifier(p):
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
    p[0] = ["type_specifier"] + p[1:]


def p_struct_or_union_specifier(p):
    """struct_or_union_specifier : struct_or_union IDENTIFIER '{' struct_declaration_list '}'
    | struct_or_union '{' struct_declaration_list '}'
    | struct_or_union IDENTIFIER
    """
    p[0] = ["struct_or_union_specifier"] + p[1:]


def p_struct_or_union(p):
    """struct_or_union : STRUCT
    | UNION
    """
    p[0] = ["struct_or_union"] + p[1:]


def p_struct_declaration_list(p):
    """struct_declaration_list : struct_declaration
    | struct_declaration_list struct_declaration
    """
    p[0] = ["struct_declaration_list"] + p[1:]


def p_struct_declaration(p):
    """struct_declaration : specifier_qualifier_list struct_declarator_list ';'"""
    p[0] = ["struct_declaration"] + p[1:]


def p_specifier_qualifier_list(p):
    """specifier_qualifier_list : type_specifier
    | type_specifier specifier_qualifier_list
    """
    p[0] = ["specifier_qualifier_list"] + p[1:]


def p_struct_declarator_list(p):
    """struct_declarator_list : struct_declarator
    | struct_declarator_list ',' struct_declarator
    """
    p[0] = ["struct_declarator_list"] + p[1:]


def p_struct_declarator(p):
    """struct_declarator : declarator
    | ':' constant_expression
    | declarator ':' constant_expression
    """
    p[0] = ["struct_declarator"] + p[1:]


def p_declarator(p):
    """declarator : pointer direct_declarator
    | direct_declarator
    """
    p[0] = ["declarator"] + p[1:]


def p_direct_declarator(p):
    """direct_declarator : IDENTIFIER
    | '(' declarator ')'
    | direct_declarator '[' constant_expression ']'
    | direct_declarator '[' ']'
    | direct_declarator '(' parameter_type_list ')'
    | direct_declarator '(' identifier_list ')'
    | direct_declarator '(' ')'
    """
    p[0] = ["direct_declarator"] + p[1:]


def p_pointer(p):
    """pointer : '*'
    | '*' pointer
    """
    p[0] = ["pointer"] + p[1:]


def p_parameter_type_list(p):
    """parameter_type_list : parameter_list"""
    p[0] = ["parameter_type_list"] + p[1:]


def p_parameter_list(p):
    """parameter_list : parameter_declaration
    | parameter_list ',' parameter_declaration
    """
    p[0] = ["parameter_list"] + p[1:]


def p_parameter_declaration(p):
    """parameter_declaration : declaration_specifiers declarator
    | declaration_specifiers abstract_declarator
    | declaration_specifiers
    """
    p[0] = ["parameter_declaration"] + p[1:]


def p_identifier_list(p):
    """identifier_list : IDENTIFIER
    | identifier_list ',' IDENTIFIER
    """
    p[0] = ["identifier_list"] + p[1:]


def p_type_name(p):
    """type_name : specifier_qualifier_list
    | specifier_qualifier_list abstract_declarator
    """
    p[0] = ["type_name"] + p[1:]


def p_abstract_declarator(p):
    """abstract_declarator : pointer
    | direct_abstract_declarator
    | pointer direct_abstract_declarator
    """
    p[0] = ["abstract_declarator"] + p[1:]


def p_direct_abstract_declarator(p):
    """direct_abstract_declarator : '(' abstract_declarator ')'
    | '[' ']'
    | '[' constant_expression ']'
    | direct_abstract_declarator '[' ']'
    | direct_abstract_declarator '[' constant_expression ']'
    | '(' ')'
    | '(' parameter_type_list ')'
    | direct_abstract_declarator '(' ')'
    | direct_abstract_declarator '(' parameter_type_list ')'
    """
    p[0] = ["direct_abstract_declarator"] + p[1:]


# Statements


def p_statement(p):
    """
    statement   : labeled_statement
                | compound_statement
                | expression_statement
                | selection_statement
                | iteration_statement
                | jump_statement
    """
    p[0] = ["statement"] + p[1:]


def p_labeled_statement(p):
    """
    labeled_statement   : IDENTIFIER ':' statement
                        | CASE constant_expression ':' statement
                        | DEFAULT ':' statement
    """
    p[0] = ["labeled_statement"] + p[1:]


def p_compound_statement(p):
    """
    compound_statement  : '{' '}'
                        | '{' statement_list '}'
                        | '{' declaration_list '}'
                        | '{' declaration_list statement_list '}'
    """
    p[0] = ["compound_statement"] + p[1:]


def p_declaration_list(p):
    """
    declaration_list    : declaration
                        | declaration_list declaration
    """
    p[0] = ["declaration_list"] + p[1:]


def p_statement_list(p):
    """
    statement_list  : statement
                    | statement_list statement
    """
    p[0] = ["statement_list"] + p[1:]


def p_expression_statement(p):
    """
    expression_statement    : ';'
                            | expression ';'
    """
    p[0] = ["expression_statement"] + p[1:]


def p_selection_statement(p):
    """
    selection_statement : IF '(' expression ')' statement %prec IF_STATEMENTS
                        | IF '(' expression ')' statement ELSE statement
                        | SWITCH '(' expression ')' statement
    """
    p[0] = ["selection_statement"] + p[1:]


def p_iteration_statement(p):
    """
    iteration_statement : WHILE '(' expression ')' statement
                        | DO statement WHILE '(' expression ')'
                        | FOR '(' expression_statement expression_statement ')' statement
                            | FOR '(' expression_statement expression_statement expression ')' statement
    """
    p[0] = ["iteration_statement"] + p[1:]


def p_jump_statement(p):
    """
    jump_statement  : CONTINUE ';'
                    | BREAK ';'
                    | RETURN ';'
                    | RETURN expression ';'
    """
    p[0] = ["jump_statement"] + p[1:]


# External declaration and function definitions
def p_translation_unit(p):
    """translation_unit : translation_unit external_declaration
    | external_declaration
    """
    p[0] = ["translation_unit"] + p[1:]


def p_external_declaration(p):
    """external_declaration : function_definition
    | declaration
    """
    p[0] = ["external_declaration"] + p[1:]


def p_function_definition(p):
    """function_definition : declaration_specifiers declarator declaration_list compound_statement
    | declaration_specifiers declarator compound_statement
    | declarator declaration_list compound_statement
    | declarator compound_statement
    """
    p[0] = ["function_definition"] + p[1:]


if __name__ == "__main__":

    aparser = argparse.ArgumentParser()
    aparser.add_argument(
        "-d", "--debug", action="store_true", help="Parser Debug Mode", default=False
    )
    aparser.add_argument(
        "-o", "--out", help="Store output of parser in a file", default=None
    )
    aparser.add_argument("infile", help="Input File")
    args = aparser.parse_args()

    parser = yacc.yacc(debug=int(args.debug))

    with open(args.infile, "r") as f:
        inp = f.read()

    lexer.lines = inp.split("\n")
    lexer.inp = inp
    if args.out is not None:
        sys.stdout = open(args.out, "w")

    print(parser.parse(inp))
