#!/usr/bin/env python3
import socket
import time
import csv
import os
import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True, help="UE1 or UE2 (used in prefix)")
    p.add_argument("--out", default=None, help="CSV path (optional). Example: /plots/ue1_latency.csv")
    p.add_argument("--port", type=int, default=5005, help="UDP listen port")
    args = p.parse_args()

    # Optional CSV
    writer = None
    f = None
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        #new_file = (not os.path.exists(args.out)) or (os.path.getsize(args.out) == 0)
        f = open(args.out, "w", newline="")
        writer = csv.writer(f)
        #if new_file:
        writer.writerow(["ue", "seq", "ubuntu_to_gnb_us", "gnb_proc_us", "gnb_to_ue_us", "total_us", "payload_bytes"])
        f.flush()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))

    # This line is optional; the important part is the per-packet print format
    print(f"[{args.name}] listening UDP on 0.0.0.0:{args.port}", flush=True)
    if args.out:
        print(f"[{args.name}] CSV logging to {args.out}", flush=True)

    while True:
        data, _ = sock.recvfrom(65535)
        ue_rx_ns = time.monotonic_ns()

        # Expected format: b"seq,ubuntu_send_ns,gnb_rx_ns,gnb_tx_ns|<payload>"
        meta, sep, payload = data.partition(b"|")
        if sep != b"|":
            continue

        try:
            seq, ubuntu_send_ns, gnb_rx_ns, gnb_tx_ns = meta.decode("ascii").split(",")
            ubuntu_send_ns = int(ubuntu_send_ns)
            gnb_rx_ns = int(gnb_rx_ns)
            gnb_tx_ns = int(gnb_tx_ns)
        except:
            continue

        ubuntu_to_gnb_us = (gnb_rx_ns - ubuntu_send_ns) / 1000.0
        gnb_proc_us      = (gnb_tx_ns - gnb_rx_ns) / 1000.0
        gnb_to_ue_us     = (ue_rx_ns - gnb_tx_ns) / 1000.0
        total_us         = (ue_rx_ns - ubuntu_send_ns) / 1000.0

        # ✅ EXACT “screenshot style” line:
        print(
            f"[{args.name}] seq={seq} "
            f"ubuntu->gnb={ubuntu_to_gnb_us:.1f}us "
            f"gnb_proc={gnb_proc_us:.1f}us "
            f"gnb->ue={gnb_to_ue_us:.1f}us "
            f"TOTAL={total_us:.1f}us "
            f"payload={len(payload)}B"
            f"UE rx={ue_rx_ns}",    
            flush=True
        )

        if writer:
            writer.writerow([args.name, int(seq), ubuntu_to_gnb_us, gnb_proc_us, gnb_to_ue_us, total_us, len(payload)])
            f.flush()

if __name__ == "__main__":
    main()

