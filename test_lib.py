import pytest

import lib


@pytest.mark.unit
class TestLib:
    """Unit tests for lib module functions.

    These tests can run without external dependencies and are marked as unit tests.
    They will run during pre-commit hooks and can be run with: pytest -m unit
    """

    def test_nothing(self):
        assert lib.cleanup_text("cleaned") == "cleaned"

    def test_hashtag(self):
        assert lib.cleanup_text("#cleaned") == "cleaned"

    def test_newlines(self):
        assert lib.cleanup_text("salut\n\n\nles amis") == "salut\n\nles amis"

    def test_https(self):
        assert lib.cleanup_text("https://doc.distributed-ci.io/") == ""

    def test_spaces(self):
        assert lib.cleanup_text("\n     \n") == "\n\n"
