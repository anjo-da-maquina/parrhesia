from network_client import status_code_ok


def test_main():
    assert status_code_ok(404) is False

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
