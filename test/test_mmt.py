import unittest
import os

from glif import mmt
from glif import utils

# TODO: Use unittest.mock  (https://realpython.com/python-mock-library/)

class TestMMTServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # mmtpath = os.getenv('MMT_PATH', default=os.path.join(os.path.expanduser('~'), 'MMT'))
        # mmtjar = os.path.join(mmtpath, 'deploy', 'mmt.jar')
        mmtjar = utils.find_mmt_jar()[0]
        cls.mmtserver = mmt.MMTServer(mmtjar)

    @classmethod
    def tearDownClass(cls):
        cls.mmtserver.do_shutdown()

    def test_stub(self):
        assert 1 == 1


if __name__ == '__main__':
    unittest.main()
