from glif import glif
import unittest


TEST_ARCHIVE = 'tmpGLIF/test'

class TestMMT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glif = glif.Glif()

    @classmethod
    def tearDownClass(cls):
        cls.glif.do_shutdown()

    def test_basic(self):
        r = self.glif.executeCommand('ps "Hello World" | ps -unchars')
        self.assertTrue(r.success)
        assert r.value
        self.assertEqual(str(r.value), 'HelloWorld')

if __name__ == '__main__':
    unittest.main()
