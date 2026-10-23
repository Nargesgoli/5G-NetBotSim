# Validation status

Preparation checks are distinct from observations reported by the authors from their Ubuntu host on 7 October 2026.

| Item | Status |
|---|---|
| Application Python / launch wrappers | Syntax checked |
| Integration checks | Eight passed without live ROS or radio |
| EPC, eNodeB, UE1, UE2 compilation | Build output and executable paths confirmed by the user |
| Broker/core/base-station startup | Initialization logs confirmed by the user |
| Both UE attachments | Successful attachment at 172.16.0.2 and 172.16.0.3 |
| UE-to-gateway traffic | Replies from both UEs; one short UE2 probe lost one packet |
| UE1-to-UE2 traffic | Failed with redirects and 100% packet loss; unresolved |
| Robot applications with network | Not validated end to end in this release |
| Final paper metrics | Final data and numerical reproduction not included |
| Radio mode | Logs identify LTE eNodeB/EPC; validated 5G NR operation not established |

## Integration adaptations

Host addresses and output paths are configurable. Namespace entry failures are checked. Drone receive/broadcast loops use their socket-owning threads. CSV output accepts filename-only paths and plotting rejects missing/empty logs. These organized sources are adaptations rather than a claim of byte-for-byte identity with every original experiment script.

## Remaining work

- Match working startup/configuration and resolve UE-to-UE traffic.
- Confirm final network branch, local patches, CQI profiles, and paper-to-radio-mode mapping.
- Pin simulator dependencies and verify a clean installation.
- Validate quadrotor operation, message loss, and shutdown behavior.
- Verify result provenance, metric definitions, DOI, and paper/video links.
- Select the authors' original-code license while preserving dependency terms.

A suitable presentation label is **Initial code and documentation release**. A complete one-command reproduction is not claimed.
