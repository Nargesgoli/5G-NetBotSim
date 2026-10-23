#!/usr/bin/env python3
import os
import time
import csv
import zmq
import socket

# =========================
# CONFIG (EDIT IF NEEDED)
# =========================
HOST_ZMQ_IP = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")    # Ubuntu host IP (docker bridge side)
HOST_ZMQ_PORT = 9990
TOPIC = b"ctrl"

UE_IP = "172.16.0.2"          # UE namespace/container IP
UE_UDP_PORT = 5011

LOG_FILE = "gnb_bridge_log.csv"


def main():
    zmq_addr = f"tcp://{HOST_ZMQ_IP}:{HOST_ZMQ_PORT}"

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(zmq_addr)
    sub.setsockopt(zmq.SUBSCRIBE, TOPIC)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[gNB] SUB connected to {zmq_addr} topic={TOPIC.decode()}")
    print(f"[gNB] Forwarding UDP to UE {UE_IP}:{UE_UDP_PORT}")

    with open(LOG_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "seq", "cmd", "host_tx_ns",
            "gnb_rx_ns", "gnb_tx_ns",
            "L1_host_to_gnb_ns", "L2_gnb_proc_ns"
        ])

        try:
            while True:
                parts = sub.recv_multipart()
                gnb_rx_ns = time.monotonic_ns()

                if len(parts) != 3:
                    print(f"[gNB] Unexpected frame count: {len(parts)}")
                    continue

                topic_rx, header, payload = parts
                if topic_rx != TOPIC:
                    continue

                try:
                    seq_str, host_tx_ns_str = header.decode("ascii").split(",")
                    seq = int(seq_str)
                    host_tx_ns = int(host_tx_ns_str)
                except Exception as e:
                    print(f"[gNB] Header parse error: {e}")
                    continue

                cmd = payload.decode("utf-8", errors="replace")
                gnb_tx_ns = time.monotonic_ns()

                # UDP payload: seq,host_tx_ns,gnb_rx_ns,gnb_tx_ns|cmd
                meta = f"{seq},{host_tx_ns},{gnb_rx_ns},{gnb_tx_ns}|".encode("ascii")
                udp_packet = meta + payload
                udp.sendto(udp_packet, (UE_IP, UE_UDP_PORT))

                L1 = gnb_rx_ns - host_tx_ns
                L2 = gnb_tx_ns - gnb_rx_ns

                print(f"[gNB] seq={seq:04d} cmd={cmd} L1={L1}ns L2={L2}ns")
                w.writerow([seq, cmd, host_tx_ns, gnb_rx_ns, gnb_tx_ns, L1, L2])
                f.flush()

        except KeyboardInterrupt:
            print("\n[gNB] Stopped.")

    sub.close()
    udp.close()
    ctx.term()


if __name__ == "__main__":
    main()
