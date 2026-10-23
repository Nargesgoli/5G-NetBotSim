#!/usr/bin/env python3
"""
ue1_injector.py  —  runs INSIDE Docker (netbotsim_0)
===========================================================
Receives leader quadrotor state (x,y,z,yaw) from host via ZMQ,
then injects it into the 5G network by sending UDP from inside
the ue1 namespace toward ue2 (172.16.0.3:6000).

Flow:
  leader_state.py (host)
    → ZMQ PUB 172.17.0.1:9993
      → [this script] ZMQ SUB
        → setns(ue1)
          → UDP sendto 172.16.0.3:6000
            → 5G uplink → EPC → 5G downlink
              → ue2 namespace
                → ue2_receiver.py

Run inside Docker:
  python3 ue1_injector.py
"""

import os
import time
import socket
from ctypes import CDLL, get_errno

import zmq

# ─── CONFIG ───────────────────────────────────────────
HOST_IP         = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")
LEADER_ZMQ_PORT = 9993

UE1_NS      = "ue1"
UE1_BIND_IP = "172.16.0.2"
UE2_IP      = "172.16.0.3"
UE2_PORT    = 6000

STALE_THRESHOLD_MS = 500
ZMQ_RCVHWM         = 5
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
    ns_path = f"/var/run/netns/{UE1_NS}"
    if not os.path.exists(ns_path):
        print(f"[ERROR] Namespace not found: {ns_path}")
        print(f"        Make sure srsRAN is running and UEs are attached.")
        return

    # ZMQ SUB — connect to host leader node
    # Must be created BEFORE entering ue1 namespace
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.RCVHWM, ZMQ_RCVHWM)
    sub.connect(f"tcp://{HOST_IP}:{LEADER_ZMQ_PORT}")
    sub.setsockopt(zmq.SUBSCRIBE, b"leader")
    print(f"[UE1-INJ] ZMQ SUB connected to tcp://{HOST_IP}:{LEADER_ZMQ_PORT}")
    time.sleep(0.5)

    # Enter ue1 namespace, then create UDP socket
    print(f"[UE1-INJ] Entering namespace {UE1_NS}...")
    original_fd = enter_ns(UE1_NS)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((UE1_BIND_IP, 0))
    print(f"[UE1-INJ] UDP socket bound inside {UE1_NS} ({UE1_BIND_IP})")
    print(f"[UE1-INJ] Forwarding to {UE2_IP}:{UE2_PORT} via 5G")
    print(f"[UE1-INJ] Stale drop threshold: {STALE_THRESHOLD_MS} ms\n")

    dropped = forwarded = 0

    try:
        while True:
            parts = sub.recv_multipart()
            if len(parts) != 3:
                continue

            topic, header, payload = parts
            meta = header.decode("ascii")    # "seq,tx_ns"
            xyzw = payload.decode("utf-8")   # "x,y,z,yaw"

            # Check message age
            try:
                seq, tx_ns = meta.split(",")
                age_ms = (time.monotonic_ns() - int(tx_ns)) / 1_000_000

                if age_ms > STALE_THRESHOLD_MS:
                    dropped += 1
                    print(f"[UE1-INJ] DROP  seq={seq:>4s}  age={age_ms:.0f}ms  "
                          f"[dropped: {dropped}]")
                    continue

            except Exception as e:
                print(f"[UE1-INJ] Header parse error: {e} — forwarding anyway")
                seq    = "?"
                age_ms = 0.0

            # Forward as "seq,tx_ns|x,y,z,yaw"
            datagram = f"{meta}|{xyzw}".encode("utf-8")
            udp.sendto(datagram, (UE2_IP, UE2_PORT))
            forwarded += 1
            print(f"[UE1-INJ] FWD  seq={seq:>4s}  age={age_ms:5.1f}ms  "
                  f"state={xyzw}")

    except KeyboardInterrupt:
        print(f"\n[UE1-INJ] Stopped.  forwarded={forwarded}  dropped={dropped}")
    finally:
        original_fd.close()
        udp.close()
        sub.close()
        ctx.term()


if __name__ == "__main__":
    main()
