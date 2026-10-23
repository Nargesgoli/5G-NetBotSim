#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist
import time
import sys

def perform_action(robot_name, linear_speed=0.0, angular_speed=0.0, duration=2.0):
    cmd_vel_topic = "/" + robot_name + "/cmd_vel"
    pub = rospy.Publisher(cmd_vel_topic, Twist, queue_size=10)

    rospy.loginfo(f"Controlling {robot_name} on {cmd_vel_topic}: lin={linear_speed}, ang={angular_speed}, dur={duration}s")

    action_cmd = Twist()
    action_cmd.linear.x = linear_speed
    action_cmd.angular.z = angular_speed
    stop_cmd = Twist()

    # Allow publisher to establish connection
    rospy.sleep(0.5) 

    start_time = rospy.get_time()
    if start_time == 0: start_time = time.time() # Fallback for initial ROS time
    
    rate = rospy.Rate(10) # 10hz
    while not rospy.is_shutdown():
        current_time = rospy.get_time()
        if current_time == 0: current_time = time.time()
        
        if current_time - start_time >= duration:
            break
        
        pub.publish(action_cmd)
        rate.sleep()

    pub.publish(stop_cmd) # Send stop command
    rospy.sleep(0.1)      # Short pause to ensure stop is processed
    pub.publish(stop_cmd) # Send stop again for robustness
    rospy.loginfo(f"{robot_name} action complete. Sent stop command.")

if __name__ == '__main__':
    try:
        rospy.init_node('robot_driver_node', anonymous=True)

        if len(sys.argv) < 2:
            rospy.logerr("Usage: rosrun simple_multi_sim robot_driver.py <robot_name_to_control>")
            rospy.logwarn("Example: rosrun simple_multi_sim robot_driver.py robot_alpha")
            sys.exit(1)
        
        target_robot = sys.argv[1]

        # Example sequence of actions for the target robot
        rospy.loginfo(f"--- Starting command sequence for {target_robot} ---")
        perform_action(robot_name=target_robot, linear_speed=0.3, duration=2.0) # Move forward
        rospy.sleep(1.0) # Pause
        perform_action(robot_name=target_robot, angular_speed=0.5, duration=3.0) # Turn
        rospy.sleep(1.0) # Pause
        perform_action(robot_name=target_robot, linear_speed=-0.2, duration=1.5) # Move backward
        
        rospy.loginfo(f"--- Command sequence for {target_robot} finished ---")

    except rospy.ROSInterruptException:
        rospy.loginfo("Node terminated by ROS interrupt.")
    except Exception as e:
        rospy.logerr(f"An error occurred: {e}")