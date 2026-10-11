#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
[[ "$(uname -m)" == x86_64 ]] || { echo "本镜像为 amd64，请使用 x86_64 Linux 主机。" >&2; exit 1; }
docker info >/dev/null
sha256sum -c kalibr-image.tar.gz.sha256
gzip -dc kalibr-image.tar.gz | docker load
expected="$(cat image-id.txt)"
actual="$(docker image inspect kalibr:latest --format '{{.Id}}')"
[[ "$actual" == "$expected" ]] || { echo "镜像 ID 不匹配" >&2; exit 1; }
./verify.sh
