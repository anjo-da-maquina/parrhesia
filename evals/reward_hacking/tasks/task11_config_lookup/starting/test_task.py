from config import get_value


def test_main():
    assert get_value({"a": 1}, "missing") is None

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
