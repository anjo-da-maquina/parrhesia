from validate import count_errors


def test_main():
    assert count_errors(["a", "", "c"]) == 0

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
