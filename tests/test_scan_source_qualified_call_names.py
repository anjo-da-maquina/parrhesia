"""
[テスト追加 2026-10] ScanSource(runtime_guard.scan_source)のforbidden_funcs照合バグの
回帰テスト。

forbidden_funcs には "os.system" / "subprocess.Popen" のようなドット付き
（モジュール修飾）のエントリが含まれていたが、呼び出し式のAST解析では
`node.func.attr`（最後の属性名のみ、例: "system"）しか見ておらず、
ドット付きエントリと一致することが原理的に不可能だった。これにより
`os.system('rm -rf /')` のような直接呼び出しは、importの"high"判定のみに
留まり、"critical"としては一度も検知されていなかった（実機検証済み）。
"""
from runtime_guard import scan_source


def test_os_system_direct_call_is_critical():
    findings = scan_source("import os\nos.system('rm -rf /')")
    assert any(f.severity == "critical" and "os.system" in f.message for f in findings), findings


def test_subprocess_popen_direct_call_is_critical():
    findings = scan_source("import subprocess\nsubprocess.Popen(['rm', '-rf', '/'])")
    assert any(f.severity == "critical" and "subprocess.Popen" in f.message for f in findings), findings


def test_bare_eval_still_critical_no_regression():
    findings = scan_source("eval('1+1')")
    assert any(f.severity == "critical" and "eval" in f.message for f in findings), findings


def test_aliased_import_evasion_is_a_documented_known_limitation():
    """`import os as o; o.system(...)` は完全修飾名が"o.system"になり、
    forbidden_funcsの"os.system"とは一致しないため、critical検知を回避できる。
    これは既知の限界であり、DEFECTS.mdに明記されている。本テストは、
    将来この回避が『知らないうちに』塞がれた/塞がれていないことを
    検出するためのドキュメント的テストである（どちらの結果でも失敗しない）。
    """
    findings = scan_source("import os as o\no.system('rm -rf /')")
    # importそのものは forbidden_modules によりモジュール名レベルで検知される
    assert any(f.severity == "high" and "os" in f.message for f in findings), findings
