#!/usr/bin/env python3
"""
leader.py  —  Ubuntu HOST
==================================
Leader robot (robot_alpha):
  - Runs a reproducible pre-defined trajectory on /robot_alpha/cmd_vel
  - Reads /robot_alpha/odom and logs ground-truth position to CSV
  - At UPDATE_RATE_HZ sends current (vx, wz) via ZMQ PUB to Docker
    where ue1_injector.py receives it, enters ue1 namespace, and
    sends it as UDP into the 5G stack toward ue2

ZMQ PUB on 172.17.0.1:9993  →  ue1_injector.py (inside Docker)

FIX: Each message now carries a monotonic timestamp (tx_ns) so the
     injector can drop stale messages that have been sitting in the
     ZMQ queue too long (backlog-drain problem).

Usage:
  python3 leader.py high     # or mid / low

Requires:
  source /opt/ros/noetic/setup.bash
  source "$NETBOTSIM_ROS_WS/devel/setup.bash"
"""

import os
import sys
import csv
import time
import math
import threading

import zmq
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# ─── CONFIG ───────────────────────────────────────────
HOST_BIND_IP    = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")
LEADER_ZMQ_PORT = 9993          # injector inside Docker subscribes here

LEADER_CMD_TOPIC  = "/robot_alpha/cmd_vel"
LEADER_ODOM_TOPIC = "/robot_alpha/odom"

LINEAR_SPEED  = 0.3             # m/s
ANGULAR_SPEED = 0.5             # rad/s
UPDATE_RATE_HZ = 5              # state broadcast rate to follower

# FIX: Limit ZMQ send buffer so stale messages don't pile up
ZMQ_SNDHWM = 5                  # max 5 messages in the outbound queue

# Reproducible trajectory: (vx, wz, duration_sec)
TRAJECTORY = [
    ( LINEAR_SPEED,  0.0,           2.0),
    ( 0.0,           ANGULAR_SPEED, 1.5),
    ( LINEAR_SPEED,  0.0,           2.5),
    ( 0.0,          -ANGULAR_SPEED, 1.0),
    ( LINEAR_SPEED,  0.0,           2.0),
    ( 0.0,           ANGULAR_SPEED, 2.0),
    ( LINEAR_SPEED,  0.0,           1.5),
    ( 0.0,          -ANGULAR_SPEED, 1.5),
    ( LINEAR_SPEED,  0.0,           2.0),
    (-LINEAR_SPEED,  0.0,           1.0),
    ( 0.0,           ANGULAR_SPEED, 1.0),
    ( LINEAR_SPEED,  0.0,           3.0),
    ( 0.0,           0.0,           1.0),
]
# ──────────────────────────────────────────────────────

CQI_LABEL = sys.argv[1] if len(sys.argv) > 1 else "high"
LOG_FILE   = f"leader_trajectory_{CQI_LABEL}.csv"


class LeaderNode:
    def __init__(self):
        rospy.init_node("leader_node", anonymous=False)

        self.cmd_pub  = rospy.Publisher(LEADER_CMD_TOPIC, Twist, queue_size=10)
        self.odom_sub = rospy.Subscriber(LEADER_ODOM_TOPIC, Odometry, self._odom_cb)

        self.x = self.y = self.yaw = 0.0
        self.odom_lock = threading.Lock()

        self.vx = self.wz = 0.0
        self.cmd_lock = threading.Lock()

        # ZMQ PUB → Docker injector
        # FIX: Set SNDHWM to prevent backlog accumulation
        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.setsockopt(zmq.SNDHWM, ZMQ_SNDHWM)
        self.pub.bind(f"tcp://{HOST_BIND_IP}:{LEADER_ZMQ_PORT}")
        rospy.loginfo(f"[Leader] ZMQ PUB bound on "
                      f"tcp://{HOST_BIND_IP}:{LEADER_ZMQ_PORT} "
                      f"(SNDHWM={ZMQ_SNDHWM})")
        time.sleep(1.5)   # slow-joiner

        self.csv_f = open(LOG_FILE, "w", newline="")
        self.csv_w = csv.writer(self.csv_f)
        self.csv_w.writerow(["t_sec", "x", "y", "yaw", "vx", "wz"])
        rospy.loginfo(f"[Leader] Logging to {LOG_FILE}")

    def _odom_cb(self, msg):
        q = msg.pose.pose.orientation
        with self.odom_lock:
            self.x   = msg.pose.pose.position.x
            self.y   = msg.pose.pose.position.y
            self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y),
                                  1 - 2*(q.y**2 + q.z**2))

    def _broadcast(self):
        """Thread: send (vx, wz) via ZMQ to Docker injector at UPDATE_RATE_HZ.
        
        FIX: header now carries monotonic tx_ns so the injector can detect
        and discard stale messages that sat in the ZMQ queue too long.
        """
        rate = rospy.Rate(UPDATE_RATE_HZ)
        seq  = 0
        while not rospy.is_shutdown():
            with self.cmd_lock:
                vx, wz = self.vx, self.wz
            tx_ns   = time.monotonic_ns()
            header  = f"{seq},{tx_ns}".encode("ascii")
            payload = f"{vx:.4f},{wz:.4f}".encode("utf-8")
            self.pub.send_multipart([b"leader", header, payload])
            seq += 1
            rate.sleep()

    def _log_odom(self):
        """Thread: log odom at UPDATE_RATE_HZ."""
        rate    = rospy.Rate(UPDATE_RATE_HZ)
        t_start = rospy.Time.now().to_sec()
        while not rospy.is_shutdown():
            with self.odom_lock:
                x, y, yaw = self.x, self.y, self.yaw
            with self.cmd_lock:
                vx, wz = self.vx, self.wz
            t = rospy.Time.now().to_sec() - t_start
            self.csv_w.writerow([f"{t:.3f}", f"{x:.4f}", f"{y:.4f}",
                                  f"{yaw:.4f}", f"{vx:.4f}", f"{wz:.4f}"])
            self.csv_f.flush()
            rate.sleep()

    def run(self):
        threading.Thread(target=self._broadcast, daemon=True).start()
        threading.Thread(target=self._log_odom,  daemon=True).start()

        rospy.loginfo("[Leader] Starting trajectory...")
        pub_rate = rospy.Rate(20)

        for (vx, wz, dur) in TRAJECTORY:
            if rospy.is_shutdown():
                break
            with self.cmd_lock:
                self.vx, self.wz = vx, wz

            twist = Twist()
            twist.linear.x  = vx
            twist.angular.z = wz
            rospy.loginfo(f"[Leader] vx={vx:.2f}  wz={wz:.2f}  dur={dur}s")

            end = time.time() + dur
            while time.time() < end and not rospy.is_shutdown():
                self.cmd_pub.publish(twist)
                pub_rate.sleep()

        # Stop
        with self.cmd_lock:
            self.vx = self.wz = 0.0
        self.cmd_pub.publish(Twist())
        rospy.loginfo(f"[Leader] Trajectory done. Log: {LOG_FILE}")
        self.csv_f.close()
        self.pub.close()
        self.ctx.term()


if __name__ == "__main__":
    LeaderNode().run()
