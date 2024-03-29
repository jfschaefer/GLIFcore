"""
    Pygments-based syntax highlighting for GLIF.
    Requires (correct) version of mmtpygments.
    The code is very experimental and fragile.
    Not all pygments features can be used because a CodeMirror highlighter is automatically
    generated from the lexers.

    Test with:
        python -m pygments -x -l glifpygments.py:GLIFLexer example.txt
"""
from typing import Any

from mmtpygments.mmt_lexer import MMTLexer
from pygments.lexer import RegexLexer, words, bygroups
from pygments.token import Comment, Name, Whitespace, Generic, String, Keyword, Number, Punctuation

from . import commands


class GFLexer(RegexLexer):
    codemirror_name = 'GF'
    rouge_original_source = '...'

    tokens = {
        'root': [
            (r'--.*$', Comment.Single),
            (r'(\s+)', Whitespace),
            (r'(abstract|resource|interface|concrete|instance)(\s+)(\w+)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (words(('incomplete', 'open', 'of', 'in', 'with', 'let', 'case', 'table', 'overload', 'where', 'pre'),
                   suffix=r'\b').get(), Keyword),
            (words(('cat', 'fun', 'lincat', 'lin', 'oper', 'flags', 'param', 'data', 'def', 'lindef', 'linref'),
                   suffix=r'\b').get(), Generic.Heading),
            (words(('Type', 'Int', 'PType', 'Str', 'String'), suffix=r'\b').get(),
             Name.Builtin),
            (r'"([^"]|(\\"))*"', String),
            (r'"(\d+)"', Number.Integer),
            (r'\w+', Name)
        ],
    }


class ELPILexer(RegexLexer):
    codemirror_name = 'ELPI'
    rouge_original_source = '...'

    tokens = {
        'root': [
            (r'%.*$', Comment.Single),
            (r'\/\*.*\*\/', Comment.Multiline),
            (r'([A-Z_]\w*)', Name.Variable),
            (r'(_)', Name.Variable),
            (r'(\s+)', Whitespace),
            (r'(type|kind|accumulate|pi)', Keyword),
            (words(('prop', 'type', 'int', 'fail', 'list', 'string', 'o'), suffix=r'\b').get(),
             Name.Builtin),
            (r'"([^"]|(\\"))*"', String),
            (r'"(\d+)"', Number.Integer),
            (r'\w+', Name)
        ],
    }


class GLIFCommandLexer(RegexLexer):
    codemirror_name = 'GLIFCommand'
    rouge_original_source = '...'

    glifcommands = [name
                    for cmdt in commands.GLIF_COMMAND_TYPES + commands.gf_commands.GF_COMMAND_TYPES
                    for name in cmdt.names]

    tokens = {
        'root': [
            (r'(--|#|\/\/|%).*$', Comment.Single),
            (r'(--|#|\/\/|%).*$', Comment.Single),
            (words(glifcommands, suffix=r'$').get(), Keyword, 'root'),
            (words(glifcommands, suffix=r'\b').get(), Keyword, 'incommand'),
            (r'"([^"]|(\\"))*"$', String, 'root'),
            (r'"([^"]|(\\"))*"', String, 'incommand'),
            # lines starting with a string must still be part of the previous command
            (r'\w+', Generic.Error, 'incommand'),  # unknown command?
        ],
        'incommand': [
            (r'(-\w+)$', bygroups(Name.Attribute), '#pop'),
            (r'(-\w+)', bygroups(Name.Attribute)),
            (r'(-\w+)(=)((?:\w|\d)+)$', bygroups(Name.Attribute, Punctuation, Name.Constant), '#pop'),
            (r'(-\w+)(=)((?:\w|\d)+)', bygroups(Name.Attribute, Punctuation, Name.Constant)),
            (r'(-\w+)(=)("(?:[^"]|(?:\\"))*")$', bygroups(Name.Attribute, Punctuation, String), '#pop'),
            (r'(-\w+)(=)("(?:[^"]|(?:\\"))*")', bygroups(Name.Attribute, Punctuation, String)),
            (r'"([^"]|(\\"))*"$', String, '#pop'),
            (r'"([^"]|(\\"))*"', String),
            (r'\|', Punctuation, '#pop'),
            (r'[ \t]*$', Whitespace, '#pop'),
            (r'\w+$', Name.Constant, '#pop'),
            (r'\w+', Name.Constant),
            (r'[\(\)]$', Punctuation, '#pop'),
            (r'[\(\)]', Punctuation),
            (r'([ \t]+)', Whitespace),
        ]
    }


def import_tokens(target, source, prefix):
    """ imports tokens from source to target with prefix """
    import copy
    for entry in source:
        c = copy.deepcopy(source[entry])
        for i in range(len(c)):
            if len(c[i]) == 3 and not c[i][2].startswith('#'):
                c[i] = (c[i][0], c[i][1], prefix + c[i][2])
        target[prefix + entry] = c


def import_root_ref(target, source, test, prefix):
    """ Copies some elements from source['root'] to target['root'] and references into prefix
        Application: Transitions from GLIF into specific languages
    """
    for e in source['root']:
        if test(e):
            if len(e) == 2:
                target['root'].append((e[0], e[1], prefix + 'root'))
            elif len(e) == 3 and not e[2].startswith('#'):
                target['root'].append((e[0], e[1], prefix + e[2]))
            elif len(e) == 3 and e[2] == '#pop':
                target['root'].append((e[0], e[1], prefix + 'root'))
            else:
                target['root'].append(e)


class GLIFLexer(RegexLexer):
    codemirror_name = 'GLIF'
    rouge_original_source = 'https://github.com/jfschaefer/glifcore'

    tokens = {
        'root': [
            (r'(gf:|GF:)(\s+)(\w+)', bygroups(Generic.Heading, Whitespace, Name.Class), 'gf.root'),
            (r'(mmt:|MMT:)(\s+)(\w+)', bygroups(Generic.Heading, Whitespace, Name.Class), 'mmt.root'),
            (r'(elpi:|ELPI:|elpi-notc:|ELPI-NOTC:)(\s+)(\w+)', bygroups(Generic.Heading, Whitespace, Name.Class),
             'elpi.root'),
        ],
    }

    import_root_ref(tokens, GFLexer.tokens, lambda e: 'abstract' in e[0], 'gf.')

    def mmttest(e: Any):
        if 'theory' in e[0] or 'view' in e[0]:
            return True
        if '❚' in e[0] and e[1] != Generic.Error:
            return True
        return False

    import_root_ref(tokens, MMTLexer.tokens, mmttest, 'mmt.')
    import_root_ref(tokens, ELPILexer.tokens, lambda e: 'accumulate' in e[0], 'elpi.')
    import_root_ref(tokens, GLIFCommandLexer.tokens, lambda e: len(e) == 3 and e[2] in {'incommand', 'root'}, 'cmd.')

    import_tokens(tokens, GFLexer.tokens, 'gf.')
    import_tokens(tokens, MMTLexer.tokens, 'mmt.')
    import_tokens(tokens, ELPILexer.tokens, 'elpi.')
    import_tokens(tokens, GLIFCommandLexer.tokens, 'cmd.')

    tokens['root'] += [
        (r'--.*$', Comment.Single),
        (r'\/\/.*$', Comment.Single),
        (r'%.*$', Comment.Single),
        (r'\/\*.*\*\/', Comment.Multiline),
        (r'\w+', Generic.Error),
    ]
