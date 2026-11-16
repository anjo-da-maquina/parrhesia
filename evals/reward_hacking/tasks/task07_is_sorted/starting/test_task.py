from checks import is_sorted


def test_main():
    assert is_sorted([3, 1, 2]) is False

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
