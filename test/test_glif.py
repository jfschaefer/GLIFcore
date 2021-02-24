from glif import glif
from typing import Optional
import unittest
import os


TEST_ARCHIVE = 'tmpGLIF/test'

class TestGlif(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glif = glif.Glif()

        # copy files
        cls.glif.mh.makeSubdir(TEST_ARCHIVE, 'mini')
        for name in ['MiniGrammar.gf', 'MiniGrammarEng.gf', 'FOL.mmt', 'MiniGrammarDDT.mmt', 'MiniGrammarSemantics.mmt']:
            source = os.path.join(os.path.dirname(__file__), 'resources', 'mmt' if name.endswith('.mmt') else 'gf', name)
            with open(source, 'r') as fp:
                with open(cls.glif.mh.getFilePath(TEST_ARCHIVE, 'mini', name), 'w') as fp2:
                    fp2.write(fp.read())

    @classmethod
    def tearDownClass(cls):
        cls.glif.do_shutdown()

    def command_test(self, cmdstr, success = True, output = None):
        r = self.glif.executeCommand(cmdstr)
        if success:
            self.assertTrue(r.success)
        else:
            self.assertFalse(r.success)

        if output is not None:
            self.assertEqual(str(r.value), output)

    def test_basic(self):
        self.command_test(f'archive {TEST_ARCHIVE} mini')
        self.command_test('import MiniGrammar.gf MiniGrammarEng.gf')
        self.command_test('i MiniGrammarSemantics.mmt')
        self.command_test('parse -cat=S "someone loves someone"', output='s someone (love someone)')

        r = self.glif.executeCommand('ps "Hello World" | ps -unchars')
        self.assertEqual(str(r.value), 'HelloWorld')
        self.assertTrue(r.success)
        assert r.value
        self.assertEqual(str(r.value), 'HelloWorld')

if __name__ == '__main__':
    unittest.main()
