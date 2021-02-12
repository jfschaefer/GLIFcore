import unittest
from glif import parsing


class TestParsing(unittest.TestCase):
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



if __name__ == '__main__':
    unittest.main()
