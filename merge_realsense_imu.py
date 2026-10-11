#!/usr/bin/env python3
"""把 RealSense 分离的 accel/sample + gyro/sample 合并成一个 sensor_msgs/Imu topic。

复现 unite_imu_method:=2 的行为：以 gyro 时间轴为基准，把 accel 线性插值到每个 gyro
时间戳上，输出到新的 ROS1 bag（原始 topic 全部保留）。供 ROS1 Kalibr 使用。

用法:
    rosbags-merge-imu --src IN.bag --dst OUT.bag
    python3 merge_realsense_imu.py --src IN.bag --dst OUT.bag \
        --accel-topic /camera/d455/accel/sample \
        --gyro-topic  /camera/d455/gyro/sample \
        --out-topic   /camera/d455/imu
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.rosbag1 import Writer

IMU_TYPE = "sensor_msgs/msg/Imu"


def _stamp_ns(msg) -> int:
    return msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec


def _lerp(a: float, b: float, t: float, t0: int, t1: int) -> float:
    if t1 == t0:
        return a
    w = (t - t0) / (t1 - t0)
    return a * (1.0 - w) + b * w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--dst", required=True, type=Path)
    ap.add_argument("--accel-topic", default="/camera/d455/accel/sample")
    ap.add_argument("--gyro-topic", default="/camera/d455/gyro/sample")
    ap.add_argument("--out-topic", default="/camera/d455/imu")
    args = ap.parse_args()

    if args.src.resolve() == args.dst.resolve():
        raise SystemExit("src 与 dst 不能相同")

    accel: list[tuple[int, float, float, float]] = []
    gyro: list[tuple[int, float, float, float]] = []
    accel_cov = None
    gyro_cov = None
    frame_id = "imu_frame"
    accel_conn = gyro_conn = None

    with AnyReader([args.src]) as reader, Writer(args.dst) as writer:
        typestore = reader.typestore
        Imu = typestore.types[IMU_TYPE]

        # 先建立所有原始 topic 的连接，逐条原样搬运。
        out_conns = {}
        for c in reader.connections:
            out_conns[c.id] = writer.add_connection(
                c.topic, c.msgtype, typestore=typestore
            )
            if c.topic == args.accel_topic:
                accel_conn = c
            elif c.topic == args.gyro_topic:
                gyro_conn = c

        if accel_conn is None:
            raise SystemExit(f"bag 中没有 accel topic: {args.accel_topic}")
        if gyro_conn is None:
            raise SystemExit(f"bag 中没有 gyro topic: {args.gyro_topic}")

        out_imu_conn = writer.add_connection(
            args.out_topic, IMU_TYPE, typestore=typestore
        )

        n_orig = 0
        for conn, ts, raw in reader.messages():
            writer.write(out_conns[conn.id], ts, raw)
            n_orig += 1
            if conn.topic == args.accel_topic:
                m = reader.deserialize(raw, conn.msgtype)
                v = m.linear_acceleration
                accel.append((_stamp_ns(m), v.x, v.y, v.z))
                accel_cov = m.linear_acceleration_covariance
            elif conn.topic == args.gyro_topic:
                m = reader.deserialize(raw, conn.msgtype)
                w = m.angular_velocity
                gyro.append((_stamp_ns(m), w.x, w.y, w.z))
                gyro_cov = m.angular_velocity_covariance
                frame_id = m.header.frame_id or frame_id

        accel.sort()
        gyro.sort()
        if not accel or not gyro:
            raise SystemExit("accel 或 gyro 样本为空")

        a_t = [s[0] for s in accel]
        n_accel = len(accel)
        j = 0
        written = 0
        for gi, (t, gx, gy, gz) in enumerate(gyro):
            # 找到 accel 时间轴上夹住 t 的区间
            while j + 1 < n_accel and a_t[j + 1] <= t:
                j += 1
            if t <= a_t[0]:
                ax, ay, az = accel[0][1:4]
            elif t >= a_t[-1]:
                ax, ay, az = accel[-1][1:4]
            else:
                t0, a0x, a0y, a0z = accel[j]
                t1, a1x, a1y, a1z = accel[j + 1]
                ax = _lerp(a0x, a1x, t, t0, t1)
                ay = _lerp(a0y, a1y, t, t0, t1)
                az = _lerp(a0z, a1z, t, t0, t1)

            sec, nsec = divmod(t, 1_000_000_000)
            msg = Imu(
                header=typestore.types["std_msgs/msg/Header"](
                    seq=gi,
                    stamp=typestore.types["builtin_interfaces/msg/Time"](
                        sec=sec, nanosec=nsec
                    ),
                    frame_id=frame_id,
                ),
                orientation=typestore.types["geometry_msgs/msg/Quaternion"](
                    x=0.0, y=0.0, z=0.0, w=1.0
                ),
                orientation_covariance=np.array([-1.0] + [0.0] * 8, dtype=np.float64),
                angular_velocity=typestore.types["geometry_msgs/msg/Vector3"](
                    x=gx, y=gy, z=gz
                ),
                angular_velocity_covariance=np.array(
                    gyro_cov if gyro_cov is not None else [0.0] * 9, dtype=np.float64
                ),
                linear_acceleration=typestore.types["geometry_msgs/msg/Vector3"](
                    x=ax, y=ay, z=az
                ),
                linear_acceleration_covariance=np.array(
                    accel_cov if accel_cov is not None else [0.0] * 9, dtype=np.float64
                ),
            )
            writer.write(out_imu_conn, t, typestore.serialize_ros1(msg, IMU_TYPE))
            written += 1

        print(f"原始消息 {n_orig} 条；accel {len(accel)} 样本，gyro {len(gyro)} 样本")
        print(f"新 topic {args.out_topic} 写入 {written} 条 (以 gyro 时间轴, accel 线性插值)")
        print(f"输出: {args.dst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
