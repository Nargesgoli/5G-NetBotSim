# Packets and measurements

| Drone link | Format |
|---|---|
| Host to UE1 | ZMQ multipart: `[b"leader", b"seq,tx_ns", b"x,y,z,yaw"]` |
| UE1 UDP to UE2 | UTF-8: `seq,tx_ns|x,y,z,yaw` |
| UE2 to host follower | ZMQ string: `x,y,z,yaw` |

The transport consumes the timestamp/sequence; the follower receives only the four-value state. Stale thresholds assume a shared host monotonic clock domain. This is not a cross-machine clock-synchronization protocol.

Follower CSV columns are `t_sec,fx,fy,fz,lx,ly,lz,error`. Its logged error is the Euclidean norm of `follower_position - (received_leader_position + [-2,0,0])`. The stored `l*` values are last received references, possibly delayed. To evaluate true synchronized tracking, preserve timestamps and align leader/follower ground truth on a common clock. Independently re-zeroing CSV times does not synchronize the measurements.

## Timing utilities

`experiments/latency/` contains a host sender, a network-side bridge, and UE receivers. The bridge adds timestamps and forwards UDP. Its default route is UE1 port 5011; receivers default to 5005, so select the matching port explicitly:

```bash
ip netns exec ue1 python3 experiments/latency/ue1_receiver.py --name UE1 --port 5011 --out results/ue1_latency.csv
```

Run from the container project root. Use `--help` to inspect receiver options. CSV timestamp differences measure the instrumented application/bridge points, not physical-layer delay. Cross-host subtraction requires a separate synchronization design.

No final-paper CSVs, historical result figures, or invented measurements are bundled. The ground plot's optional `--demo` output is explicitly synthetic and labeled accordingly; its mean spatial separation is not claimed as verified offset tracking error. The drone plot requires real populated logs. CQI labels and directory names do not select radio conditions.
