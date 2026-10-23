#!/usr/bin/env python3
"""
Leader Drone Controller for 5G-NetBotSim
Flies a predefined waypoint mission independently.

Usage (in its own terminal, matching decoupled architecture):
  rosrun simple_multi_sim leader_driver.py robot_alpha

This maps to UE1 in the 5G-NetBotSim architecture.
Commands flow: Host → gNB → UE1 → robot_alpha/cmd_vel
"""

import rospy
import math
import sys
import csv
import os
from datetime import datetime
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty


class QuadrotorController:
    """Controls a single namespaced hector quadrotor."""

    def __init__(self, name, log_dir=None):
        self.name = name
        self.cmd_pub = rospy.Publisher(f'/{name}/cmd_vel', Twist, queue_size=10)
        self.position = {'x': 0.0, 'y': 0.0, 'z': 0.0}

        # CSV logging setup
        self.log_dir = os.path.expanduser(log_dir or os.environ.get("NETBOTSIM_RESULTS_DIR", "~/5G-NetBotSim-results"))
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = os.path.join(self.log_dir, f"{name}_{timestamp}.csv")
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'ros_time', 'wall_time', 'x', 'y', 'z',
            'cmd_vx', 'cmd_vy', 'cmd_vz', 'cmd_wz', 'phase'
        ])
        self.current_phase = 'init'
        self.last_cmd = {'vx': 0, 'vy': 0, 'vz': 0, 'wz': 0}
        rospy.loginfo(f"[{name}] Logging to: {self.csv_path}")

        rospy.Subscriber(f'/{name}/ground_truth/state', Odometry, self._odom_cb)
        rospy.sleep(0.5)

    def _odom_cb(self, msg):
        self.position['x'] = msg.pose.pose.position.x
        self.position['y'] = msg.pose.pose.position.y
        self.position['z'] = msg.pose.pose.position.z
        try:
            self.csv_writer.writerow([
                rospy.get_time(),
                datetime.now().isoformat(),
                f"{self.position['x']:.4f}",
                f"{self.position['y']:.4f}",
                f"{self.position['z']:.4f}",
                f"{self.last_cmd['vx']:.4f}",
                f"{self.last_cmd['vy']:.4f}",
                f"{self.last_cmd['vz']:.4f}",
                f"{self.last_cmd['wz']:.4f}",
                self.current_phase
            ])
        except:
            pass

    def engage_motors(self):
        service_name = f'/{self.name}/engage'
        rospy.loginfo(f"[{self.name}] Waiting for engage service...")
        try:
            rospy.wait_for_service(service_name, timeout=10.0)
            engage = rospy.ServiceProxy(service_name, Empty)
            engage()
            rospy.loginfo(f"[{self.name}] Motors engaged!")
            return True
        except rospy.ROSException:
            rospy.logerr(f"[{self.name}] engage service not available!")
            return False

    def send_cmd(self, lx=0.0, ly=0.0, lz=0.0, az=0.0):
        cmd = Twist()
        cmd.linear.x = lx
        cmd.linear.y = ly
        cmd.linear.z = lz
        cmd.angular.z = az
        self.last_cmd = {'vx': lx, 'vy': ly, 'vz': lz, 'wz': az}
        self.cmd_pub.publish(cmd)

    def stop(self):
        self.send_cmd(0.0, 0.0, 0.0, 0.0)

    def shutdown_motors(self):
        try:
            srv_name = f'/{self.name}/shutdown'
            rospy.wait_for_service(srv_name, timeout=2.0)
            shutdown = rospy.ServiceProxy(srv_name, Empty)
            shutdown()
            rospy.loginfo(f"[{self.name}] Motors shut down.")
        except:
            rospy.logwarn(f"[{self.name}] Could not shut down motors.")

    def close_log(self):
        self.csv_file.close()
        rospy.loginfo(f"[{self.name}] Log saved: {self.csv_path}")


def takeoff(drone, target_alt=2.0, speed=0.5):
    drone.current_phase = 'takeoff'
    rospy.loginfo(f"[{drone.name}] Taking off to {target_alt}m...")
    rate = rospy.Rate(20)
    while not rospy.is_shutdown():
        alt_error = target_alt - drone.position['z']
        if abs(alt_error) < 0.15:
            rospy.loginfo(f"[{drone.name}] Reached {drone.position['z']:.2f}m")
            break
        vz = max(min(alt_error * 0.8, speed), -speed)
        drone.send_cmd(lz=vz)
        rate.sleep()
    for _ in range(20):
        drone.stop()
        rate.sleep()


def go_to_point(drone, tx, ty, tz, speed=0.5, tolerance=0.3):
    rate = rospy.Rate(20)
    while not rospy.is_shutdown():
        dx = tx - drone.position['x']
        dy = ty - drone.position['y']
        dz = tz - drone.position['z']
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < tolerance:
            rospy.loginfo(f"[{drone.name}] Reached ({tx:.1f}, {ty:.1f}, {tz:.1f})")
            break

        kp = 0.6
        vx = max(min(dx * kp, speed), -speed)
        vy = max(min(dy * kp, speed), -speed)
        vz = max(min(dz * kp, speed), -speed)
        drone.send_cmd(lx=vx, ly=vy, lz=vz)
        rate.sleep()

    for _ in range(10):
        drone.stop()
        rate.sleep()


def land(drone, speed=0.3):
    drone.current_phase = 'landing'
    rospy.loginfo(f"[{drone.name}] Landing...")
    rate = rospy.Rate(20)
    while not rospy.is_shutdown():
        if drone.position['z'] < 0.25:
            break
        drone.send_cmd(lz=-speed)
        rate.sleep()
    for _ in range(30):
        drone.stop()
        rate.sleep()
    drone.shutdown_motors()


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            print("Usage: rosrun simple_multi_sim leader_driver.py <robot_name>")
            print("Example: rosrun simple_multi_sim leader_driver.py robot_alpha")
            sys.exit(1)

        robot_name = sys.argv[1]
        rospy.init_node(f'{robot_name}_leader_node', anonymous=False)
        rospy.loginfo(f"=== Leader Mission: {robot_name} ===")

        drone = QuadrotorController(robot_name)

        if not drone.engage_motors():
            rospy.signal_shutdown("Engage failed")
            sys.exit(1)

        rospy.sleep(1.0)

        # Phase 1: Takeoff
        takeoff(drone, target_alt=2.0)
        rospy.sleep(1.0)

        # Phase 2: Zigzag / staircase waypoint pattern
        drone.current_phase = 'waypoint'
        rospy.loginfo("=== Flying zigzag pattern ===")
        waypoints = [
            (3.0,  0.0, 2.0),
            (3.0,  2.0, 2.0),
            (6.0,  2.0, 2.0),
            (6.0,  4.0, 2.0),
            (9.0,  4.0, 2.0),
            (9.0,  6.0, 2.0),
            (6.0,  6.0, 2.5),
            (3.0,  4.0, 2.0),
            (0.0,  0.0, 2.0),
        ]

        for i, (wx, wy, wz) in enumerate(waypoints):
            drone.current_phase = f'waypoint_{i+1}'
            rospy.loginfo(f"--- Waypoint {i+1}/{len(waypoints)}: ({wx}, {wy}, {wz}) ---")
            go_to_point(drone, wx, wy, wz)

        # Phase 3: Land
        land(drone)
        drone.close_log()
        rospy.loginfo(f"=== {robot_name} mission complete! ===")

    except rospy.ROSInterruptException:
        rospy.loginfo("Mission interrupted.")
    except Exception as e:
        rospy.logerr(f"Error: {e}")
