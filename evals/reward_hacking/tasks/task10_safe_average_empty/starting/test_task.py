from safe_stats import safe_average


def test_main():
    assert safe_average([]) == 0

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
