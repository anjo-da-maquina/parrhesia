"""
adapters/provisioning_agent.py
===============================
[脆弱性修正 2026-10] 以前の実装は、この場で新規生成したRSA鍵対の
公開鍵を使って `runtime_audit_gatekeeper.py` の `MAQUINA_PUBLIC_KEY_PEM`
（証明書検証の信頼の起点）を直接上書きし、同じ鍵対の秘密鍵で自ら
署名した証明書(`ataraxia_certificate.json`)をそのまま有効化していた。

これは「審査者と被審査者が同一」という自己署名の構造的欠陥であり、
`enforce_maquina_seal`（runtime_audit_gatekeeper.py）によるライセンス
証明書チェックは、本スクリプトを実行できる者なら誰でも自分自身を
無条件に「承認済み」にできてしまい、実質的に何の認可も提供していな
かった。§Fの`ZadkielDominion`（LLM提案ルールの無審査反映）や
Armageddon Engineの`raziel_ledger_pending.json`で既に修正したのと
同種の脆弱性である。

本修正では、鍵対の生成と証明書ペイロードの署名はこの場で行うが、
`runtime_audit_gatekeeper.py`の書き換えと`ataraxia_certificate.json`の
発行は行わず、`runtime_guard/provisioning_pending.json`への提案キューイング
に留める。人間が`tools/promote_provisioning_seal.py`で内容
（hardware_fingerprint・client_id・有効期限）を確認し明示的に
承認して初めて、信頼の起点（公開鍵）が更新され証明書が発行される。
"""
import rsa
import json
import datetime
import base64
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runtime_audit_gatekeeper import get_absolute_hardware_fingerprint

PENDING_PATH = os.path.join(os.path.dirname(__file__), "..", "runtime_guard", "provisioning_pending.json")


def _load_pending():
    if not os.path.exists(PENDING_PATH):
        return []
    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_pending(entries):
    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def provision_registration(client_id="anjo-local-tester"):
    print("\n[Provisioning Agent] 新たな鍵対を生成し、承認を提案します...")
    # 2048bitの強力なRSA鍵対を新規生成（この場限り。秘密鍵は保存しない）
    pubkey, privkey = rsa.newkeys(2048)
    pubkey_pem = pubkey.save_pkcs1().decode('utf-8')

    fingerprint = get_absolute_hardware_fingerprint()
    valid_until = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"

    payload = {
        "client_id": client_id,
        "hardware_fingerprint": fingerprint,
        "valid_until": valid_until
    }

    payload_str = json.dumps(payload, sort_keys=True)
    signature = rsa.sign(payload_str.encode('utf-8'), privkey, 'SHA-256')
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    entry = {
        "status": "PENDING_HUMAN_REVIEW",
        "requested_at": datetime.datetime.utcnow().isoformat() + "Z",
        "payload": payload,
        "signature": signature_b64,
        "public_key_pem": pubkey_pem.strip(),
    }

    pending = _load_pending()
    pending.append(entry)
    _save_pending(pending)

    print(f"[Provisioning Agent] 承認待ちキュー({PENDING_PATH})に提案を追加しました。")
    print("[Provisioning Agent] runtime_audit_gatekeeper.py・ataraxia_certificate.jsonはまだ変更されていません。")
    print(f"[Provisioning Agent] 人間が 'python tools/promote_provisioning_seal.py --approve {client_id}' で承認するまで有効になりません。")


if __name__ == '__main__':
    provision_registration()
