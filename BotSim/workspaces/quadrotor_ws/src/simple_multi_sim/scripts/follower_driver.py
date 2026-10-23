#!/usr/bin/env python3
"""
Follower Drone Controller for 5G-NetBotSim
Subscribes to a leader drone's odometry and follows with a fixed offset.

Usage (in its own terminal, matching decoupled architecture):
  rosrun simple_multi_sim follower_driver.py robot_beta robot_alpha

  Args:
    robot_beta   = this follower's name
    robot_alpha  = the leader to follow

This maps to UE2 in the 5G-NetBotSim architecture.
- Leader telemetry arrives via: gNB → UE2 (over 5G downlink)
- Follower commands flow: Host → gNB → UE2 → robot_beta/cmd_vel
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
            'cmd_vx', 'cmd_vy', 'cmd_vz', 'cmd_wz', 'phase',
            'leader_x', 'leader_y', 'leader_z'
        ])
        self.current_phase = 'init'
        self.last_cmd = {'vx': 0, 'vy': 0, 'vz': 0, 'wz': 0}
        self.leader_pos = {'x': 0, 'y': 0, 'z': 0}
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
                self.current_phase,
                f"{self.leader_pos['x']:.4f}",
                f"{self.leader_pos['y']:.4f}",
                f"{self.leader_pos['z']:.4f}"
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


class LeaderTracker:
    """Subscribes to a leader drone's odometry."""

    def __init__(self, leader_name):
        self.leader_name = leader_name
        self.position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.has_data = False

        rospy.Subscriber(
            f'/{leader_name}/ground_truth/state', Odometry, self._leader_odom_cb
        )
        rospy.loginfo(f"Subscribed to /{leader_name}/ground_truth/state")

    def _leader_odom_cb(self, msg):
        self.position['x'] = msg.pose.pose.position.x
        self.position['y'] = msg.pose.pose.position.y
        self.position['z'] = msg.pose.pose.position.z
        self.has_data = True

    def is_airborne(self):
        """Leader is considered airborne if altitude > 1.0m"""
        return self.has_data and self.position['z'] > 1.0

    def has_landed(self):
        """Leader is considered landed if altitude < 0.3m"""
        return self.has_data and self.position['z'] < 0.3


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


def follow_leader(drone, leader, offset_x=-2.0, offset_y=0.0, speed=0.5):
    """
    Continuously follow the leader with a fixed offset.
    Runs until the leader lands (altitude < 0.3m for sustained period)
    or ROS shuts down.
    """
    drone.current_phase = 'following'
    rate = rospy.Rate(20)
    kp = 0.8
    landed_count = 0
    # Need leader to be grounded for 3 seconds (60 ticks at 20Hz) to confirm landed
    landed_threshold = 60

    rospy.loginfo(f"[{drone.name}] Following {leader.leader_name} "
                  f"with offset ({offset_x}, {offset_y})")

    while not rospy.is_shutdown():
        if not leader.has_data:
            rate.sleep()
            continue

        # Update leader position for CSV logging
        drone.leader_pos = leader.position.copy()

        # Detect if leader has landed (must be sustained)
        if leader.has_landed():
            landed_count += 1
            if landed_count > landed_threshold:
                rospy.loginfo(f"[{drone.name}] Leader has landed. Stopping follow.")
                break
        else:
            landed_count = 0

        # Compute target = leader position + offset
        tx = leader.position['x'] + offset_x
        ty = leader.position['y'] + offset_y
        tz = leader.position['z']

        dx = tx - drone.position['x']
        dy = ty - drone.position['y']
        dz = tz - drone.position['z']

        vx = max(min(dx * kp, speed), -speed)
        vy = max(min(dy * kp, speed), -speed)
        vz = max(min(dz * kp, speed), -speed)

        drone.send_cmd(lx=vx, ly=vy, lz=vz)
        rate.sleep()

    drone.stop()


if __name__ == '__main__':
    try:
        if len(sys.argv) < 3:
            print("Usage: rosrun simple_multi_sim follower_driver.py <follower_name> <leader_name>")
            print("Example: rosrun simple_multi_sim follower_driver.py robot_beta robot_alpha")
            sys.exit(1)

        follower_name = sys.argv[1]
        leader_name = sys.argv[2]

        rospy.init_node(f'{follower_name}_follower_node', anonymous=False)
        rospy.loginfo(f"=== Follower: {follower_name} tracking {leader_name} ===")

        drone = QuadrotorController(follower_name)
        leader = LeaderTracker(leader_name)

        if not drone.engage_motors():
            rospy.signal_shutdown("Engage failed")
            sys.exit(1)

        rospy.sleep(1.0)

        # Wait for leader data
        rospy.loginfo(f"[{follower_name}] Waiting for leader odometry...")
        while not leader.has_data and not rospy.is_shutdown():
            rospy.sleep(0.1)
        rospy.loginfo(f"[{follower_name}] Leader data received!")

        # WAIT ON THE GROUND until leader is airborne
        drone.current_phase = 'waiting_for_leader'
        rospy.loginfo(f"[{follower_name}] Waiting on ground for leader to take off...")
        while not leader.is_airborne() and not rospy.is_shutdown():
            rospy.sleep(0.1)
        rospy.loginfo(f"[{follower_name}] Leader is airborne! Starting takeoff.")

        # Takeoff
        takeoff(drone, target_alt=2.0)
        rospy.sleep(0.5)

        # Follow leader until leader lands
        follow_leader(drone, leader, offset_x=-2.0, offset_y=0.0)

        # Land
        land(drone)
        drone.close_log()
        rospy.loginfo(f"=== {follower_name} mission complete! ===")

    except rospy.ROSInterruptException:
        rospy.loginfo("Mission interrupted.")
    except Exception as e:
        rospy.logerr(f"Error: {e}")
