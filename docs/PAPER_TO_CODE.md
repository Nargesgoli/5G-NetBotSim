# Paper-to-code map

This map follows the supplied accepted manuscript, **5G-NetBotSim: A Synchronized Intelligent Co-Simulation Framework for Connected Robots over ROS and srsRAN-based 5G Network**. The supplied architecture image is copied unchanged to `docs/assets/5g-netbotsim.jpg`.

| Paper item | Repository location | Current coverage |
|---|---|---|
| Section III-A: 5G-NetSim | `5G-NetSim/`, `scripts/run-network` | Radio broker, source integration, launch guide; external baseline radio mode documented |
| Section III-B: BotSim | `BotSim/` | ROS applications, custom quadrotor packages; complete arm simulation external |
| Section III-C: EdgeSim | `EdgeSim/` | RAN-side controller, messaging, and scheduling integration guide |
| Section III-D: timing | `experiments/human_to_robot/timing/`, `docs/MEASUREMENTS.md` | Packet stages L1–L3 available; complete L4–L5 arm event logging pending |
| IV-C1, V-B1, Figs. 3a/6/7: human-to-robot | `experiments/human_to_robot/`, `BotSim/human_to_robot/` | Position timing code; position/velocity protocols; full MoveIt workflows pending |
| IV-C2, V-B2, Figs. 3b/8: robot-to-robot | `experiments/robot_to_robot/`, `BotSim/robot_to_robot/` | Quadrotor state/control/transport and received-reference plot |

The architecture figure uses generic robot/UE namespace labels. The actual example ROS topics use `robot_alpha`/`robot_beta`, separately mapped to Linux UE namespaces `ue1`/`ue2`.

The paper's platform is Ubuntu 20.04.6, ROS Noetic, Gazebo 11.15.1, and a single co-located host. Table III reports one base station, two UEs, 10 MHz bandwidth, 15 kHz spacing, 1 ms TTI, MAX CQI scheduling, and low/medium/high CQI regimes. This describes the manuscript configuration; it is not a claim that all values are already reproduced by the selected public baseline. See `RELEASE_STATUS.md` for integration evidence.
