import unittest
import os
import shutil

from glif import mmt
from glif import utils

# TODO: Use unittest.mock to overwrite `os.getenv` to simulate missing MMT installation
# (https://realpython.com/python-mock-library/)

TEST_ARCHIVE = 'tmpGLIF/test'


class TestMMT(unittest.TestCase):
    mh: mmt.MathHub
    mmt: mmt.MMTInterface

    @classmethod
    def setUpClass(cls):
        mmtjar = utils.find_mmt_jar()
        assert mmtjar.success
        mhdir = utils.find_mathhub_dir(mmtjar.value)
        assert mhdir.success
        tmp = os.path.join(mhdir.value, TEST_ARCHIVE.split('/')[0])
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        cls.mh = mmt.MathHub(mhdir.value)
        r = cls.mh.make_archive(TEST_ARCHIVE)
        assert r.success
        cls.testarchivedir = r.value
        cls.mmt = mmt.MMTInterface(mmtjar.value, cls.mh)

    @classmethod
    def tearDownClass(cls):
        cls.mmt.server.do_shutdown()

    def build(self, archive, subdir, filename, content):
        with open(self.mh.get_file_path(archive, subdir, filename), 'w') as fp:
            fp.write(content)
        r = self.mmt.build_file(archive, subdir, filename)
        self.assertTrue(r.success)

    def test_simple_build(self):
        self.mh.make_subdir(TEST_ARCHIVE, 'testSimpleBuild')
        self.build(TEST_ARCHIVE, 'testSimpleBuild', 'Test.gf', 'abstract Test = { cat A; fun f : A -> A; x : A; }')
        self.build(TEST_ARCHIVE, 'testSimpleBuild', 'testSimpleBuild.mmt',
                   'theory testSimpleBuild : ur:?LF = t : type ❙ ❚')

        r = self.mmt.build_file(TEST_ARCHIVE, 'testSimpleBuild', 'NonExistent.gf')
        self.assertFalse(r.success)

    def test_build_typeerror(self):
        self.mh.make_subdir(TEST_ARCHIVE, 'testFailedBuild')
        with open(self.mh.get_file_path(TEST_ARCHIVE, 'testFailedBuild', 'bad.mmt'), 'w') as fp:
            fp.write('theory bad : ur:?LF = s : a ⟶ b ❙ ❚')
        r = self.mmt.build_file(TEST_ARCHIVE, 'testFailedBuild', 'bad.mmt')
        self.assertTrue('unbound token: a' in r.logs)
        self.assertFalse(r.success)

    def copyandbuild(self, source, archive, subdir, filename):
        with open(source, 'r') as fp:
            self.build(archive, subdir, filename, fp.read())

    def test_mini_construct(self):
        self.mh.make_subdir(TEST_ARCHIVE, 'mini')
        for name in ['MiniGrammar.gf', 'FOL.mmt', 'MiniGrammarDDT.mmt', 'MiniGrammarSemantics.mmt']:
            self.copyandbuild(
                os.path.join(os.path.dirname(__file__), 'resources', 'mmt' if name.endswith('.mmt') else 'gf', name),
                TEST_ARCHIVE, 'mini', name)
        result = self.mmt.construct(['s everyone (love someone)', 's someone (love someone)'],
                                    TEST_ARCHIVE, 'mini', 'MiniGrammarSemantics', delta_expand=False)
        self.assertTrue(result.success)
        self.assertEqual(len(result.value['mmt']), 2)
        self.assertEqual(len(result.value['elpi']), 2)
        self.assertEqual(result.value['mmt'][0], '∀[x]∃(love x)')
        self.assertEqual(result.value['elpi'][0], '(forall (X/x \\ exists (love X/x)))')

        # Test delta expansion
        result = self.mmt.construct(['s everyone (love someone)'],
                                    TEST_ARCHIVE, 'mini', 'MiniGrammarSemantics', delta_expand=True)
        self.assertTrue(result.success)
        self.assertEqual(result.value['mmt'][0], '∀[x]¬∀[x/r]¬(love x x/r)')

    def test_elpigen_types(self):
        self.mh.make_subdir(TEST_ARCHIVE, 'mini')
        self.copyandbuild(os.path.join(os.path.dirname(__file__), 'resources', 'mmt', 'FOL.mmt'), TEST_ARCHIVE, 'mini',
                          'FOL.mmt')
        result = self.mmt.elpigen('types', TEST_ARCHIVE, 'mini', 'FOL')
        self.assertTrue(result.success)
        self.assertTrue('type forall (ind -> prop) -> prop.' in result.value)


if __name__ == '__main__':
    unittest.main()
