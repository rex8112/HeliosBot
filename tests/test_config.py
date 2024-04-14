#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

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
