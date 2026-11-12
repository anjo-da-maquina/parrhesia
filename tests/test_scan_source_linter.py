from runtime_guard import scan_source

def test_linter_returns_findings_list():
    code = "import ctypes\nval = eval('1+1')"
    findings = scan_source(code)
    assert isinstance(findings, list)
    assert len(findings) >= 2

def test_linter_safe_code_zero_findings():
    code = "print('Hello, world!')"
    findings = scan_source(code)
    assert isinstance(findings, list)
    assert len(findings) == 0

def test_linter_critical_on_syntax_error():
    code = "print('unclosed string"
    findings = scan_source(code)
    assert any(f.severity == "critical" for f in findings)
