#!/usr/bin/env bash
# read-only repo audit (no network, no writes). Run from repo root.
# RUN_TESTS=1 でテストも実行(必ずコンテナ/サンドボックス内で)。
set -u
P=0; F=0; W=0
ok(){ echo "[PASS] $*"; P=$((P+1)); }
ng(){ echo "[FAIL] $*"; F=$((F+1)); }
wn(){ echo "[WARN] $*"; W=$((W+1)); }
[ -d .git ] || { echo "repo root で実行してください"; exit 2; }

echo "== 1. License / packaging =="
ls LICENSE* COPYING* >/dev/null 2>&1 && ok "LICENSE あり" || ng "LICENSE が無い(企業は使えない)"
if [ -f pyproject.toml ]; then
  ok "pyproject.toml あり"
  for k in '^name' '^version' 'license' 'readme' 'requires-python'; do
    grep -qE "$k" pyproject.toml && ok "pyproject: $k" || wn "pyproject に $k が無い"
  done
else ng "pyproject.toml が無い"; fi

echo "== 2. README =="
if [ -f README.md ]; then
  ok "README.md あり"
  for s in 'install|quickstart|getting started' 'usage|example|demo' 'license' 'limitation|non-goal|not guarantee|does not'; do
    grep -qiE "$s" README.md && ok "README: $s" || ng "README に節が無い: $s"
  done
  tot=$(wc -c < README.md); na=$(LC_ALL=C tr -d '\000-\177' < README.md | wc -c)
  if [ "$tot" -gt 0 ] && [ $((na*100/tot)) -gt 15 ]; then wn "READMEの非ASCII率が高い: $((na*100/tot))%"; else ok "READMEは概ね英語"; fi
  echo "-- 誇大表現の候補 --"
  grep -niE 'absolute|unbreakable|impenetrable|unhackable|bulletproof|100 ?%|military|guarantee|real-time|seal ' README.md || echo "(なし)"
  echo "-- READMEが参照しているが存在しないファイル --"
  grep -oE '`[A-Za-z0-9_./-]+\.(json|md|py|xml|yml|yaml|toml|txt|html)`' README.md | tr -d '`' | sort -u | while read -r f; do [ -e "$f" ] || echo "MISSING: $f"; done
else ng "README.md が無い"; fi

echo "== 3. ルートの散らかり =="
n=$(git ls-files | grep -vc /)
if [ "$n" -gt 12 ]; then wn "ルート直下のファイルが ${n} 個(12以下が目安)"; else ok "ルート直下 ${n} 個"; fi
echo "-- 拡張子なしファイル --"
git ls-files | grep -v / | grep -v '\.' | grep -vE '^(LICENSE|Dockerfile|Makefile|NOTICE|CHANGELOG)' || echo "(なし)"
echo "-- 神話・内輪の名前を含むパス --"
git ls-files | grep -iE 'grimoire|underground|ataraxia|threat_intel|merkabah|chotam|local_arena' || echo "(なし)"

echo "== 4. 秘密情報らしき文字列 =="
git grep -nIE 'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' \
  && wn "上記が実キーでないか確認し、ダミーなら明示的にダミーと分かる名前にする" || ok "検出なし"

echo "== 5. テスト / CI =="
ls .github/workflows/*.y*ml >/dev/null 2>&1 && ok "CI workflow あり" || ng "CI workflow が無い"
if [ -d tests ] && [ -n "$(ls tests 2>/dev/null)" ]; then ok "tests/ あり"; else wn "tests/ が空か無い(ルート直下の test_*.py を tests/ に集約)"; fi
if [ "${RUN_TESTS:-0}" = "1" ]; then
  echo "-- pytest(サンドボックス内のみ) --"
  timeout 300 python -m pytest -q 2>&1 | tail -20
else echo "(RUN_TESTS=1 でテスト実行)"; fi

echo "== 6. 履歴 / サイズ =="
echo "commits: $(git rev-list --count HEAD)  last: $(git log -1 --format=%cd 2>/dev/null)"
echo "uncommitted: $(git status --porcelain | wc -l)"
echo "-- 1MB超のファイル --"
git ls-files -z | xargs -0 du -k 2>/dev/null | awk '$1>1024' || true

echo "== SUMMARY: PASS=$P WARN=$W FAIL=$F =="
[ "$F" -eq 0 ]
