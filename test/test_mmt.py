import unittest
import os
import shutil

from glif import mmt
from glif import utils

# TODO: Use unittest.mock to overwrite `os.getenv` to simulate missing MMT installation (https://realpython.com/python-mock-library/)

TEST_ARCHIVE = 'tmpGLIF/test'

class TestMMT(unittest.TestCase):
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
        r = cls.mh.makeArchive(TEST_ARCHIVE)
        assert r.success
        cls.testarchivedir = r.value
        cls.mmt = mmt.MMTInterface(mmtjar.value, cls.mh)


    @classmethod
    def tearDownClass(cls):
        cls.mmt.server.do_shutdown()

    def test_simple_build(self):
        self.mh.makeSubdir(TEST_ARCHIVE, 'testSimpleBuild')
        with open(self.mh.getFilePath(TEST_ARCHIVE, 'testSimpleBuild', 'Test.gf'), 'w') as fp:
            fp.write('abstract Test = { cat A; fun f : A -> A; x : A; }')
        r1 = self.mmt.buildFile(TEST_ARCHIVE, 'testSimpleBuild', 'Test.gf')
        print(r1.logs)
        self.assertTrue(r1.success)
        r2 = self.mmt.buildFile(TEST_ARCHIVE, 'testSimpleBuild', 'NonExistent.gf')
        self.assertFalse(r2.success)


if __name__ == '__main__':
    unittest.main()
