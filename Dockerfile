# 軽量かつ堅牢なAlpine Linuxをベースとする
FROM python:3.11-alpine

# 最低限のユーザーを作成（root権限を剥奪するため）
RUN addgroup -S anjo && adduser -S anjo -G anjo

# 作業ディレクトリの設定
WORKDIR /sanctuary

# 依存関係を先にコピーしてインストール（レイヤーキャッシュを効かせるため）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# [修正 2026-10] 以前はmaquina_gatekeeper.py・tests/のみを個別にCOPYしており、
# テストが実際に必要とするruntime_guard/・angels/・adapters/・anjo_interceptor/・
# src/・tartarus/・tools/等が一切コピーされていなかった(ビルドして実行すると
# ほぼ全テストがModuleNotFoundErrorで失敗する、実質ビルド後未使用の不備が
# あった。詳細はGRIMOIRE.md §R参照)。個別ファイルの列挙は新規ディレクトリの
# 追記漏れを構造的に誘発するため、リポジトリ全体をコピーし、イメージに
# 含めたくないもの(.git・マシン固有の証明書・実行時生成物等)は.dockerignore
# 側で除外する方式に変更した。
COPY . .

# 実行ユーザーを root から anjo へ降格（OS層での権限剥奪）
USER anjo

# デフォルトの実行コマンド（テストやオーケストレータを起動）
CMD ["pytest", "tests/", "-v", "-s"]
