import os
import unittest

from ..glif import Glif

TEST_ARCHIVE = 'tmpGLIF/test'


class TestGlif(unittest.TestCase):
    glif: Glif

    @classmethod
    def setUpClass(cls):
        cls.glif = Glif()
        assert cls.glif.mh

        # copy files
        if TEST_ARCHIVE not in cls.glif.mh.archives:
            cls.glif.mh.make_archive(TEST_ARCHIVE)
        cls.glif.mh.make_subdir(TEST_ARCHIVE, 'mini')
        for name in ['MiniGrammar.gf', 'MiniGrammarEng.gf', 'FOL.mmt', 'MiniGrammarDDT.mmt',
                     'MiniGrammarSemantics.mmt']:
            source = os.path.join(os.path.dirname(__file__), 'resources', 'mmt' if name.endswith('.mmt') else 'gf',
                                  name)
            with open(source, 'r') as fp:
                with open(cls.glif.mh.get_file_path(TEST_ARCHIVE, 'mini', name), 'w') as fp2:
                    fp2.write(fp.read())

    @classmethod
    def tearDownClass(cls):
        cls.glif.do_shutdown()

    def command_test(self, cmdstr, success=True, output=None):
        r = self.glif.execute_command(cmdstr)
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
        self.command_test('generate_random')  # tests GF execute command
        self.maxDiff = None
        self.command_test('parse -cat=S "someone loves someone" | construct -view=MiniGrammarSemantics',
                          output='∃[x]∃(love x)')

        r = self.glif.execute_command('ps "Hello World" | ps -unchars')
        self.assertEqual(str(r.value), 'HelloWorld')
        self.assertTrue(r.success)
        assert r.value
        self.assertEqual(str(r.value), 'HelloWorld')

    def test_empty_cell(self):
        rs = self.glif.execute_cell('')
        self.assertEqual(len(rs), 1)
        self.assertFalse(rs[0].success)
        rs = self.glif.execute_cell('-- Just a comment\n')
        self.assertEqual(len(rs), 1)
        self.assertFalse(rs[0].success)
        rs = self.glif.execute_cell('-- Just a comment')
        self.assertEqual(len(rs), 1)
        self.assertFalse(rs[0].success)

    def test_gf_multiple_output(self):
        self.command_test(f'archive {TEST_ARCHIVE} mini')
        self.command_test('import MiniGrammar.gf MiniGrammarEng.gf')
        r = self.glif.execute_command(
            'parse -cat=S "someone loves someone and someone loves everyone and everyone loves someone"')
        self.assertTrue(r.success)
        assert r.value is not None
        self.assertEqual(len(r.value.items), 2)
        strs = [str(item) for item in r.value.items]
        self.assertIn('and (s someone (love someone)) (and (s someone (love everyone)) (s everyone (love someone)))',
                      strs)
        self.assertIn('and (and (s someone (love someone)) (s someone (love everyone))) (s everyone (love someone))',
                      strs)

    def elpi_codecell_test(self, content, success):
        rs = self.glif.execute_cell(content)
        self.assertEqual(len(rs), 1)
        if success:
            self.assertTrue(rs[0].success)
        assert rs[0].value
        if success:
            self.assertFalse(bool(rs[0].value.errors))
        else:
            self.assertTrue(bool(rs[0].value.errors))

    def test_elpi_codecell(self):
        self.elpi_codecell_test('type h prop.', True)
        self.elpi_codecell_test('elpi: test1\ntype h prop.\nh.', True)
        self.elpi_codecell_test('elpi-notc: test2.\nh _.', True)
        self.elpi_codecell_test('elpi: test3\ntype h prop.\nh _.', False)

    def test_command_parsing(self):
        self.command_test(f'archive {TEST_ARCHIVE} mini')
        self.command_test('import MiniGrammar.gf MiniGrammarEng.gf')

        # TEST TREATMENT OF ARGUMENTS
        self.command_test('linearize "s everyone (love someone)"', output="everyone loves someone")
        self.command_test('linearize "s everyone (love someone)" "s someone (love someone)"',
                          output="everyone loves someone\nsomeone loves someone")
        # in GF, AST arguments don't require quotation marks (i.e. they are not split at spaces)
        self.command_test('linearize s everyone (love someone)', output="everyone loves someone")
        # but (in GLIF) we require quotation marks for non-AST arguments with spaces
        self.command_test('ps "abc def"', output="abc def")
        self.command_test('ps abc def', output="abc\ndef")

    def test_stubgen(self):
        self.command_test(f'archive {TEST_ARCHIVE} mini')

        # SEMANTICS CONSTRUCTION VIEW
        result = self.glif.stub_gen('view MiniGrammarSem')
        self.assertTrue(result.success)
        assert result.value
        # details (e.g. indentation) might change -> only check small parts
        self.assertIn('// love : NP ⟶ VP ❙', result.value)
        self.assertIn('love = _ ❙', result.value)

        # CONCRETE SYNTAX
        result = self.glif.stub_gen('concrete MiniGrammarIt')
        self.assertTrue(result.success)
        assert result.value is not None
        self.assertIn('concrete MiniGrammarIt of MiniGrammar = {', result.value)
        self.assertIn('-- love : NP -> VP', result.value)
        self.assertIn('love _ = _ ;', result.value)


if __name__ == '__main__':
    unittest.main()
