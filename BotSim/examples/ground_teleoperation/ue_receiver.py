#!/usr/bin/env python3
"""
ue_receiver.py  —  UE-side (runs INSIDE Docker container: netbotsim_0)
=======================================================================
Fix: socket must be created AND bound inside the namespace context,
     not just bound. The OS assigns the socket to the current net
     namespace at creation time, not at bind time.

Two threads — one per UE namespace:

  Thread 1:
    enters ue1 namespace → creates+binds UDP on 172.16.0.2:5012
    stays in namespace to recv → ZMQ PUB to host 172.17.0.1:9991

  Thread 2:
    enters ue2 namespace → creates+binds UDP on 172.16.0.3:5012
    stays in namespace to recv → ZMQ PUB to host 172.17.0.1:9992
"""

import os
import socket
import threading
import time
from ctypes import CDLL, get_errno

import zmq

# ─── CONFIG ───────────────────────────────────────────
HOST_IP = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")   # Ubuntu host (docker bridge)

UE_CONFIG = [
    {
        "ns_name":  "ue1",
        "bind_ip":  "172.16.0.2",
        "udp_port": int(os.environ.get("NETBOTSIM_TELEOP_PORT", "5012")),
        "zmq_port": 9991,
        "robot":    "robot_alpha",
    },
    {
        "ns_name":  "ue2",
        "bind_ip":  "172.16.0.3",
        "udp_port": int(os.environ.get("NETBOTSIM_TELEOP_PORT", "5012")),
        "zmq_port": 9992,
        "robot":    "robot_beta",
    },
]
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


def leave_ns(original_fd):
    try:
        if _setns(original_fd.fileno(), 0) != 0:
            error = get_errno()
            raise OSError(error, os.strerror(error), "restore network namespace")
    finally:
        original_fd.close()


def ue_worker(cfg: dict, zmq_ctx: zmq.Context):
    ns_name  = cfg["ns_name"]
    bind_ip  = cfg["bind_ip"]
    udp_port = cfg["udp_port"]
    zmq_port = cfg["zmq_port"]
    robot    = cfg["robot"]

    # ── ZMQ PUB to host — created in default namespace ──────────
    pub = zmq_ctx.socket(zmq.PUB)
    pub.connect(f"tcp://{HOST_IP}:{zmq_port}")
    print(f"[{ns_name}] ZMQ PUB → tcp://{HOST_IP}:{zmq_port}  ({robot})")
    time.sleep(0.5)   # slow-joiner

    # ── Enter UE namespace, then create AND bind the UDP socket ──
    # IMPORTANT: socket() must be called AFTER setns(), not before.
    # The kernel assigns a socket to the current netns at creation time.
    print(f"[{ns_name}] Entering namespace...")
    my_fd = enter_ns(ns_name)

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((bind_ip, udp_port))
    print(f"[{ns_name}] UDP bound on {bind_ip}:{udp_port} ✓")

    # Stay inside the namespace for the entire receive loop
    try:
        while True:
            data, _ = udp_sock.recvfrom(4096)
            raw = data.decode("utf-8", errors="replace")

            # Packet format from gNB: "seq,host_tx_ns,gnb_rx_ns,gnb_tx_ns|cmd"
            if "|" in raw:
                meta_str, cmd = raw.split("|", 1)
                cmd = cmd.strip()
                try:
                    parts   = meta_str.split(",")
                    seq     = parts[0]
                    host_tx = int(parts[1])
                    e2e_us  = (time.monotonic_ns() - host_tx) / 1000
                    print(f"[{ns_name}] seq={seq}  cmd={cmd}  e2e={e2e_us:.1f}µs → {robot}")
                except Exception:
                    pass
            else:
                cmd = raw.strip()

            # Forward command to host ROS bridge via ZMQ
            pub.send_string(cmd)

    except KeyboardInterrupt:
        pass
    finally:
        leave_ns(my_fd)
        udp_sock.close()
        pub.close()
        print(f"[{ns_name}] Stopped.")


def main():
    # Verify namespaces exist before starting threads
    for cfg in UE_CONFIG:
        ns_path = f"/var/run/netns/{cfg['ns_name']}"
        if not os.path.exists(ns_path):
            print(f"[ERROR] Namespace not found: {ns_path}")
            print(f"        Make sure UEs are running and attached.")
            print("        An empty namespace is insufficient; attach the UE first.")
            return

    ctx = zmq.Context()
    threads = []
    for cfg in UE_CONFIG:
        t = threading.Thread(target=ue_worker, args=(cfg, ctx), daemon=True)
        t.start()
        threads.append(t)

    print("[UE Receiver] Both UE workers running. Ctrl+C to stop.\n")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n[UE Receiver] Stopped.")
    finally:
        ctx.term()


if __name__ == "__main__":
    main()
