from math_utils import divide


def test_main():
    assert divide(4, 0) is None

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
