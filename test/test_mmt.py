import unittest
import os

from glif import mmt
from glif import utils

# TODO: Use unittest.mock to overwrite `os.getenv` to simulate missing MMT installation (https://realpython.com/python-mock-library/)


class TestMMTServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mmtjar = utils.find_mmt_jar()[0]
        mathhub = utils.find_mathhub_dir(mmtjar)[0]
        cls.mmt = mmt.MMTInterface(mmtjar, mathhub)

    @classmethod
    def tearDownClass(cls):
        cls.mmt.server.do_shutdown()

    def test_stub(self):
        assert 1 == 1


if __name__ == '__main__':
    unittest.main()
