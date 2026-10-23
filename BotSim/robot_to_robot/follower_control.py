#!/usr/bin/env python3
"""
follower_control.py  —  Ubuntu HOST
=========================================
Follower quadrotor (robot_beta):
  - ZMQ SUB on 172.17.0.1:9994 ← receives leader (x,y,z,yaw) from
    ue2_receiver.py via 5G pipeline
  - Computes target position as leader_position + offset
  - Sends velocity commands to /robot_beta/cmd_vel to reach target
  - Logs trajectory to CSV

Offset: follower trails 2m behind leader in X axis.

Usage:
  python3 follower_control.py

Requires:
  source /opt/ros/noetic/setup.bash
  source BotSim/workspaces/quadrotor_ws/devel/setup.bash
"""

import os
import time
import csv
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
FOLLOWER_ODOM_TOPIC = "/robot_beta/ground_truth/state"

# Offset: follower stays 2m behind leader in X, same Y, same Z
OFFSET_X = -2.0
OFFSET_Y =  0.0
OFFSET_Z =  0.0

# Controller gains
KP_XY  = 0.5    # proportional gain for XY position error
KP_Z   = 0.8    # proportional gain for altitude error
KP_YAW = 0.5    # proportional gain for yaw error

MAX_VXY = 0.5   # m/s max horizontal speed
MAX_VZ  = 0.3   # m/s max vertical speed
MAX_WZ  = 0.5   # rad/s max yaw rate

LOG_RATE_HZ = 10
ZMQ_RCVHWM  = 5

LOG_FILE = os.path.join(os.environ.get("NETBOTSIM_RESULTS_DIR", "."), "follower_quad.csv")
# ──────────────────────────────────────────────────────


class FollowerNodeQuad:
    def __init__(self):
        rospy.init_node("follower_node_quad", anonymous=False)

        self.cmd_pub  = rospy.Publisher(FOLLOWER_CMD_TOPIC, Twist, queue_size=10)
        self.odom_sub = rospy.Subscriber(
            FOLLOWER_ODOM_TOPIC, Odometry, self._odom_cb)

        # Follower current position
        self.fx = self.fy = self.fz = self.fyaw = 0.0
        self.odom_lock = threading.Lock()

        # Leader last known position (received via 5G)
        self.lx = self.ly = self.lz = self.lyaw = 0.0
        self.leader_lock    = threading.Lock()
        self.leader_received = False

        # ZMQ SUB — host binds, UE2 receiver connects
        self.ctx = zmq.Context()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.setsockopt(zmq.RCVHWM, ZMQ_RCVHWM)
        self.sub.bind(f"tcp://{BRIDGE_IP}:{FOLLOWER_ZMQ_PORT}")
        self.sub.setsockopt_string(zmq.SUBSCRIBE, "")
        rospy.loginfo(f"[Follower] ZMQ SUB bound on "
                      f"tcp://{BRIDGE_IP}:{FOLLOWER_ZMQ_PORT}")

        # CSV log
        import os
        os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
        self.csv_f = open(LOG_FILE, "w", newline="")
        self.csv_w = csv.writer(self.csv_f)
        self.csv_w.writerow(["t_sec", "fx", "fy", "fz",
                              "lx", "ly", "lz", "error"])
        self.t_start = None
        rospy.loginfo(f"[Follower] Logging to {LOG_FILE}")

    def _odom_cb(self, msg):
        q = msg.pose.pose.orientation
        with self.odom_lock:
            self.fx   = msg.pose.pose.position.x
            self.fy   = msg.pose.pose.position.y
            self.fz   = msg.pose.pose.position.z
            self.fyaw = math.atan2(2*(q.w*q.z + q.x*q.y),
                                   1 - 2*(q.y**2 + q.z**2))

    def _receive_leader(self):
        """Thread: receive leader position from ZMQ (via 5G pipeline)."""
        rospy.loginfo("[Follower] Waiting for leader state via 5G...")
        while not rospy.is_shutdown():
            try:
                msg = self.sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.01)
                continue

            try:
                x, y, z, yaw = [float(v) for v in msg.strip().split(",")]
                with self.leader_lock:
                    self.lx, self.ly, self.lz, self.lyaw = x, y, z, yaw
                    if not self.leader_received:
                        self.leader_received = True
                        rospy.loginfo(
                            f"[Follower] First leader state received: "
                            f"x={x:.2f} y={y:.2f} z={z:.2f}")
            except Exception as e:
                rospy.logwarn(f"[Follower] Parse error: {e}  raw='{msg}'")

    def _control_loop(self):
        """Thread: compute and publish velocity commands at LOG_RATE_HZ."""
        rate = rospy.Rate(LOG_RATE_HZ)

        # Wait for first leader state
        while not rospy.is_shutdown():
            with self.leader_lock:
                if self.leader_received:
                    break
            time.sleep(0.05)

        self.t_start = rospy.Time.now().to_sec()
        rospy.loginfo("[Follower] Control loop started.")

        while not rospy.is_shutdown():
            with self.leader_lock:
                lx, ly, lz, lyaw = self.lx, self.ly, self.lz, self.lyaw
            with self.odom_lock:
                fx, fy, fz, fyaw = self.fx, self.fy, self.fz, self.fyaw

            # Target position = leader + offset (in world frame)
            tx = lx + OFFSET_X
            ty = ly + OFFSET_Y
            tz = lz + OFFSET_Z

            # Position errors
            ex = tx - fx
            ey = ty - fy
            ez = tz - fz

            # Rotate XY error into robot body frame using follower yaw
            cos_y = math.cos(fyaw)
            sin_y = math.sin(fyaw)
            ex_body =  cos_y * ex + sin_y * ey
            ey_body = -sin_y * ex + cos_y * ey

            # Proportional control
            vx = max(-MAX_VXY, min(MAX_VXY, KP_XY * ex_body))
            vy = max(-MAX_VXY, min(MAX_VXY, KP_XY * ey_body))
            vz = max(-MAX_VZ,  min(MAX_VZ,  KP_Z  * ez))

            # Yaw control — follow leader yaw
            yaw_err = lyaw - fyaw
            while yaw_err >  math.pi: yaw_err -= 2*math.pi
            while yaw_err < -math.pi: yaw_err += 2*math.pi
            wz = max(-MAX_WZ, min(MAX_WZ, KP_YAW * yaw_err))

            # Publish command
            twist = Twist()
            twist.linear.x  = vx
            twist.linear.y  = vy
            twist.linear.z  = vz
            twist.angular.z = wz
            self.cmd_pub.publish(twist)

            # Log
            error = math.sqrt(ex**2 + ey**2 + ez**2)
            t = rospy.Time.now().to_sec() - self.t_start
            self.csv_w.writerow([f"{t:.3f}",
                                  f"{fx:.4f}", f"{fy:.4f}", f"{fz:.4f}",
                                  f"{lx:.4f}", f"{ly:.4f}", f"{lz:.4f}",
                                  f"{error:.4f}"])
            self.csv_f.flush()
            rate.sleep()

    def run(self):
        def control_worker():
            try:
                self._control_loop()
            except rospy.ROSInterruptException:
                pass
        worker = threading.Thread(target=control_worker)
        worker.start()
        rospy.loginfo("[Follower] Running. Ctrl+C to stop.")
        try:
            self._receive_leader()
        except (KeyboardInterrupt, rospy.ROSInterruptException):
            pass
        finally:
            rospy.signal_shutdown("Follower endpoint stopped")
            worker.join()
            self.cmd_pub.publish(Twist())
            self.csv_f.close()
            self.sub.close()
            self.ctx.term()
            rospy.loginfo(f"[Follower] Log saved to {LOG_FILE}")


if __name__ == "__main__":
    FollowerNodeQuad().run()
