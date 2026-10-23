# BotSim

**Paper: Section III-B — Isolated Robotic Execution.**

BotSim is the ROS Noetic/Gazebo 11 robotic application layer. Host-side ROS processes are associated with per-robot ROS namespaces; network endpoints run inside the Docker environment and UE namespaces. ZeroMQ connects the host/container application boundaries while the cellular path carries messages between network endpoints.

| Workload | Robot application | Source / integration |
|---|---|---|
| Human-to-robot | Robotic arm, position targets and velocity-parameterized motion | [human_to_robot/](human_to_robot/); supplied timing path, with full MoveIt execution assets pending |
| Robot-to-robot | Two quadrotors, leader state and follower control | [robot_to_robot/](robot_to_robot/) and `workspaces/quadrotor_ws/src/simple_multi_sim` |

The architecture image uses illustrative `/ue1` and `/ue2` robot labels. The supplied quadrotor code uses `/robot_alpha` and `/robot_beta` ROS namespaces, mapped to Linux network namespaces `ue1` and `ue2` respectively; these names are separate scopes.

`workspaces/` contains custom source packages, not prebuilt full simulations. Third-party Hector packages are external. See [installation](../docs/INSTALLATION.md).
