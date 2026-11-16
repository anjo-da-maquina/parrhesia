from calc import clamp


def test_main():
    assert clamp(10, 0, 5) == 5

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
