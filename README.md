# 本机 Kalibr Docker 配置清单与迁移说明

检查日期：2026-10-10。推荐直接复制本机已经编译好的镜像，其他电脑无需安装 ROS、Kalibr 或修改 Dockerfile。镜像归档不包含数据目录；标定数据需要单独复制。

## 已确认的本机配置

| 项目 | 本机配置 |
| --- | --- |
| 镜像 | `kalibr:latest`，精确 ID 见 `image-id.txt` |
| 镜像系统 / 架构 | Ubuntu 20.04.6 LTS / linux amd64 |
| ROS / Python | ROS Noetic / Python 3.8.10 |
| 工作空间 | `/catkin_ws`，已编译，环境文件 `/catkin_ws/devel/setup.bash` |
| 数值与绘图库 | NumPy 1.17.4、SciPy 1.3.3、Matplotlib 3.1.2 |
| OpenCV 开发包 | 4.2.0+dfsg-5 |
| 参考容器 | `charming_euler`，停止状态 |
| 原数据挂载 | `/home/qingxiansui/d455_kalibr/data` → `/data`，读写 |
| 原图形配置 | `/tmp/.X11-unix` 挂载、`DISPLAY=:1`、`QT_X11_NO_MITSHM=1` |
| 启动环境 | `KALIBR_MANUAL_FOCAL_LENGTH_INIT=1` |
| 网络 / 共享内存 | bridge / 64 MiB |
| 权限与设备 | root 用户；非 privileged；无 GPU、USB 映射，无端口发布 |
| 本机 Docker Engine | 29.4.3；目标机器不必完全同版 |

完整原始镜像及容器参数在 `local-config.json`。参考容器 diff 未发现依赖或源码文件修改，主要是 Python、ROS、绘图等运行缓存，因此迁移镜像即可。原 Dockerfile 位于项目的 `tools/kalibr/Dockerfile_ros1_20_04`，源码目录当前 Git 提交为 `1f60227442d25e36365ef5f72cd80b9666d73467`；这只说明当前宿主机源码版本，不保证是原镜像构建提交。

## 最快迁移流程

1. 本机导出（交付目录内已有归档时跳过）：

   ```bash
   cd /home/qingxiansui/d455_kalibr/deploy/kalibr
   ./export.sh
   ```

2. 把整个 `deploy/kalibr` 目录复制到新电脑任意位置，例如 `~/kalibr-docker`。目录含镜像归档、校验文件、脚本及本说明；无需复制源码和重新编译。

3. 新电脑使用 x86_64 Linux，准备可正常运行的 Docker Engine。Ubuntu 尚未安装 Docker 时可使用发行版软件包（若已安装 Docker，不要再执行安装）：

   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io
   sudo systemctl enable --now docker
   sudo usermod -aG docker "$USER"
   # 注销并重新登录后执行
   docker info
   ```

   建议至少预留 15 GB 可用磁盘，包含归档、解压后的镜像及余量；标定 bag 的空间另计。内存建议至少 8 GB，大数据集建议 16 GB 或更多。宿主机无需是 Ubuntu 20.04；镜像内部系统保持原版本。ARM 电脑及 Windows/macOS 图形配置不在这套已验证流程范围内。

4. 导入并自动验证：

   ```bash
   cd ~/kalibr-docker
   ./import.sh
   ```

   导入前自动校验归档 SHA256，导入后校验镜像 ID，并验证 Python 依赖、相机及相机-IMU命令。此版本的 Kalibr `--help` 会返回 2；验证脚本同时检查帮助内容以兼容这一行为。

5. 将 `.bag`、`aprilgrid.yaml`、`imu.yaml` 和相机配置等复制到该目录的 `data/`，进入环境：

   ```bash
   ./run.sh
   # 容器内已经加载 ROS 和 Kalibr，当前目录为 /data
   rosbag info your-recording.bag
   ```

   或直接指定已有的数据目录，无需编辑脚本：

   ```bash
   KALIBR_DATA_DIR="$HOME/d455_kalibr/data" ./run.sh
   ```

## 标定命令示例

实际 bag 名称和 topic 请先用 `rosbag info` 确认；以下 topic 是示例，不代表当前数据的真实 topic。

```bash
./run.sh rosrun kalibr kalibr_calibrate_cameras \
  --bag /data/your-recording.bag \
  --topics /cam0/image_raw /cam1/image_raw \
  --models pinhole-radtan pinhole-radtan \
  --target /data/aprilgrid.yaml --dont-show-report

./run.sh rosrun kalibr kalibr_calibrate_imu_camera \
  --bag /data/your-recording.bag \
  --cams /data/camchain.yaml --imu /data/imu.yaml \
  --target /data/aprilgrid.yaml --dont-show-report
```

默认无界面，设置 `MPLBACKEND=Agg`；标定时使用 `--dont-show-report`，完成后在宿主机打开 PDF。原始 ROS2 bag 目录不能直接交给此 ROS1 Kalibr，需先转换为 ROS1 `.bag`。

需要显示提取图像或报告时，在 Linux 图形桌面的终端中运行：

```bash
sudo apt-get install -y x11-xserver-utils
KALIBR_GUI=1 ./run.sh
```

脚本读取当前电脑的 `DISPLAY`，自动挂载 X11 socket 并临时授权本机 root，退出后撤销授权。Wayland 桌面需要启用 XWayland；纯 SSH 或无显示器环境使用默认无界面模式。GUI 尚未在新电脑验证。

## 不需要反复修改的设置

- 默认数据路径是脚本旁的 `data/`，自动计算绝对路径，不含本机用户名。
- 自定义数据路径：`KALIBR_DATA_DIR=/absolute/path ./run.sh`。
- 图形模式：`KALIBR_GUI=1 ./run.sh`，无需硬编码 `DISPLAY=:1`。
- 自定义镜像：`KALIBR_IMAGE=your-tag ./run.sh`。
- 每次自动加载 ROS/Kalibr 环境，绕过原镜像不会正确传递命令参数的 shell 入口。
- 容器结束后自动删除，输出需放在 `/data` 才能保留。root 生成的文件必要时在宿主机用 `sudo chown -R "$USER:$(id -gn)" data` 调整归属。

## 验证范围

本机已通过依赖导入及两个标定命令的帮助入口验证。没有重新运行完整标定，也未验证新电脑的 GUI。优先使用归档复现环境；原 Dockerfile 依赖在线软件源、未锁定的基础镜像和依赖版本，重新构建不保证获得完全相同的镜像。
