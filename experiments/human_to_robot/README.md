# Human-to-robot teleoperation

[Open or download the experiment video (MP4)](https://github.com/Nargesgoli/5G-NetBotSim/raw/refs/heads/main/experiments/human_to_robot/Humon_robot.mp4).

If GitHub cannot preview the file, use this direct link to open or download it. Playback depends on your browser; downloaded files can be opened in a local media player.

**Paper: Sections IV-C1 and V-B1; Figures 3a, 6, and 7.**

The robotic-arm workload has two modes:

| Mode | Paper protocol | Available release assets |
|---|---|---|
| [Position/waypoint](position_control/) | Six named target configurations; evaluate delivery, queueing, dispatch, and task-response delay | Host command source, network bridge, and UE packet timing receivers in `timing/` |
| [Velocity-parameterized](velocity_control/) | Motion label and requested velocity; cancel/replan on new commands; intervals 0.5, 1.0, 1.5 s | Protocol guide; complete motion sender/controller and trajectory-analysis assets pending |

Read [the workflow and timing commands](../../docs/HUMAN_TO_ROBOT.md). The existing timing sender cycles pose labels; it is not itself a velocity-mode implementation. Full MoveIt/Gazebo arm assets and final datasets are external to this compact release.
