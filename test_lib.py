import unittest

import lib


class TestLib(unittest.TestCase):
    def test_nothing(self):
        self.assertEqual(lib.cleanup_text("cleaned"), "cleaned")

    def test_stop_words_en(self):
        self.assertEqual(lib.cleanup_text("hello the friends"), "hello friends")

    def test_stop_words_fr(self):
        self.assertEqual(lib.cleanup_text("Salut les. amis!"), "salut . amis!")

    def test_hashtag(self):
        self.assertEqual(lib.cleanup_text("#cleaned"), "cleaned")

    def test_newlines(self):
        self.assertEqual(lib.cleanup_text("salut\n\n\nles amis"), "salut\n amis")

    def test_load_all_langs(self):
        lib.init(lib.SUPPORTED_LANGUAGES.keys())


if __name__ == "__main__":
    lib.init(["en", "fr"])
    unittest.main()

# test_lib.py ends here
