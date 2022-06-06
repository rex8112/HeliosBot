import unittest
import os
from os.path import exists
from helios.tools import Config


class ConfigTestCase(unittest.TestCase):
    testing_file_path = 'test_config.json'

    def test_no_file(self):
        try:
            c = Config.from_file_path(ConfigTestCase.testing_file_path)
            self.assertTrue(exists(ConfigTestCase.testing_file_path))
        except Exception:
            raise
        finally:
            os.remove(ConfigTestCase.testing_file_path)

    def test_save(self):
        try:
            c = Config.from_file_path(ConfigTestCase.testing_file_path)
            c.token = 'Testing Token'
            c.save()
            self.assertEqual(c.token, 'Testing Token')
        except Exception:
            raise
        finally:
            os.remove(ConfigTestCase.testing_file_path)

    def test_save_load(self):
        try:
            c = Config.from_file_path(ConfigTestCase.testing_file_path)
            c.token = 'Testing Token'
            c.save()
            c2 = Config.from_file_path(ConfigTestCase.testing_file_path)
            self.assertEqual(c.token, c2.token)
        except Exception:
            raise
        finally:
            os.remove(ConfigTestCase.testing_file_path)


if __name__ == '__main__':
    unittest.main()
