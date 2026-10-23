#!/usr/bin/env python3
"""
leader_state.py  —  Ubuntu HOST
=======================================
Leader quadrotor (robot_alpha):
  - Reads /robot_alpha/ground_truth/state (nav_msgs/Odometry)
  - At UPDATE_RATE_HZ sends current (x, y, z, yaw) via ZMQ PUB to Docker
    where ue1_injector.py receives it, enters ue1 namespace, and
    sends it as UDP into the 5G stack toward ue2
  - Logs position to CSV

ZMQ PUB on 172.17.0.1:9993  →  ue1_injector.py (inside Docker)

Usage:
  python3 leader_state.py

Requires:
  source /opt/ros/noetic/setup.bash
  source BotSim/workspaces/quadrotor_ws/devel/setup.bash
"""

import os
import csv
import time
import math
import threading

import zmq
import rospy
from nav_msgs.msg import Odometry

# ─── CONFIG ───────────────────────────────────────────
HOST_BIND_IP    = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")
LEADER_ZMQ_PORT = 9993

LEADER_ODOM_TOPIC = "/robot_alpha/ground_truth/state"

UPDATE_RATE_HZ = 10             # state broadcast rate to follower
ZMQ_SNDHWM     = 5             # max messages in outbound ZMQ queue

LOG_FILE = os.path.join(os.environ.get("NETBOTSIM_RESULTS_DIR", "."), "leader_quad.csv")
# ──────────────────────────────────────────────────────


class LeaderNodeQuad:
    def __init__(self):
        rospy.init_node("leader_node_quad", anonymous=False)

        self.x = self.y = self.z = self.yaw = 0.0
        self.odom_lock = threading.Lock()
        self.odom_received = False

        self.odom_sub = rospy.Subscriber(
            LEADER_ODOM_TOPIC, Odometry, self._odom_cb)

        # ZMQ PUB → Docker injector
        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.setsockopt(zmq.SNDHWM, ZMQ_SNDHWM)
        self.pub.bind(f"tcp://{HOST_BIND_IP}:{LEADER_ZMQ_PORT}")
        rospy.loginfo(f"[Leader] ZMQ PUB bound on "
                      f"tcp://{HOST_BIND_IP}:{LEADER_ZMQ_PORT}")
        time.sleep(1.5)   # slow-joiner

        # CSV log
        import os
        os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
        self.csv_f = open(LOG_FILE, "w", newline="")
        self.csv_w = csv.writer(self.csv_f)
        self.csv_w.writerow(["t_sec", "x", "y", "z", "yaw"])
        rospy.loginfo(f"[Leader] Logging to {LOG_FILE}")

    def _odom_cb(self, msg):
        q = msg.pose.pose.orientation
        with self.odom_lock:
            self.x   = msg.pose.pose.position.x
            self.y   = msg.pose.pose.position.y
            self.z   = msg.pose.pose.position.z
            self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y),
                                  1 - 2*(q.y**2 + q.z**2))
            self.odom_received = True

    def _broadcast(self):
        """Thread: send (x, y, z, yaw) via ZMQ to Docker injector."""
        rate  = rospy.Rate(UPDATE_RATE_HZ)
        seq   = 0
        t_start = None

        while not rospy.is_shutdown():
            with self.odom_lock:
                received = self.odom_received
                x, y, z, yaw = self.x, self.y, self.z, self.yaw
            if not received:
                rate.sleep()
                continue

            if t_start is None:
                t_start = rospy.Time.now().to_sec()

            tx_ns   = time.monotonic_ns()
            header  = f"{seq},{tx_ns}".encode("ascii")
            payload = f"{x:.4f},{y:.4f},{z:.4f},{yaw:.4f}".encode("utf-8")
            self.pub.send_multipart([b"leader", header, payload])

            # Log to CSV
            t = rospy.Time.now().to_sec() - t_start
            self.csv_w.writerow([f"{t:.3f}", f"{x:.4f}", f"{y:.4f}",
                                  f"{z:.4f}", f"{yaw:.4f}"])
            self.csv_f.flush()

            seq += 1
            rate.sleep()

    def run(self):
        rospy.loginfo("[Leader] Broadcasting odometry. Ctrl+C to stop.")
        try:
            self._broadcast()
        except rospy.ROSInterruptException:
            pass
        finally:
            self.csv_f.close()
            self.pub.close()
            self.ctx.term()
            rospy.loginfo(f"[Leader] Log saved to {LOG_FILE}")


if __name__ == "__main__":
    LeaderNodeQuad().run()
