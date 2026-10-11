#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${KALIBR_IMAGE:-kalibr:latest}"
DATA="${KALIBR_DATA_DIR:-$ROOT/data}"
mkdir -p -- "$DATA"
DATA="$(cd -- "$DATA" && pwd)"
docker info >/dev/null
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "未找到镜像，请先运行 ./import.sh" >&2
    exit 1
fi
args=(run --rm --network bridge --shm-size 64m
    --mount "type=bind,source=$DATA,target=/data"
    --workdir /data --env KALIBR_MANUAL_FOCAL_LENGTH_INIT=1
    --env QT_X11_NO_MITSHM=1 --entrypoint /bin/bash)
if [[ -t 0 && -t 1 ]]; then args+=(-it); fi
if [[ "${KALIBR_GUI:-0}" == 1 ]]; then
    : "${DISPLAY:?GUI 模式需要在本地图形桌面设置 DISPLAY}"
    command -v xhost >/dev/null || { echo "请安装 x11-xserver-utils" >&2; exit 1; }
    [[ -d /tmp/.X11-unix ]] || { echo "未找到 X11 socket" >&2; exit 1; }
    xhost +si:localuser:root >/dev/null
    trap 'xhost -si:localuser:root >/dev/null 2>&1 || true' EXIT
    args+=(--env "DISPLAY=$DISPLAY" --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix)
else
    args+=(--env MPLBACKEND=Agg)
fi
# 覆盖原镜像 shell-form ENTRYPOINT，确保参数被传递且每次加载 ROS 环境。
docker "${args[@]}" "$IMAGE" -c 'source /opt/ros/noetic/setup.bash --extend; source /catkin_ws/devel/setup.bash --extend; if [[ $# == 0 ]]; then exec bash --rcfile <(printf "%s\n" "source /opt/ros/noetic/setup.bash --extend; source /catkin_ws/devel/setup.bash --extend") -i; else exec "$@"; fi' kalibr "$@"
