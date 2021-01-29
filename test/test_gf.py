import unittest
import os
from distutils.spawn import find_executable

from glif import gf

class TestShellIO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gfshell = gf.GFShellRaw(
                find_executable('gf'),
                cwd = os.path.dirname(__file__),
                )

    @classmethod
    def tearDownClass(cls):
        cls.gfshell.do_shutdown()

    def setUp(self):
        self.checkio('empty', '')    # empty environment

    def checkio(self, in_, out):
        self.assertEqual(self.gfshell.handle_command(in_), out)

    def test_basic_io(self):
        self.checkio('ps "Hello world"', 'Hello world')

    def test_unicode(self):
        # test ascii, 8-bit unicode, 16-bit unicode and 24-bit unicode
        for c in ["A", "Ä", "ᴬ", "𝔸"]:
            self.checkio(f'ps "{c}"', c)
        # combined
        self.checkio(f'ps "AÄᴬ𝔸 end"', "AÄᴬ𝔸 end")

    def test_multiline(self):
        self.checkio('import resources/gf/MiniGrammarEng.gf', '')
        result = self.gfshell.handle_command('generate_trees -depth=2').splitlines()
        self.assertEqual(len(result), 8)
        self.assertEqual(len(set(result)), 8)
        self.assertIn('s someone (love someone)', result)


if __name__ == '__main__':
    unittest.main()
