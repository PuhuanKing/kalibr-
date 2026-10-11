#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
[[ ! -e kalibr-image.tar.gz ]] || { echo "镜像归档已存在，请先移动旧文件。" >&2; exit 1; }
trap 'rm -f kalibr-image.tar.gz.partial' EXIT
docker image inspect kalibr:latest --format '{{.Id}}' > image-id.txt
docker save kalibr:latest | gzip -1 > kalibr-image.tar.gz.partial
mv kalibr-image.tar.gz.partial kalibr-image.tar.gz
sha256sum kalibr-image.tar.gz > kalibr-image.tar.gz.sha256
echo "导出完成：复制整个目录到新电脑，再运行 ./import.sh"
