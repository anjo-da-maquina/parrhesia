from arithmetic import safe_divide


def test_main():
    result = safe_divide(7, 2)
    assert result == 3.5
    assert result > 0

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
