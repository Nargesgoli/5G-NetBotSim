# Position/waypoint commands

The paper uses `zero_state`, `straight_up`, `pick_object_pose`, `lift_object_pose`, `opposite_pose`, and `place_object_pose`. Each names a fixed target; communication delay affects start/queueing and task response rather than changing the requested final configuration.

Available code: [command_sender.py](../timing/command_sender.py), [ran_bridge.py](../timing/ran_bridge.py), and the two UE timing receivers. They instrument the packet route. Full arm MoveIt dispatch, execution event logging, and the robot model are not included here. See [human-to-robot guide](../../../docs/HUMAN_TO_ROBOT.md).
