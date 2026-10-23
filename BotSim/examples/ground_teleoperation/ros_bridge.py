#!/usr/bin/env python3
"""
ros_bridge.py  —  Ubuntu HOST
================================
Receives commands from UE1/UE2 (via ZMQ) and publishes
them as ROS Twist messages to the Gazebo robots.

  ZMQ SUB on 9991  →  /robot_alpha/cmd_vel
  ZMQ SUB on 9992  →  /robot_beta/cmd_vel

Run (after roslaunch):
  source /opt/ros/noetic/setup.bash
  source "$NETBOTSIM_ROS_WS/devel/setup.bash"
  python3 ros_bridge.py
"""

import os
import threading
import time
import zmq
import rospy
from geometry_msgs.msg import Twist

# ─── CONFIG ───────────────────────────────────────────
BRIDGE_BIND_IP = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")   # Docker bridge IP (host side)

UE_ROS_MAP = [
    {
        "zmq_port":  9991,
        "ros_topic": "/robot_alpha/cmd_vel",
        "robot":     "robot_alpha",
    },
    {
        "zmq_port":  9992,
        "ros_topic": "/robot_beta/cmd_vel",
        "robot":     "robot_beta",
    },
]

LINEAR_SPEED  = 0.6   # m/s
ANGULAR_SPEED = 0.8   # rad/s
CMD_DURATION  = 1.5   # seconds to apply command before auto-stop
# ──────────────────────────────────────────────────────


def cmd_to_twist(cmd: str) -> Twist:
    t   = Twist()
    cmd = cmd.strip().lower()
    if   cmd == "forward":   t.linear.x  =  LINEAR_SPEED
    elif cmd == "backward":  t.linear.x  = -LINEAR_SPEED
    elif cmd == "left":      t.angular.z =  ANGULAR_SPEED
    elif cmd == "right":     t.angular.z = -ANGULAR_SPEED
    elif cmd == "stop":      pass  # all zeros
    else:
        rospy.logwarn(f"Unknown command '{cmd}' — treating as stop")
    return t


def ue_bridge_worker(cfg: dict, zmq_ctx: zmq.Context):
    zmq_port  = cfg["zmq_port"]
    ros_topic = cfg["ros_topic"]
    robot     = cfg["robot"]

    # ZMQ SUB — UE connects TO this
    sub = zmq_ctx.socket(zmq.SUB)
    sub.bind(f"tcp://{BRIDGE_BIND_IP}:{zmq_port}")
    sub.setsockopt_string(zmq.SUBSCRIBE, "")
    rospy.loginfo(f"[ROS Bridge] SUB bound on {BRIDGE_BIND_IP}:{zmq_port}  ({robot})")

    pub       = rospy.Publisher(ros_topic, Twist, queue_size=10)
    stop_msg  = Twist()  # all zeros

    try:
        while not rospy.is_shutdown():
            try:
                cmd = sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.01)
                continue

            rospy.loginfo(f"[{robot}] cmd={cmd}")
            pub.publish(cmd_to_twist(cmd))
            time.sleep(CMD_DURATION)
            pub.publish(stop_msg)   # auto-stop

    except KeyboardInterrupt:
        pass
    finally:
        sub.close()
        rospy.loginfo(f"[ROS Bridge] {robot} worker stopped.")


def main():
    rospy.init_node("ue_ros_bridge", anonymous=False)
    rospy.loginfo("[ROS Bridge] Starting...")

    ctx = zmq.Context()
    threads = []
    for cfg in UE_ROS_MAP:
        t = threading.Thread(target=ue_bridge_worker,
                             args=(cfg, ctx), daemon=True)
        t.start()
        threads.append(t)

    rospy.loginfo("[ROS Bridge] Both UE→ROS bridges active. Waiting for commands...")
    rospy.spin()

    ctx.term()


if __name__ == "__main__":
    main()
