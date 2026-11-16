from intervals import merge_intervals


def test_main():
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
