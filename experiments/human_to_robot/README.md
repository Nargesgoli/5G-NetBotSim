# Human-to-robot teleoperation

Video upload pending. See [upload instructions](../../docs/VIDEO_UPLOAD.md).

**Paper: Sections IV-C1 and V-B1; Figures 3a, 6, and 7.**

The robotic-arm workload has two modes:

| Mode | Paper protocol | Available release assets |
|---|---|---|
| [Position/waypoint](position_control/) | Six named target configurations; evaluate delivery, queueing, dispatch, and task-response delay | Host command source, network bridge, and UE packet timing receivers in `timing/` |
| [Velocity-parameterized](velocity_control/) | Motion label and requested velocity; cancel/replan on new commands; intervals 0.5, 1.0, 1.5 s | Protocol guide; complete motion sender/controller and trajectory-analysis assets pending |

Read [the workflow and timing commands](../../docs/HUMAN_TO_ROBOT.md). The existing timing sender cycles pose labels; it is not itself a velocity-mode implementation. Full MoveIt/Gazebo arm assets and final datasets are external to this compact release.
