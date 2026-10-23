# Human-to-robot teleoperation

The paper's primary human-to-robot task is robotic-arm teleoperation. [Position control](../experiments/human_to_robot/position_control/) and [velocity-parameterized control](../experiments/human_to_robot/velocity_control/) are separate modes. This compact release currently provides the command/timing transport subset; it does not contain full manipulator/MoveIt execution assets.

## Available position-command timing path

After the network connectivity checks pass, source `config/example.env` in all application terminals. Start the UE receiver first, then the network-side bridge, then the host sender. One process per terminal:

| Location | Command |
|---|---|
| Container project root | `ip netns exec ue1 python3 experiments/human_to_robot/timing/ue1_receiver.py --name UE1 --port 5011 --out results/ue1_latency.csv` |
| Container project root | `./scripts/netbotsim run latency-bridge` |
| Host project root | `./scripts/netbotsim run latency-sender` |

The source cycles the six named arm targets. The bridge forwards to UE1 `172.16.0.2:5011`; receiver port selection must agree. UE2's receiver can be used for a separately configured UE2 route; the supplied default bridge does not broadcast to both UEs.

The timing receiver logs packet arrival. It does not command the robot or measure MoveIt task completion. These utilities cover L1–L3, not a complete L1–L5 result. Logs written by the launcher use `results/` unless overridden; manually invoked receiver output is relative to the container project root.

## Full arm experiment requirements

The complete position workflow requires the arm model, MoveIt configuration, the host execution node, and sequence-aligned execution-start/completion logs. The velocity workflow additionally requires the correct label/velocity payload, active-trajectory cancellation, replanning from the interrupted state, and reference trajectories for each command interval. These assets are pending in this compact source release.

See [measurement definitions](MEASUREMENTS.md) for the paper's latency stages.
