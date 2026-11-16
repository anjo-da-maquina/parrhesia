from text_utils import is_palindrome


def test_main():
    assert is_palindrome("Racecar") is True

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
