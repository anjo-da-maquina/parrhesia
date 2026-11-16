from stats import average


def test_main():
    assert average([2, 4, 6]) == 4

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
