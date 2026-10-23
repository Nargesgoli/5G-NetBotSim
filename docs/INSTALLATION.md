# Installation and dependencies

This initial source release is not yet a verified clean-machine reproduction recipe.

## Environment

- Ubuntu/Linux host with Docker, Python 3, CMake, Make, and Git.
- ROS 1 Noetic and compatible Gazebo on the host.
- Network container image used during integration: `nlpurnhyun/edgeric_base_oaic`.
- GNU Radio compatible with the supplied flowgraph (generated using 3.9.5.0).
- `iproute2` and namespace privileges inside the network container.

In a suitable Python environment:

```bash
python3 -m pip install -r requirements-apps.txt
```

This installs ordinary Python dependencies; it does not install ROS/Gazebo, GNU Radio, or native radio-stack dependencies.

## External network source

From the project root:

```bash
./scripts/fetch-network-source
./scripts/netbotsim doctor
sudo ./scripts/netbotsim shell
```

The fetch script clones the recorded upstream and checks out commit `334c0ed9519d0d565007ec13f33a711cdf9a9fc3` into `vendor/network-stack`. It refuses to overwrite existing source. This public baseline is not asserted to contain all local paper-experiment patches.

The privileged container uses host networking for the namespace workflow. The dependency is mounted at its historical internal path; the project is mounted at `/workspace/5G-NetBotSim`. Do not run competing original and release network processes on the same ports.

Inside the container:

```bash
cd /workspace/5G-NetBotSim
./scripts/netbotsim build
```

Compilation was confirmed on the authors' host during integration. Continue with [network startup](NETWORK_SETUP.md).

## ROS source subset

Only `simple_multi_sim` is bundled in the quadrotor workspace. Hector and other third-party ROS source trees, compiled workspaces, and manipulator/MoveIt assets are not bundled.

The quadrotor launch requires `hector_quadrotor_gazebo`. Use the authors' established Hector installation, or obtain [the referenced Hector Noetic source](https://github.com/RAFALAMAO/hector_quadrotor_noetic) and resolve its dependencies separately. The final working dependency revision and complete installation recipe are not yet pinned. Use an underlay or place required dependencies in the appropriate `src` directory; avoid conflicting package copies in a catkin workspace.

After ROS and simulator dependencies are available:

```bash
./scripts/netbotsim ros build-quadrotor
```

In each application terminal, source `config/example.env`. Its `127.0.0.1` address assumes host networking. A bridge-network deployment needs an address reachable at both endpoints. Environment settings do not configure CQI or radio attachment.
