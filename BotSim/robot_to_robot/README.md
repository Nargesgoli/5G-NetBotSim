# Robot-to-robot application layer

The paper's quadrotor example uses `leader_state.py`, `ue1_injector.py`, `ue2_receiver.py`, and `follower_control.py`. The leader's flight driver is in the custom `simple_multi_sim` ROS package. The world-X follower offset is 2 m, and leader state is sampled at 10 Hz.

See [experiment organization](../../experiments/robot_to_robot/) and [launch guide](../../docs/ROBOT_TO_ROBOT.md). These normal-path UDP adapters do not enable EdgeSim's partial MAC bypass.
