# D455 启动日志分析与正确命令

日志表明相机已经正常启动。真正的问题是，当前版本 RealSense ROS 4.57.7 / LibRealSense 2.57.7 不支持以下参数：

```text
emitter_enabled
depth_module.emitter_enabled
depth_module.laser_power
```

这些参数会被忽略。日志中的：

```text
Failed to get parameters: emitter_enabled
```

表示节点中不存在 `emitter_enabled` 参数。`unite_imu_method` 的 warning 只是启动顺序提示，不是致命错误。

正确启动命令如下：

```bash
ros2 launch realsense2_camera rs_launch.py \
  camera_name:=d455 \
  enable_color:=false \
  enable_depth:=false \
  enable_infra1:=true \
  enable_infra2:=true \
  depth_module.infra_profile:=848x480x30 \
  enable_gyro:=true \
  enable_accel:=true \
  gyro_fps:=200 \
  accel_fps:=100 \
  unite_imu_method:=2
```

日志已确认当前输出为：

```text
Infra1: 848x480, 30 Hz
Infra2: 848x480, 30 Hz
Accel: 100 Hz
Gyro: 200 Hz
```

如果必须关闭 D455 的红外发射器，需要通过 RealSense Viewer、设备 JSON 配置或 `pyrealsense2` 的底层 `set_option()` 设置。当前这个 ROS 启动文件不能直接通过参数关闭。关闭深度流本身也不能保证发射器关闭。
