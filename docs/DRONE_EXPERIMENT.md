# Drone leader–follower example

Requires a working quadrotor simulator and UE-to-UE connectivity. This workflow is not yet validated end to end in this release.

In every host application terminal, from the repository root:

```bash
source /opt/ros/noetic/setup.bash
source BotSim/workspaces/quadrotor_ws/devel/setup.bash
source config/example.env
```

In container application terminals, source `config/example.env` from `/workspace/5G-NetBotSim`.

With network processes running, start one application per terminal:

| Order | Location | Command |
|---|---|---|
| 1 | Host | `./scripts/netbotsim ros quadrotor` |
| 2 | Host | `./scripts/netbotsim run drone-follower` |
| 3 | Container | `./scripts/netbotsim run drone-ue2-receiver` |
| 4 | Container | `./scripts/netbotsim run drone-ue1-injector` |
| 5 | Host | `./scripts/netbotsim run drone-leader-state` |
| 6 | Host | `./scripts/netbotsim run drone-flight robot_alpha` |

The state observer broadcasts odometry; the separate flight driver moves the leader. Confirm Hector motor/controller engagement settings in the established simulator. Do not run the direct-ROS `follower_driver.py` together with the network follower: both command the same robot.

## State/control path

- Leader odometry: `/robot_alpha/ground_truth/state`; x/y/z/yaw broadcast at 10 Hz on ZMQ 9993.
- UE1 injector sends UDP to `172.16.0.3:6000`; UE2 forwards the state to host ZMQ 9994.
- Follower odometry: `/robot_beta/ground_truth/state`; commands: `/robot_beta/cmd_vel`.
- Target offset: `(-2,0,0)` in world axes relative to the received leader state.
- Injector stale threshold: 500 ms; receiver hard-drop threshold: 1000 ms.

## Results

CSV logs go to `results/` by default. Use distinct directories per trial because files are opened for writing. Set this in relevant host logging/plot terminals before launch:

```bash
export NETBOTSIM_RESULTS_DIR="$PWD/results/trial-01"
```

After a populated follower CSV exists:

```bash
./scripts/netbotsim run drone-plot
```

This plots offset error to the **received**, possibly delayed leader state. It is not automatically synchronized true-leader tracking error. Header-only logs are rejected. Final datasets and historical figures are not bundled. See [measurement definitions](MEASUREMENTS.md).
