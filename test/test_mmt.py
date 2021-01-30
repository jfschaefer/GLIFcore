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
        cls.mmt = mmt.MMTInterface(mmtjar.value, cls.mh)
        r = cls.mh.makeArchive(TEST_ARCHIVE)
        assert r.success
        cls.testarchivedir = r.value


    @classmethod
    def tearDownClass(cls):
        cls.mmt.server.do_shutdown()

    def test_stub(self):
        assert 1 == 1


if __name__ == '__main__':
    unittest.main()
