cmake_minimum_required(VERSION 3.0.2)
project(multi_robot_sim)

find_package(catkin REQUIRED COMPONENTS
  std_msgs rospy roscpp gazebo_ros xacro
)

catkin_package()

catkin_install_python(PROGRAMS scripts/robot_driver.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch urdf worlds
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
