import unittest
from glif import parsing
from glif import glif
from glif import commands
from glif import utils


class TestBasicParsing(unittest.TestCase):
    def test_parse_argument(self):
        def test(s,k,v):
            pr = parsing.parseCommandArg(s)
            if not pr.success:
                print(pr.logs)
            self.assertTrue(pr.success)
            expected = parsing.CommandArgument(key=k, value=v)
            self.assertEqual(pr.value[0], expected)
        test('-lang=Eng "test"', 'lang', 'Eng')
        test('-lang=Eng', 'lang', 'Eng')
        test('-val="test"', 'val', 'test')
        test('-val=""', 'val', '')
        test('-val="te st\\\\" " "', 'val', 'te st\\')
        test('-val="test\\""', 'val', 'test"')
        test('-level=3', 'level', '3')
        test('-simple', 'simple', '')
        test('-simple "test"', 'simple', '')

class TestCommandParsing(unittest.TestCase):
    def parseBCtest(self, cmdStr: str, cmdname: str = '', args: list[tuple[str,str]] = [], mainargs: list[str] = [], success: bool = True, remainder: str = ''):
        cmd = parsing.parseBasicCommand(cmdStr)
        if success:
            self.assertTrue(cmd.success)
            assert cmd.value
            self.assertEqual(cmd.value[1].strip(), remainder)
            self.assertEqual(len(cmd.value[0].args), len(args))
            for (a,b) in zip(args, cmd.value[0].args):
                self.assertEqual(a[0], b.key)
                self.assertEqual(a[1], b.value)
            self.assertEqual(len(cmd.value[0].mainargs), len(mainargs))
            for (x,y) in zip(mainargs, cmd.value[0].mainargs):
                self.assertEqual(x, y)
        else:
            self.assertFalse(cmd.success)

    def test_basic(self):
        self.parseBCtest('parse -lang=Eng "hello world"', 'parse', [('lang', 'Eng')], ['hello world'])
        self.parseBCtest('parse -lang=Eng -cat=S', 'parse', [('lang', 'Eng'), ('cat', 'S')])
        self.parseBCtest('parse -lang=Eng "hello world" | l -lang=Ger', 'parse', [('lang', 'Eng')], ['hello world'], remainder='l -lang=Ger')
        self.parseBCtest('parse "hello world"', 'parse', [], ['hello world'])
        self.parseBCtest('parse', 'parse')
        self.parseBCtest('l -lang=Eng hello', 'l', [('lang','Eng')], ['hello'])
        self.parseBCtest('l -lang=Eng exclaim (hello world)', 'l', [('lang','Eng')], ['exclaim (hello world)'])

    def test_incomplete(self):
        self.parseBCtest('parse -lang=', success=False)
        self.parseBCtest('parse -lang=Eng "hello world', success=False)
        self.parseBCtest('parse -', success=False)

    def test_args(self):
        self.parseBCtest('c -arg="value"', 'c', [('arg', 'value')])
        self.parseBCtest('c -bracket', 'c', [('bracket', '')])
        self.parseBCtest('c -depth=3', 'c', [('depth', '3')])

    def test_escape(self):
        self.parseBCtest('parse "\\""', 'parse', [], ['"'])
        self.parseBCtest('parse "\\"', success=False)
        self.parseBCtest('parse "\\\\"', 'parse', [], ['\\'])
        self.parseBCtest('parse "|" | l', 'parse', [], ['|'], remainder='l')

    def test_space(self):
        self.parseBCtest('parse    -lang=Eng    "hello world"   | l -lang=Ger', 'parse', [('lang', 'Eng')], ['hello world'], remainder='l -lang=Ger')
        self.parseBCtest('parse -lang=Eng "hello world"| l -lang=Ger', 'parse', [('lang', 'Eng')], ['hello world'], remainder='l -lang=Ger')

    def test_mainargs(self):
        self.parseBCtest('parse "hello" "world"', 'parse', [], ['hello', 'world'])


class TestFileIdentification(unittest.TestCase):
    def idTest(self, content: str, expected: utils.Result[tuple[str,str]]):
        r = parsing.identifyFile(content)
        if expected.success:
            self.assertTrue(r.success)
            assert r.value
            self.assertEqual(r.value[0:2], expected.value)
        else:
            self.assertFalse(r.success)

    def test_basic(self):
        self.idTest('abstract Grammar = { cat T; }', utils.Result(True, ('gf-abstract', 'Grammar')))
        self.idTest('concrete GrammarEng of Grammar = { lin T = Str; }', utils.Result(True, ('gf-concrete', 'GrammarEng')))
        self.idTest('theory DDT : ur:?LF = ❚', utils.Result(True, ('mmt-theory', 'DDT')))
        self.idTest('view V : ?A -> ?B = ❚', utils.Result(True, ('mmt-view', 'V')))
        self.idTest('parse "Hello world"', utils.Result(False))
        self.idTest('-- The abstract syntax\nabstract Grammar = { cat T; }', utils.Result(True, ('gf-abstract', 'Grammar')))
        self.idTest('// Example MMT theory ❚  theory DDT : ur:?LF = ❚', utils.Result(True, ('mmt-theory', 'DDT')))


if __name__ == '__main__':
    unittest.main()

