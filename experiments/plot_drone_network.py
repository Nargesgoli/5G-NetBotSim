#!/usr/bin/env python3
"""Plot received-state offset error from a real drone follower CSV."""
import argparse
import csv
from pathlib import Path


def load_follower(path):
    required = {"t_sec", "fx", "fy", "fz", "lx", "ly", "lz", "error"}
    with open(path, newline="") as source:
        reader = csv.DictReader(source)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Follower CSV has an unexpected schema")
        rows = list(reader)
    if not rows:
        raise ValueError("Follower CSV contains no samples; a header alone cannot produce results")
    return [{key: float(row[key]) for key in required} for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follower", default="follower_quad.csv")
    parser.add_argument("--out", default="drone_received_state_error.png")
    args = parser.parse_args()
    rows = load_follower(args.follower)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axis = plt.subplots(figsize=(7, 3.5))
    axis.plot([r["t_sec"] for r in rows], [r["error"] for r in rows], color="black")
    axis.set_xlabel("Time since follower log start (s)")
    axis.set_ylabel("Offset error to received state (m)")
    axis.grid(alpha=.25)
    figure.tight_layout()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=200)
    plt.close(figure)
    mean = sum(r["error"] for r in rows) / len(rows)
    print(f"Samples: {len(rows)}; mean offset error to received state: {mean:.6f} m")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
