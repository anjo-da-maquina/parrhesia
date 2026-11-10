import pytest

@pytest.mark.xfail(reason="DockerSandbox implementation is pending", strict=True)
def test_docker_sandbox_isolation():
    """
    TODO: 物理隔離層（DockerSandbox）の実装に合わせて修正する。
    未実装時は確実な失敗（XFAIL）として可視化する。
    """
    from runtime_guard.sandbox import DockerSandbox
    sandbox = DockerSandbox()
    assert sandbox.is_isolated() is True