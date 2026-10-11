本文件记录如何录制rosbag并进行估计：

# 1 运行docker

```
cd ~/kalibr-deploy/kalibr
./run.sh

```

# 2 录.mcap 文件

终端1：打开左右相机流和imu流

```
ros2 launch realsense2_camera rs_launch.py \
  camera_name:=d455 \
  enable_color:=false \
  enable_depth:=false \
  enable_infra1:=true \
  enable_infra2:=true \
  depth_module.infra_profile:=848x480x30 \
  enable_gyro:=true \
  enable_accel:=true \
  unite_imu_method:=2 \
  depth_module.emitter_enabled:=0
```

终端3：打开左gui
```
ros2 run rqt_image_view rqt_image_view /camera/d455/infra1/image_rect_raw
```

如果看到的图像有斑点，需要[关闭红外投射器](#1-ros中关闭红外发射器)

终端4：打开右gui
```
ros2 run rqt_image_view rqt_image_view /camera/d455/infra2/image_rect_raw
```


终端2旁：在运行 ROS 2 Jazzy 的主机终端执行，开始录制。注意采集的时候应该[遵循规则](#2-标定版推荐移动顺序)。

```
cd /home/suiqingxian/kalibr-deploy/kalibr
mkdir -p data/d455

ros2 bag record -s mcap -o data/d455/d455_stereo_imu \
/camera/d455/infra1/image_rect_raw \
/camera/d455/infra1/camera_info \
/camera/d455/infra2/image_rect_raw \
/camera/d455/infra2/camera_info \
/camera/d455/accel/sample \
/camera/d455/gyro/sample
```

录制期间另开终端检查频率：

```
source /opt/ros/jazzy/setup.bash
ros2 topic hz /camera/d455/infra1/image_rect_raw
ros2 topic hz /camera/d455/infra2/image_rect_raw
ros2 topic hz /camera/d455/accel/sample
ros2 topic hz /camera/d455/gyro/sample
```

# 3 转化为rosbag

安装 rosbags 并转换成 ROS1 bag

在该python环境下安装，其实在conda里面安装也可以，无所谓。在系统还会报broken的错误。
```
sudo apt install -y python3-pip
python3 -m pip install --user -U rosbags
````
检查rosbags-convert --help 能输出内容就行，有问题问gpt

进行转换：
```
cd ~/kalibr-deploy/kalibr/data
rosbags-convert --src d455/d455_stereo_imu --dst d455_stereo_imu.bag

```

在docker中检查一下rosbag

```
rosbag info /data/d455/d455_stereo_imu.bag
```
有正确输出就是对的。

# 4 双目标定

需要有`imu.yaml` `aprilgrid.yaml`两个文件。imu是imu的信息，通过allen标定得到。
aprilgrid是所使用的标定板的信息。具体格式是规定好的，参考文件中的格式。

```
cd /home/suiqingxian/kalibr-deploy/kalibr     # 宿主机路径，这里才有 run.sh
KALIBR_GUI=1 ./run.sh bash -c 'cd /data/d455 && rosrun kalibr kalibr_calibrate_cameras \
  --bag /data/d455/d455_stereo_imu.bag \
  --target /data/d455/aprilgrid.yaml \
  --models pinhole-radtan pinhole-radtan \
  --topics /camera/d455/infra1/image_rect_raw /camera/d455/infra2/image_rect_raw \
  --show-extraction'
```

# 5 双目加imu标定

会报错，没有imu,需要合并一下imu的数据

在宿主机执行

```
cd /home/suiqingxian/kalibr-deploy/kalibr
KALIBR_GUI=0 ./run.sh bash -c 'cd /data/d455 && rosrun kalibr kalibr_calibrate_imu_camera \
  --bag /data/d455/d455_stereo_imu_imu.bag \
  --cams /data/d455/d455_stereo_imu-camchain.yaml \
  --imu /data/d455/imu.yaml \
  --target /data/d455/aprilgrid.yaml \
  --dont-show-report'

```


# 附录

## 1 ros中关闭红外发射器

ROS 2 直接关闭发射器

官方 RealSense ROS 文档实际上支持 depth_module.emitter_enabled 参数，但是否存在于你的节点中，需要以实际参数列表为准。不能仅凭 Failed to get parameters: emitter_enabled 就断定带前缀的参数也不存在。
GitHub
+1

先启动你的相机：

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

然后打开第二个终端，执行：

ros2 node list

假设节点名为 /camera/d455，检查：

ros2 param list /camera/d455 | grep -E 'emitter|laser'

如果输出包含 depth_module.emitter_enabled，直接执行：

ros2 param set /camera/d455 depth_module.emitter_enabled 0

再读取：

ros2 param get /camera/d455 depth_module.emitter_enabled

如果显示 Integer value is: 0，说明参数值已经设为关闭状态。

也可以在启动时尝试添加：

depth_module.emitter_enabled:=0

但如果参数列表中根本没有该参数，就不要继续尝试不同的参数值，应使用下面的底层方案。

## 2 标定版推荐移动顺序

推荐：前后移动
左右移动
上下移动
绕 X 轴转
绕 Y 轴转
绕 Z 轴转
近距离
中距离
远一点
标定板出现在画面左上、右上、左下、右下和中心


