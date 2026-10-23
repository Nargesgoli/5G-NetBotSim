#!/usr/bin/env python3
"""
robot_commander.py  —  Ubuntu HOST
====================================
Sends robot movement commands to the gNB (inside Docker) via ZMQ PUB.
Two topics are used — one per UE/robot — sent sequentially with per-message timestamps.

  topic b"ue1"  →  gNB → UE1 ns → robot_alpha
  topic b"ue2"  →  gNB → UE2 ns → robot_beta

Run:
  python3 robot_commander.py

Commands: forward | backward | left | right | stop
"""

import os
import time
import zmq

# ─── CONFIG ───────────────────────────────────────────
HOST_BIND_IP  = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")   # Docker bridge IP (host side)
HOST_ZMQ_PORT = 9990
SEND_INTERVAL = 1.0             # seconds between command pairs
# ──────────────────────────────────────────────────────

# Each tuple: (cmd_for_robot_alpha, cmd_for_robot_beta)
COMMAND_PAIRS = [
    ("forward",  "forward"),   # both robots forward
    ("left",     "right"),     # alpha turns left, beta turns right
    ("forward",  "backward"),  # alpha forward, beta backward
    ("stop",     "stop"),      # both stop
]


def send_command(pub, topic: bytes, seq: int, cmd: str):
    tx_ns  = time.monotonic_ns()
    header = f"{seq},{tx_ns}".encode("ascii")
    pub.send_multipart([topic, header, cmd.encode("utf-8")])
    print(f"[HOST] seq={seq:04d}  topic={topic.decode()}  cmd={cmd}")


def main():
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://{HOST_BIND_IP}:{HOST_ZMQ_PORT}")

    print(f"[HOST] PUB bound on tcp://{HOST_BIND_IP}:{HOST_ZMQ_PORT}")
    print("[HOST] Waiting 1.5s for gNB to connect...")
    time.sleep(1.5)

    seq = 0
    for (cmd_alpha, cmd_beta) in COMMAND_PAIRS:
        # ZeroMQ sockets must not be shared by concurrent sender threads.
        send_command(pub, b"ue1", seq, cmd_alpha)
        send_command(pub, b"ue2", seq, cmd_beta)

        seq += 1
        time.sleep(SEND_INTERVAL)

    print(f"[HOST] Done — sent {seq} command pairs.")
    pub.close()
    ctx.term()


if __name__ == "__main__":
    main()
