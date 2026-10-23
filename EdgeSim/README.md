# EdgeSim

**Paper: Section III-C — RAN-Side Edge Integration; Section V-C — D2D Communication with MAC Bypass.**

EdgeSim provides RAN-side support for edge-assisted communication and control. It builds on the upstream RAN controller/messaging architecture and supports evaluating conventional full-stack forwarding against an edge-assisted partial MAC-layer bypass.

## Normal and bypass paths in the paper

| Mode | Path and retained processing |
|---|---|
| Normal full stack | UE1 uplink, gNB PHY/MAC/RLC/PDCP, uplink GTP/core processing, then the conventional UE2 downlink |
| Partial MAC bypass | Intercept after gNB MAC reception, forward to `srs_spgw_sgi`, then core processing and the conventional UE2 downlink |

The bypass described in the paper skips selected gNB uplink processing. Source UE processing, gNB PHY/MAC reception, EPC, and full downlink remain active. This is not removal of the radio link.

## Release coverage

The external dependency is fetched under `vendor/network-stack`. Its `edgeric/` directory provides upstream controller/messaging and scheduling examples; its modified `srsran-enb/` and `srsran-ue/` trees provide network integration points. The working notes reference Redis scheduling selection (`scheduling_algorithm`, `Max CQI`) and an upstream scheduling application. These are reference integration details, not a validated standalone EdgeSim launch recipe.

This component directory documents the architecture and integration boundary. **A reviewed, validated final-paper bypass patch, resource monitor, and normal-versus-bypass runner are not bundled.** The current UE1-to-UE2 application adapters use the normal UDP route and do not activate a MAC bypass. No automatic bypass switch is exposed by the release launcher.

For a future comparison, hold CQI/traffic/workload constant, record which network build is active, align packet IDs, and report latency and per-process CPU separately. Do not infer a working bypass from an experiment folder name. See [robot-to-robot experiments](../experiments/robot_to_robot/) and [paper-to-code mapping](../docs/PAPER_TO_CODE.md).
