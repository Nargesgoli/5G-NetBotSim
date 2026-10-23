# 5G-NetSim

**Paper: Section III-A — Executable 5G Network Emulation.**

5G-NetSim is the framework's communication backbone: srsRAN base-station/UE processes, the core path, virtual-radio interfaces, per-UE network namespaces, and channel-quality configuration. The paper evaluates network effects through CQI, MCS, throughput, and packet timing.

## Included integration

- `radio_broker.py`: the supplied two-UE GNU Radio flowgraph.
- [Network launcher](../scripts/run-network): broker, EPC, base station, UE1, and UE2 roles.
- [External-source fetcher](../scripts/fetch-network-source): recorded public dependency revision.
- [Endpoint settings](../config/example.env): host/container application addresses.

The dependency is fetched into ignored `vendor/network-stack`; it is not redistributed as a large source tree in this release. The selected baseline starts an LTE eNodeB/EPC. The paper's 5G terminology is retained as the component name; it does not establish NR operation of this baseline. Exact final-paper configuration remains to be confirmed.

See [installation](../docs/INSTALLATION.md), [network startup](../docs/NETWORK_SETUP.md), and [release status](../docs/RELEASE_STATUS.md). After attachment, validate the application route before running either experimental workload.
