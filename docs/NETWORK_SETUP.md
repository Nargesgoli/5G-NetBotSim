# Network startup

First fetch and build the external source; see [installation](INSTALLATION.md). This configuration runs LTE eNodeB/EPC and two UEs. End-to-end connectivity remains unresolved in this release.

## Container terminals

From the host repository root, create the container:

```bash
sudo ./scripts/netbotsim shell
```

Open additional container terminals from the host with:

```bash
sudo ./scripts/netbotsim exec
```

Within the container work from `/workspace/5G-NetBotSim`. Run one process per terminal, in order:

```bash
./scripts/netbotsim network broker
./scripts/netbotsim network epc
./scripts/netbotsim network enb
```

Leave the broker waiting at `Press Enter to quit:`; Enter stops it. Startup messages are not proof of UE attachment.

In a free container terminal, inspect namespaces with `ip netns list`. Create each only if absent:

```bash
ip netns add ue1
ip netns add ue2
```

Start each UE in its own terminal:

```bash
./scripts/netbotsim network ue1
```

```bash
./scripts/netbotsim network ue2
```

The broker may wait for both UEs. Check successful attachment messages and actual namespace addresses.

## Endpoints

| Endpoint | Address / ports |
|---|---|
| Core gateway | `172.16.0.1` |
| UE1 / namespace ue1 | `172.16.0.2` |
| UE2 / namespace ue2 | `172.16.0.3` |
| Base-station radio | TX 2101 / RX 2100 |
| UE1 radio | TX 2001 / RX 2000 |
| UE2 radio | TX 2011 / RX 2010 |
| Base sample rate | 23.04e6 |

## Connectivity gate

In a free container terminal:

```bash
ip netns exec ue1 ip addr
ip netns exec ue2 ip addr
ip netns exec ue1 ping -c 5 -W 2 172.16.0.1
ip netns exec ue2 ping -c 5 -W 2 172.16.0.1
ip netns exec ue1 ping -c 5 -W 2 172.16.0.3
ip netns exec ue2 ping -c 5 -W 2 172.16.0.2
```

During integration both UEs attached and reached the gateway, but UE1-to-UE2 ping failed with redirects. Gateway replies do not establish UE-to-UE communication. Proceed to cellular robot experiments only after the required path works.

## Working-deployment differences

The supplied original UE launcher kept core-to-UE pings running; these foreground wrappers do not. Original `automation.sh` used tmux for startup. The original Docker launcher stopped host `firewalld` and enabled forwarding. These are observed differences, not confirmed causes or fixes for the connectivity problem.

Original automation/Docker scripts are retained in `docs/reference/` for comparison, not automatic execution. They use historical paths and include host service/display changes. Do not apply blanket firewall changes or run competing radio instances to troubleshoot. Compare working configuration, namespace routes, forwarding, and radio logs first.

Current public-baseline UE parameters select upstream traces. Integration logs showed UE1 CQI range 1–7, UE2 range 8–15, and a 2 ms CQI period. Final-paper trace/settings provenance remains to be confirmed.

Stop network processes with Ctrl+C in their own terminals (broker also stops with Enter). Stop the processes before exiting the primary container shell, since the container uses `--rm`. The wrappers do not automatically delete namespaces or alter persistent host firewall rules.
