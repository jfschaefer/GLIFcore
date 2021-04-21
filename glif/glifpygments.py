'''
    Pygments-based syntax highlighting for GLIF.
    Requires (correct) version of mmtpygments.
    The code is very experimental and fragile.
    Not all pygments features can be used because a CodeMirror highlighter is automatically
    generated from the lexers.

'''

from pygments.lexer import RegexLexer, using, words, bygroups
from pygments.token import Comment, Name, Whitespace, Generic, String, Keyword

from mmtpygments.mmt_lexer import MMTLexer


class GFLexer(RegexLexer):
    codemirror_name = 'GF'
    rouge_original_source = '...'

    tokens = {
        'root': [
            (r'--.*$', Comment.Single),
            (r'(\s+)', Whitespace),
            (r'(abstract|resource|interface|concrete|instance)(\s+)(\w+)',
                bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (words(('incomplete', 'open', 'of', 'in', 'with', 'let', 'case', 'table', 'overload'), suffix=r'\b').get(),
                Keyword),
            (words(('cat', 'fun', 'lincat', 'lin', 'oper', 'flags', 'param', 'data', 'def', 'lindef', 'linref'), suffix=r'\b').get(),
                Generic.Heading),
            (r'"([^"]|(\\"))*"', String),
            (r'\w+', Name)
        ],
    }

def importTokens(target, source, prefix):
    ''' imports tokens from source to target with prefix '''
    import copy
    for entry in source:
        c = copy.deepcopy(source[entry])
        for i in range(len(c)):
            if len(c[i]) == 3 and not c[i][2].startswith('#'):
                c[i] = (c[i][0], c[i][1], prefix + c[i][2])
        target[prefix+entry] = c

def importRootRef(target, source, test, prefix):
    ''' Copies some elements from source['root'] to target['root'] and references into prefix
        Application: Transitions from GLIF into specific languages
    '''
    for e in source['root']:
        if test(e):
            if len(e) == 2:
                target['root'].append((e[0], e[1], prefix+'root'))
            elif len(e) == 3 and not e[2].startswith('#'):
                target['root'].append((e[0], e[1], prefix+e[2]))   # problem: pops back to root, not prefix.root
            else:
                target['root'].append(e)


class GLIFLexer(RegexLexer):
    codemirror_name = 'GLIF'
    rouge_original_source = 'https://github.com/jfschaefer/glifcore'

    tokens = {
        'root': [
        ],
    }

    importRootRef(tokens, GFLexer.tokens, lambda e : 'abstract' in e[0], 'gf.')
    def mmttest(e):
        if 'theory' in e[0] or 'view' in e[0]:
            return True
        if '❚' in e[0] and e[1] != Generic.Error:
            return True
        return False
    importRootRef(tokens, MMTLexer.tokens, mmttest, 'mmt.')

    importTokens(tokens, GFLexer.tokens, 'gf.')
    importTokens(tokens, MMTLexer.tokens, 'mmt.')

    tokens['root'] += [
            (r'--.*$', Comment.Single),
            (r'\/\/.*$', Comment.Single),
            (r'\w+', Generic.Error),
        ]


