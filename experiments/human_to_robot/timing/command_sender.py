#!/usr/bin/env python3
import os
import time
import csv
import zmq

# =========================
# CONFIG (Ubuntu host -> gNB)
# =========================
HOST_BIND_IP = os.environ.get("NETBOTSIM_HOST_IP", "172.17.0.1")   # Host IP visible to gNB container
HOST_ZMQ_PORT = 9990
TOPIC = b"ctrl"

SEND_INTERVAL_SEC = 0.2
TOTAL_COMMANDS_TO_SEND = 10   # <--- total packets/commands to send
LOG_FILE = "ubuntu_tx_log.csv"

# Must match your MoveIt named targets on ROS host
COMMANDS = [
    "zero_state",
    "straight_up",
    "pick_object_pose",
    "lift_object_pose",
    "opposite_pose",
    "place_object_pose",
]


def main():
    pub_addr = f"tcp://{HOST_BIND_IP}:{HOST_ZMQ_PORT}"
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(pub_addr)

    print(f"[HOST] PUB bound on {pub_addr}, topic={TOPIC.decode()}")
    print("[HOST] Waiting 1.5s for gNB SUB...")
    time.sleep(1.5)  # PUB/SUB slow-joiner protection

    seq = 0
    cmd_idx = 0
    n_cmds = len(COMMANDS)

    with open(LOG_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "cmd", "host_tx_ns", "payload_len"])

        while seq < TOTAL_COMMANDS_TO_SEND:
            cmd = COMMANDS[cmd_idx % n_cmds]

            host_tx_ns = time.monotonic_ns()
            header = f"{seq},{host_tx_ns}".encode("ascii")
            payload = cmd.encode("utf-8")

            # Multipart: [topic, header, payload]
            pub.send_multipart([TOPIC, header, payload])

            print(f"[HOST] seq={seq:04d} cmd={cmd} host_tx_ns={host_tx_ns}")
            w.writerow([seq, cmd, host_tx_ns, len(payload)])
            f.flush()

            seq += 1
            cmd_idx += 1
            time.sleep(SEND_INTERVAL_SEC)

    pub.close()
    ctx.term()
    print(f"[HOST] Done. Sent {TOTAL_COMMANDS_TO_SEND} commands.")


if __name__ == "__main__":
    main()
