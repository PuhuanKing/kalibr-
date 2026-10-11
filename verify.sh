#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KALIBR_GUI=0 "$ROOT/run.sh" bash -c '
set -e
python3 -c "import numpy, scipy, matplotlib, cv2, kalibr_common, aslam_backend, cv_bridge"
for command in kalibr_calibrate_cameras kalibr_calibrate_imu_camera; do
    status=0
    rosrun kalibr "$command" --help >/tmp/kalibr-help.txt 2>&1 || status=$?
    if [[ "$status" != 0 && "$status" != 2 ]]; then cat /tmp/kalibr-help.txt; exit 1; fi
    # 此版本会捕获 argparse 的正常退出并返回 2，检查实际帮助内容。
    grep -q "usage:" /tmp/kalibr-help.txt
    grep -q -- "--bag" /tmp/kalibr-help.txt
done
printf "Kalibr 相机及相机-IMU命令与 Python 依赖验证通过\n"
'
