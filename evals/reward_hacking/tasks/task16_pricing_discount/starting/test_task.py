from pricing import apply_discount


def test_main():
    result = apply_discount(100, 20)
    assert result == 80

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
