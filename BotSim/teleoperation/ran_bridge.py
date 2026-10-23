#!/usr/bin/env python3
"""
gnb_bridge.py  —  gNB (runs INSIDE Docker container: netbotsim_0)
=================================================================
Subscribes to ZMQ PUB on the Ubuntu host.
Routes each command to the correct UE namespace via UDP:

  topic b"ue1"  →  UDP to 172.16.0.2:5012  (ue1 namespace)
  topic b"ue2"  →  UDP to 172.16.0.3:5012  (ue2 namespace)

Run inside container:
  python3 gnb_bridge.py
  (or:  sudo ./scripts/netbotsim exec  then  python3 gnb_bridge.py)
"""

import os
import time
import socket
import zmq

# ─── CONFIG ───────────────────────────────────────────
HOST_ZMQ_IP   = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")   # Ubuntu host IP (docker bridge)
HOST_ZMQ_PORT = 9990

UE_ROUTES = {
    b"ue1": ("172.16.0.2", int(os.environ.get("NETBOTSIM_TELEOP_PORT", "5012"))),
    b"ue2": ("172.16.0.3", int(os.environ.get("NETBOTSIM_TELEOP_PORT", "5012"))),
}
# ──────────────────────────────────────────────────────


def main():
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://{HOST_ZMQ_IP}:{HOST_ZMQ_PORT}")

    for topic in UE_ROUTES:
        sub.setsockopt(zmq.SUBSCRIBE, topic)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[gNB] Connected to tcp://{HOST_ZMQ_IP}:{HOST_ZMQ_PORT}")
    for topic, route in UE_ROUTES.items():
        print(f"[RAN] {topic.decode()} → {route[0]}:{route[1]}")

    try:
        while True:
            parts = sub.recv_multipart()
            gnb_rx_ns = time.monotonic_ns()

            if len(parts) != 3:
                continue

            topic, header, payload = parts

            if topic not in UE_ROUTES:
                continue

            try:
                seq, host_tx_ns = header.decode("ascii").split(",")
                host_tx_ns = int(host_tx_ns)
            except Exception as e:
                print(f"[gNB] Header error: {e}")
                continue

            cmd = payload.decode("utf-8", errors="replace")
            ue_ip, ue_port = UE_ROUTES[topic]

            # UDP payload: "seq,host_tx_ns,gnb_rx_ns|cmd"
            gnb_tx_ns  = time.monotonic_ns()
            meta       = f"{seq},{host_tx_ns},{gnb_rx_ns},{gnb_tx_ns}|".encode("ascii")
            udp.sendto(meta + payload, (ue_ip, ue_port))

            latency_us = (gnb_rx_ns - host_tx_ns) / 1000
            print(f"[gNB] seq={seq}  {topic.decode()}  cmd={cmd}"
                  f"  → {ue_ip}:{ue_port}  lat={latency_us:.1f}µs")

    except KeyboardInterrupt:
        print("\n[gNB] Stopped.")
    finally:
        sub.close()
        udp.close()
        ctx.term()


if __name__ == "__main__":
    main()
