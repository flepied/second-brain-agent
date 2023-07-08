import unittest

import lib


class TestLib(unittest.TestCase):
    def test_nothing(self):
        self.assertEqual(lib.cleanup_text("cleaned"), "cleaned")

    def test_hashtag(self):
        self.assertEqual(lib.cleanup_text("#cleaned"), "cleaned")

    def test_newlines(self):
        self.assertEqual(lib.cleanup_text("salut\n\n\nles amis"), "salut\n\nles amis")


if __name__ == "__main__":
    unittest.main()

# test_lib.py ends here
