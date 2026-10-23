#!/usr/bin/env python3
"""
follower.py  —  Ubuntu HOST
=====================================
Follower robot (robot_beta):
  - ZMQ SUB on 172.17.0.1:9994 ← receives leader (vx,wz) from ue2_receiver.py
  - Applies received command to /robot_beta/cmd_vel immediately
  - Continues executing last command until next update arrives (hold-last)
  - Subscribes to /robot_beta/odom and logs trajectory to CSV

FIXES applied:
  1. t_sec in CSV now starts from first received command, not from node init.
     This prevents hundreds of seconds of frozen (0,0) rows polluting the log.
  2. CSV logging only begins once the first command arrives (first_cmd_received flag).
  3. Log also records the received vx/wz alongside position so trajectory
     and command are always in sync.

SPAWN NOTE: robot_beta must be spawned with yaw=0 (same heading as robot_alpha)
  and positioned directly behind it (e.g. x=-1.5, y=0) in your .launch file.
  If robot_beta spawns facing yaw=pi (opposite direction), the same velocity
  commands will drive it in the mirrored direction.

Usage:
  python3 follower.py high     # or mid / low

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
BRIDGE_IP         = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")
FOLLOWER_ZMQ_PORT = 9994

FOLLOWER_CMD_TOPIC  = "/robot_beta/cmd_vel"
FOLLOWER_ODOM_TOPIC = "/robot_beta/odom"

LOG_RATE_HZ = 5
CMD_PUB_HZ  = 20    # rate at which we republish current command to Gazebo

# FIX: Limit receive buffer to avoid draining a stale backlog after leader stops
ZMQ_RCVHWM = 5
# ──────────────────────────────────────────────────────

CQI_LABEL = sys.argv[1] if len(sys.argv) > 1 else "high"
LOG_FILE   = f"follower_trajectory_{CQI_LABEL}.csv"


class FollowerNode:
    def __init__(self):
        rospy.init_node("follower_node", anonymous=False)

        self.cmd_pub  = rospy.Publisher(FOLLOWER_CMD_TOPIC, Twist, queue_size=10)
        self.odom_sub = rospy.Subscriber(FOLLOWER_ODOM_TOPIC, Odometry, self._odom_cb)

        # Current position
        self.x = self.y = self.yaw = 0.0
        self.odom_lock = threading.Lock()

        # Current command (hold-last until new one arrives)
        self.vx = self.wz = 0.0
        self.cmd_lock = threading.Lock()

        # FIX: t_start is None until the first command arrives.
        # Logging thread waits for this before writing any rows.
        self.t_start = None
        self.t_start_lock = threading.Lock()

        # ZMQ SUB — host binds, UE2 receiver connects
        # FIX: Set RCVHWM so stale queued messages are dropped
        self.ctx = zmq.Context()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.setsockopt(zmq.RCVHWM, ZMQ_RCVHWM)
        self.sub.bind(f"tcp://{BRIDGE_IP}:{FOLLOWER_ZMQ_PORT}")
        self.sub.setsockopt_string(zmq.SUBSCRIBE, "")
        rospy.loginfo(f"[Follower] ZMQ SUB bound on "
                      f"tcp://{BRIDGE_IP}:{FOLLOWER_ZMQ_PORT} "
                      f"(RCVHWM={ZMQ_RCVHWM})")

        # CSV log
        self.csv_f = open(LOG_FILE, "w", newline="")
        self.csv_w = csv.writer(self.csv_f)
        self.csv_w.writerow(["t_sec", "x", "y", "yaw", "vx", "wz"])
        rospy.loginfo(f"[Follower] Logging to {LOG_FILE} "
                      f"(will start on first received command)")

    def _odom_cb(self, msg):
        q = msg.pose.pose.orientation
        with self.odom_lock:
            self.x   = msg.pose.pose.position.x
            self.y   = msg.pose.pose.position.y
            self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y),
                                  1 - 2*(q.y**2 + q.z**2))

    def _receive_state(self):
        """Thread: receive leader state from ZMQ, update current command.
        
        FIX: Sets t_start on the very first successfully parsed message
        so CSV timestamps are relative to actual motion start.
        """
        rospy.loginfo("[Follower] Waiting for first leader command...")
        while not rospy.is_shutdown():
            try:
                msg = self.sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.01)
                continue

            # Parse "vx,wz"
            try:
                vx, wz = [float(v) for v in msg.strip().split(",")]
                with self.cmd_lock:
                    self.vx, self.wz = vx, wz

                # FIX: stamp t_start on first command received
                with self.t_start_lock:
                    if self.t_start is None:
                        self.t_start = rospy.Time.now().to_sec()
                        rospy.loginfo(
                            f"[Follower] First command received — "
                            f"starting CSV log. vx={vx:.3f} wz={wz:.3f}"
                        )
                    else:
                        rospy.loginfo(
                            f"[Follower] New cmd  vx={vx:.3f}  wz={wz:.3f}"
                        )

            except Exception as e:
                rospy.logwarn(f"[Follower] Parse error: {e}  raw='{msg}'")

    def _publish_cmd(self):
        """Thread: continuously publish current command at CMD_PUB_HZ (hold-last)."""
        rate = rospy.Rate(CMD_PUB_HZ)
        while not rospy.is_shutdown():
            with self.cmd_lock:
                vx, wz = self.vx, self.wz
            twist = Twist()
            twist.linear.x  = vx
            twist.angular.z = wz
            self.cmd_pub.publish(twist)
            rate.sleep()

    def _log_odom(self):
        """Thread: log odom position at LOG_RATE_HZ.
        
        FIX: Blocks until t_start is set (i.e. first command received).
        t_sec in the CSV is always relative to that moment.
        """
        rate = rospy.Rate(LOG_RATE_HZ)

        # Wait for first command before starting to log
        while not rospy.is_shutdown():
            with self.t_start_lock:
                if self.t_start is not None:
                    break
            time.sleep(0.05)

        rospy.loginfo("[Follower] Odometry logging started.")

        while not rospy.is_shutdown():
            with self.odom_lock:
                x, y, yaw = self.x, self.y, self.yaw
            with self.cmd_lock:
                vx, wz = self.vx, self.wz
            with self.t_start_lock:
                t_start = self.t_start

            t = rospy.Time.now().to_sec() - t_start
            self.csv_w.writerow([f"{t:.3f}", f"{x:.4f}", f"{y:.4f}",
                                  f"{yaw:.4f}", f"{vx:.4f}", f"{wz:.4f}"])
            self.csv_f.flush()
            rate.sleep()

    def run(self):
        threading.Thread(target=self._receive_state, daemon=True).start()
        threading.Thread(target=self._publish_cmd,   daemon=True).start()
        threading.Thread(target=self._log_odom,      daemon=True).start()

        rospy.loginfo("[Follower] Running — waiting for leader. Ctrl+C to stop.")
        rospy.spin()

        # Stop robot on exit
        self.cmd_pub.publish(Twist())
        self.csv_f.close()
        self.sub.close()
        self.ctx.term()
        rospy.loginfo(f"[Follower] Log saved to {LOG_FILE}")


if __name__ == "__main__":
    FollowerNode().run()
