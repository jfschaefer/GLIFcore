"""
    Generates stubs for concrete syntax and semantics construction from GF abstract syntaxes.
    This is only a prototype implementation, supporting a subset of abstract syntaxes.
    Eventually, this code should be re-implemented properly.
"""

import re
import os
from typing import Optional
from .utils import Result


def tokenizer(string):
    string += " \n"  # hack to avoid running out of string indices too early
    tokens = []
    pos = 0
    linecounter = 1
    while pos < len(string):
        if string[pos].isspace():
            if string[pos] == "\n":
                linecounter += 1
            pos += 1
        elif string[pos].isalnum() or string[pos] == "_":
            token = string[pos]
            pos += 1
            while string[pos].isalnum() or string[pos] == "_":
                token += string[pos]
                pos += 1
            tokens += [(token, "id", linecounter)]
        elif string[pos] in "->*(){}=;,:":
            token = string[pos]
            pos += 1
            while string[pos] in "->*(){}=;,:":
                token += string[pos]
                pos += 1
            # handle comments:
            if token.startswith("--"):
                while string[pos] != "\n":
                    pos += 1
            elif token.startswith("{-") and "-}" not in token:
                while not (string[pos] != "-" and string[pos + 1] != "}"):
                    if pos == len(string) - 2:
                        break
                    pos += 1
            else:
                tokens += [(token, "op", linecounter)]
        else:
            raise Exception("Unexpected character in line " + str(linecounter) + ": " + repr(string[pos]))
    return tokens


def pop_op(tokens, pos, op):
    if tokens[pos][0] != op:
        raise Exception(f"Line {tokens[pos][2]}: Expected '{op}', but found '{tokens[pos][0]}'")
    return pos + 1


def pop_id(tokens, pos):
    if tokens[pos][1] != "id":
        raise Exception(f"Line {tokens[pos][2]}: Expected identifier, but found '{tokens[pos][0]}'")
    return tokens[pos][0], pos + 1


def process_tokens(tokens):
    if tokens[0][0] != "abstract":
        raise Exception("Line 1: Expected keyword 'abstract'")
    if tokens[1][1] != "id":
        raise Exception(f"Line {tokens[0][2]}: Expected name of abstract syntax")
    name = tokens[1][0]
    pop_op(tokens, 2, "=")

    pos = 3
    imports = []
    while tokens[pos][0] != "{":
        if tokens[pos][1] != "id":
            raise Exception(f"Line {tokens[pos - 1][2]}: Expected '{{'")
        imports += [tokens[pos][0]]
        pos += 1
        if tokens[pos][0] not in [",", "**"]:
            raise Exception(f"Line {tokens[pos - 1][2]}: Expected '{{'")
        pos += 1
    pos += 1

    catfun = None
    cats = []
    funs = []
    while tokens[pos][0] != "}":
        if tokens[pos][0] == "cat":
            catfun = "cat"
            pos += 1
        elif tokens[pos][0] in ["fun", "data"]:
            catfun = "fun"
            pos += 1
        elif catfun == "skip":
            pos += 1
            continue
        elif tokens[pos][0] in ["flags"]:
            catfun = "skip"
        elif tokens[pos][1] == "op":
            raise Exception(f"Line {tokens[pos][2]}: Unexpected token: '{tokens[pos][0]}'")
        else:
            n, pos = pop_id(tokens, pos)
            if catfun == "cat":
                pos = pop_op(tokens, pos, ";")
                cats += [n]
            elif catfun == "fun":
                names = [n]
                while tokens[pos][0] == ",":
                    pos += 1
                    n, pos = pop_id(tokens, pos)
                    names.append(n)
                pos = pop_op(tokens, pos, ":")
                t = []
                while tokens[pos][1] == "id":
                    t += [tokens[pos][0]]
                    pos += 1
                    if tokens[pos][0] == "->":
                        pos += 1
                pos = pop_op(tokens, pos, ";")
                for n in names:
                    funs += [(n, t)]
            else:
                raise Exception(f"I don't know if '{n}' is a cat or a fun")
    pos = pop_op(tokens, pos, "}")
    if pos != len(tokens):
        raise Exception(f"Line {tokens[pos][2]}: Didn't expect any more tokens")
    return name, imports, cats, funs


def generate_view(file, source=None, namesuffix="Semantics"):
    with open(file) as fp:
        args = process_tokens(tokenizer(fp.read()))

    name, imports, cats, funs = args
    j_dd = "\u2759"
    j_md = "\u275a"
    j_raa = "\u27f6"
    blank = "_"

    result = ""

    if not source:
        source = "?" + name

    # semantics construction stub:
    result += "view " + name + namesuffix + " : " + source + " -> " + blank + " =\n"
    for import_ in imports:
        result += "    include ?" + import_ + namesuffix + " " + j_dd + "\n"
    if imports and cats:
        result += "\n"
    for cat in cats:
        result += "    " + cat + " = " + blank + " " + j_dd + "\n"
    if (imports or cats) and funs:
        result += "\n"
    for fun in funs:
        result += "    // " + fun[0] + " : " + (" " + j_raa + " ").join(fun[1]) + " " + j_dd + "\n"
        result += "    " + fun[0] + " = " + blank + " " + j_dd + "\n"
    result += j_md + "\n"
    return result


def generate_concrete(file, lang):
    with open(file) as fp:
        args = process_tokens(tokenizer(fp.read()))

    name, imports, cats, funs = args
    blank = "_"

    result = ""

    # semantics construction stub:
    result += "concrete " + name + lang + " of " + name + " = "
    if imports:
        result += ", ".join(i + lang for i in imports) + " ** "
    result += "{\n"
    if cats:
        result += "  lincat\n"
    for cat in cats:
        result += "    " + cat + " = " + blank + " ;\n"
    if cats and funs:
        result += "\n"
    if funs:
        result += "  lin\n"
    for fun in funs:
        result += "    -- " + fun[0] + " : " + " -> ".join(fun[1]) + "\n"
        result += "    " + fun[0] + " " + (blank + " ") * (len(fun[1]) - 1) + "= " + blank + " ;\n"
    result += "}\n"
    return result


def generate(target: str, cwd: str, view_base: Optional[str]) -> Result[str]:
    match = re.match(r'(view|concrete) *([A-Z]\w*)([A-Z][a-z]*)', target)
    if not match:
        return Result(False, None, f'Failed to match "{target}"')
    type_ = match.group(1)
    name = match.group(2)
    suffix = match.group(3)

    filename = os.path.join(cwd, f'{name}.gf')
    if not os.path.isfile(filename):
        return Result(False, None, f'No such file: {filename}')

    try:
        if type_ == 'view':
            assert view_base
            return Result(True, generate_view(filename, f'{view_base}/{name}.gf?{name}', suffix))
        else:
            assert type_ == 'concrete'
            return Result(True, generate_concrete(filename, suffix))
    except Exception as ex:
        return Result(False, None, f'Error during stub generation: {str(ex)}')
