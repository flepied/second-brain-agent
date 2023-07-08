import unittest

import lib


class TestLib(unittest.TestCase):
    def test_nothing(self):
        self.assertEqual(lib.cleanup_text("cleaned"), "cleaned")

    def test_hashtag(self):
        self.assertEqual(lib.cleanup_text("#cleaned"), "cleaned")

    def test_newlines(self):
        self.assertEqual(lib.cleanup_text("salut\n\n\nles amis"), "salut\n\nles amis")

    def test_https(self):
        self.assertEqual(lib.cleanup_text("https://doc.distributed-ci.io/"), "")

    def test_spaces(self):
        self.assertEqual(lib.cleanup_text("\n     \n"), "\n\n")


if __name__ == "__main__":
    unittest.main()

# test_lib.py ends here
