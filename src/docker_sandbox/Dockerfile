FROM python:3.11-alpine
# 権限を極限まで削ぎ落とした実行環境を構築
RUN adduser -D -H -s /bin/sh prisoner
WORKDIR /jail
USER prisoner
ENTRYPOINT ["python"]
