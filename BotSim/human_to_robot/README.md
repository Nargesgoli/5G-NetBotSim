# Human-to-robot application layer

The paper's human-to-robot experiment controls a multi-joint robotic arm using MoveIt, RViz, and Gazebo. It has position/waypoint and velocity-parameterized modes.

The available command and packet timing code is under [experiments/human_to_robot/timing](../../experiments/human_to_robot/timing/). Full host-side MoveIt dispatch, execution-start/completion instrumentation, cancellation/replanning nodes, and manipulator simulation assets are not included in this compact release.

See [human-to-robot workflow](../../docs/HUMAN_TO_ROBOT.md).
