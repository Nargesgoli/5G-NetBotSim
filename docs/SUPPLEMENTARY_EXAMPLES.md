# Ground robot examples

Build the ground workspace after installing ROS/Gazebo dependencies. Source ROS, `BotSim/workspaces/ground_ws/devel/setup.bash`, and `config/example.env` in host terminals. Source the same env file in container application terminals. Validate the required network path first.

## Command teleoperation

Start one process per terminal, in this order:

| Location | Command |
|---|---|
| Host | `./scripts/netbotsim ros ground` |
| Host | `./scripts/netbotsim run ros-bridge` |
| Container | `./scripts/netbotsim run ran-bridge` |
| Container | `./scripts/netbotsim run ue-receiver` |
| Host | `./scripts/netbotsim run commander` |

The sender/receiver default UDP port is 5012. `NETBOTSIM_TELEOP_PORT` must agree at both ends. Commands target `/robot_alpha/cmd_vel` and `/robot_beta/cmd_vel`.

## Velocity replay

`BotSim/examples/ground_velocity_replay` is a separate ground example broadcasting `(vx,wz)` at 5 Hz. The `ros ground-follow` launch aligns headings with a 2 m initial gap; roles `leader`, `follower`, `ue1-injector`, and `ue2-receiver` run the applications. Start receivers before senders. This is distinct from the drone 10 Hz position/yaw workflow and has not been validated end to end in this release.

Manipulator/MoveIt simulation assets are external to this compact release. The latency sender's named pose payloads are example packet contents, not a complete manipulator demo.
