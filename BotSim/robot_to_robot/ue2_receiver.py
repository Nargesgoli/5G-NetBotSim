#!/usr/bin/env python3
"""
ue2_receiver.py  —  runs INSIDE Docker (netbotsim_0)
===============================================================
Robot-to-robot receiver for quadrotor follower side.

  1. Uses setns() to enter ue2 network namespace
  2. Binds UDP on 172.16.0.3:6000  ← receives leader state from ue1 via 5G
  3. Forwards payload via ZMQ PUB → host 172.17.0.1:9994
     where follower_control.py is listening

Payload format: "seq,tx_ns|x,y,z,yaw"

Run inside Docker:
  python3 ue2_receiver.py
"""

import os
import time
import socket
from ctypes import CDLL, get_errno

import zmq

# ─── CONFIG ───────────────────────────────────────────
UE2_NS      = "ue2"
UE2_BIND_IP = "172.16.0.3"
UE2_PORT    = 6000

HOST_IP       = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")
HOST_ZMQ_PORT = 9994

STALE_HARD_DROP_MS = 1000
ZMQ_SNDHWM         = 5
# ──────────────────────────────────────────────────────

libc   = CDLL("libc.so.6", use_errno=True)
_setns = libc.setns


def enter_ns(ns_name):
    original_fd = open("/proc/thread-self/ns/net")
    try:
        with open(f"/var/run/netns/{ns_name}") as target_fd:
            if _setns(target_fd.fileno(), 0) != 0:
                error = get_errno()
                raise OSError(error, os.strerror(error), ns_name)
    except BaseException:
        original_fd.close()
        raise
    return original_fd


def main():
    ns_path = f"/var/run/netns/{UE2_NS}"
    if not os.path.exists(ns_path):
        print(f"[ERROR] Namespace not found: {ns_path}")
        return

    # ZMQ PUB → host follower node
    # Create BEFORE entering namespace so it uses Docker bridge
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.setsockopt(zmq.SNDHWM, ZMQ_SNDHWM)
    pub.connect(f"tcp://{HOST_IP}:{HOST_ZMQ_PORT}")
    print(f"[UE2-R2R] ZMQ PUB → tcp://{HOST_IP}:{HOST_ZMQ_PORT}")
    time.sleep(0.5)

    # Enter ue2 namespace, then create UDP socket
    print(f"[UE2-R2R] Entering namespace {UE2_NS}...")
    original_fd = enter_ns(UE2_NS)
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((UE2_BIND_IP, UE2_PORT))
    print(f"[UE2-R2R] UDP bound on {UE2_BIND_IP}:{UE2_PORT} ✓")
    print(f"[UE2-R2R] Waiting for leader state from ue1 via 5G...\n")

    forwarded = dropped = 0

    try:
        while True:
            data, addr = udp_sock.recvfrom(4096)
            rx_ns = time.monotonic_ns()
            raw   = data.decode("utf-8", errors="replace").strip()

            # Parse "seq,tx_ns|x,y,z,yaw"
            seq_str = "?"
            age_ms  = None
            xyzw    = raw

            if "|" in raw:
                meta, xyzw = raw.split("|", 1)
                try:
                    seq_str, tx_ns_str = meta.split(",", 1)
                    age_ms = (rx_ns - int(tx_ns_str)) / 1_000_000
                except Exception as e:
                    print(f"[UE2-R2R] Meta parse error: {e}")

            # Hard-drop if extremely stale
            if age_ms is not None and age_ms > STALE_HARD_DROP_MS:
                dropped += 1
                print(f"[UE2-R2R] HARD-DROP  seq={seq_str:>4s}  "
                      f"age={age_ms:.0f}ms  [dropped: {dropped}]")
                continue

            # Forward "x,y,z,yaw" to follower node on host
            pub.send_string(xyzw)
            forwarded += 1

            if age_ms is not None:
                print(f"[UE2-R2R] FWD  seq={seq_str:>4s}  "
                      f"state={xyzw}  e2e={age_ms:.1f}ms")
            else:
                print(f"[UE2-R2R] FWD  raw={raw[:60]}")

    except KeyboardInterrupt:
        print(f"\n[UE2-R2R] Stopped.  forwarded={forwarded}  dropped={dropped}")
    finally:
        original_fd.close()
        udp_sock.close()
        pub.close()
        ctx.term()


if __name__ == "__main__":
    main()
