import unittest
from glif import parsing
from glif import glif
from glif import commands
from glif import utils


class TestBasicParsing(unittest.TestCase):
    def test_parse_argument(self):
        def test(s,k,v,v2):
            pr = parsing.parseCommandArg(s)
            if not pr.success:
                print(pr.logs)
            self.assertTrue(pr.success)
            expected = parsing.CommandArgument(key=k, value=v, stringvalue=v2)
            self.assertEqual(pr.value[0], expected)
        test('-lang=Eng "test"', 'lang', 'Eng', '')
        test('-lang=Eng', 'lang', 'Eng', '')
        test('-val="test"', 'val', '', 'test')
        test('-val=""', 'val', '', '')
        test('-val="te st\\\\" " "', 'val', '', 'te st\\')
        test('-val="test\\""', 'val', '', 'test"')
        test('-level=3', 'level', '3', '')
        test('-simple', 'simple', '', '')
        test('-simple "test"', 'simple', '', '')

class TestCommandParsing(unittest.TestCase):
    fakeGetInput = lambda item: utils.Result(True, '')
    fakeGetOutput = lambda item, s: commands.Items([])
    parseCT = commands.GfCommandType(['parse', 'p'], fakeGetInput, fakeGetOutput)

    def parseCTtest(self, cmdStr: str, success: bool = True, remainder: str = '', isApplicable: bool = False):
        cmd = self.parseCT.fromString(cmdStr)
        if success:
            self.assertTrue(cmd.success)
            assert cmd.value
            self.assertEqual(cmd.value[1].strip(), remainder)
            if isApplicable:
                self.assertTrue(cmd.value[0].is_applicable)
            else:
                self.assertFalse(cmd.value[0].is_applicable)
        else:
            self.assertFalse(cmd.success)

    def test_basic(self):
        self.parseCTtest('parse -lang=Eng "hello world"')
        self.parseCTtest('p -lang=Eng "hello world"')
        self.parseCTtest('parse -lang=Eng', isApplicable=True)
        self.parseCTtest('parse -lang=Eng "hello world" | l -lang=Ger', remainder='l -lang=Ger')
        self.parseCTtest('parse "hello world"')
        self.parseCTtest('parse', isApplicable=True)
        # these should be linearize:
        self.parseCTtest('parse -lang=Eng hello')
        self.parseCTtest('parse -lang=Eng exclaim (hello world)')

    def test_incomplete(self):
        self.parseCTtest('parse -lang=', success=False)
        self.parseCTtest('parse -lang=Eng "hello world', success=False)
        self.parseCTtest('parse -', success=False)

    def test_args(self):
        self.parseCTtest('parse -arg="value"', isApplicable=True)
        self.parseCTtest('parse -bracket', isApplicable=True)
        self.parseCTtest('parse -depth=3', isApplicable=True)

    def test_escape(self):
        self.parseCTtest('parse "\\""', success=True)
        self.parseCTtest('parse "\\"', success=False)
        self.parseCTtest('parse "\\\\"', success=True)
        self.parseCTtest('parse "|" | l', success=True, remainder='l')

    def test_space(self):
        self.parseCTtest('parse    -lang=Eng    "hello world"   | l -lang=Ger', remainder='l -lang=Ger')
        self.parseCTtest('parse -lang=Eng "hello world"| l -lang=Ger', remainder='l -lang=Ger')



if __name__ == '__main__':
    unittest.main()
