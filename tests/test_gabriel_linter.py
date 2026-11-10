from runtime_guard import inquisition

def test_linter_returns_findings_list():
    code = "import ctypes\nval = eval('1+1')"
    findings = inquisition(code)
    assert isinstance(findings, list)
    assert len(findings) >= 2

def test_linter_safe_code_zero_findings():
    code = "print('Hello, world!')"
    findings = inquisition(code)
    assert isinstance(findings, list)
    assert len(findings) == 0

def test_linter_critical_on_syntax_error():
    code = "print('unclosed string"
    findings = inquisition(code)
    assert any(f.severity == "critical" for f in findings)
