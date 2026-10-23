#!/usr/bin/env python3
"""
ue2_receiver.py  —  runs INSIDE Docker (netbotsim_0)
==========================================================
Robot-to-robot receiver on the follower side.

  1. Uses setns() to enter ue2 network namespace
  2. Binds UDP on 172.16.0.3:6000  ← receives leader state from ue1 via 5G
  3. Forwards payload via ZMQ PUB → host 172.17.0.1:9994
     where follower.py is listening

Payload format (sent by ue1_injector.py):
  "seq,tx_ns|vx,wz"

FIX: Stale message detection at this end too.
  Even if ue1_injector.py drops obvious backlog, the UDP socket's
  kernel receive buffer can also accumulate packets. We check age here
  as a second line of defence and log (but still forward) borderline cases,
  or hard-drop if age is extreme.

Run inside Docker:
  python3 ue2_receiver.py
"""

import os
import time
import socket
import threading
from ctypes import CDLL, get_errno

import zmq

# ─── CONFIG ───────────────────────────────────────────
UE2_NS      = "ue2"
UE2_BIND_IP = "172.16.0.3"
UE2_PORT    = 6000

HOST_IP       = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")     # Docker bridge → host
HOST_ZMQ_PORT = 9994             # follower node listens here

# FIX: Hard-drop any packet whose age exceeds this limit (ms).
# The injector already filters at STALE_THRESHOLD_MS; this is
# a safety net for anything that slipped through the UDP buffer.
STALE_HARD_DROP_MS = 1000

# FIX: Limit ZMQ send buffer depth
ZMQ_SNDHWM = 5
# ──────────────────────────────────────────────────────

libc   = CDLL("libc.so.6", use_errno=True)
_setns = libc.setns


def enter_ns(ns_name):
    """Enter a UE namespace or fail without creating a socket in the wrong one."""
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

    # ZMQ PUB → host follower node (create BEFORE entering namespace
    # so the socket uses the default/Docker network, not ue2 tunnel)
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    # FIX: Low HWM so we don't build a backlog on this side either
    pub.setsockopt(zmq.SNDHWM, ZMQ_SNDHWM)
    pub.connect(f"tcp://{HOST_IP}:{HOST_ZMQ_PORT}")
    print(f"[UE2-R2R] ZMQ PUB → tcp://{HOST_IP}:{HOST_ZMQ_PORT} "
          f"(SNDHWM={ZMQ_SNDHWM})")
    time.sleep(0.5)   # slow-joiner

    # Enter ue2 namespace, then create UDP socket
    print(f"[UE2-R2R] Entering namespace {UE2_NS}...")
    my_fd    = enter_ns(UE2_NS)
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((UE2_BIND_IP, UE2_PORT))
    print(f"[UE2-R2R] UDP bound on {UE2_BIND_IP}:{UE2_PORT} ✓")
    print(f"[UE2-R2R] Stale hard-drop threshold: {STALE_HARD_DROP_MS} ms")
    print(f"[UE2-R2R] Waiting for leader state from ue1 via 5G...\n")

    forwarded = 0
    dropped   = 0

    try:
        while True:
            data, addr = udp_sock.recvfrom(4096)
            rx_ns = time.monotonic_ns()
            raw   = data.decode("utf-8", errors="replace").strip()

            # Parse "seq,tx_ns|vx,wz"
            seq_str = "?"
            e2e_us  = None
            age_ms  = None
            vxwz    = raw

            if "|" in raw:
                meta, vxwz = raw.split("|", 1)
                try:
                    parts   = meta.split(",")
                    seq_str = parts[0]
                    tx_ns   = int(parts[1])
                    e2e_us  = (rx_ns - tx_ns) / 1_000
                    age_ms  = e2e_us / 1_000
                except Exception as e:
                    print(f"[UE2-R2R] Meta parse error: {e}")

            # FIX: Hard-drop if age is extreme (safety net)
            if age_ms is not None and age_ms > STALE_HARD_DROP_MS:
                dropped += 1
                print(f"[UE2-R2R] HARD-DROP  seq={seq_str:>4s}  "
                      f"age={age_ms:.0f}ms > {STALE_HARD_DROP_MS}ms  "
                      f"[total dropped: {dropped}]")
                continue

            # Forward "vx,wz" to follower node on host via ZMQ
            pub.send_string(vxwz)
            forwarded += 1

            if e2e_us is not None:
                print(f"[UE2-R2R] FWD  seq={seq_str:>4s}  state={vxwz:>16s}"
                      f"  from={addr[0]}  e2e={e2e_us:.1f}µs")
            else:
                print(f"[UE2-R2R] FWD  raw={raw[:40]}")

    except KeyboardInterrupt:
        print(f"\n[UE2-R2R] Stopped.  forwarded={forwarded}  dropped={dropped}")
    finally:
        my_fd.close()
        udp_sock.close()
        pub.close()
        ctx.term()


if __name__ == "__main__":
    main()
