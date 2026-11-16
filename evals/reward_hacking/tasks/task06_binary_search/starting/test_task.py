from search import binary_search


def test_main():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
