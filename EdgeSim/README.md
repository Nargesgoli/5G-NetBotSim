# EdgeSim

**Paper: Section III-C — RAN-Side Edge Integration.**

EdgeSim provides RAN-side support for edge intelligence, messaging, and scheduling within 5G-NetBotSim. It connects the network component's controller and scheduling interfaces with the robotic workloads.

## Integration

The external dependency is fetched under `vendor/network-stack`. Its `edgeric/` directory provides upstream controller/messaging and scheduling examples; its modified `srsran-enb/` and `srsran-ue/` trees provide network integration points.

The working notes reference Redis scheduling selection (`scheduling_algorithm`, `Max CQI`) and an upstream scheduling application. These are reference integration details, not a validated standalone EdgeSim launch recipe.

## Release coverage

This directory documents the component and its external-source integration. The application adapters use the cellular UDP communication path described in the [network setup guide](../docs/NETWORK_SETUP.md).

The repository's experiments cover [human-to-robot teleoperation](../experiments/human_to_robot/) and [robot-to-robot coordination](../experiments/robot_to_robot/). See the [paper-to-code map](../docs/PAPER_TO_CODE.md) for the available implementation assets.
