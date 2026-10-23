#!/usr/bin/env python3
"""
7_plot_platooning.py  —  Ubuntu HOST
======================================
Reads leader_trajectory_{cqi}.csv and follower_trajectory_{cqi}.csv
for high, mid, low CQI conditions and plots superimposed trajectories
as a 3-subplot figure suitable for the paper (Fig. 7).

FIX: If follower CSV still contains a pre-command frozen period
(e.g. from older data), it is automatically trimmed before plotting.
The trimming threshold is: skip rows where both vx==0 and wz==0
at the start, as long as position hasn't changed from spawn.

Run:
  python3 7_plot_platooning.py
  python3 7_plot_platooning.py --save   # save as PNG + PDF

Install:
  pip3 install matplotlib pandas numpy scipy
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

SAVE = "--save" in sys.argv
DEMO = "--demo" in sys.argv

# ─── IEEE paper style ────────────────────────────────
matplotlib.rcParams.update({
    "font.family":      "serif",
    "font.size":        9,
    "axes.labelsize":   9,
    "axes.titlesize":   9,
    "legend.fontsize":  8,
    "xtick.labelsize":  8,
    "ytick.labelsize":  8,
    "xtick.direction":  "in",
    "ytick.direction":  "in",
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "lines.linewidth":  1.5,
})

LEADER_COLOR    = "#1f77b4"
FOLLOWER_COLORS = {
    "high": "#2ca02c",
    "mid":  "#ff7f0e",
    "low":  "#d62728",
}
CQI_LABELS = ["high", "mid", "low"]
CQI_TITLES = ["High CQI", "Mid CQI", "Low CQI"]

# Max age (ms) to consider a follower sample "active" relative to leader duration
# Used only for legacy CSVs that weren't produced with the fixed follower node.
STALE_TRIM_ENABLED = True


def load(prefix, cqi):
    path = f"{prefix}_trajectory_{cqi}.csv"
    if not os.path.exists(path):
        if DEMO:
            return None
        raise FileNotFoundError(f"Missing experiment log: {path}. Use --demo only for synthetic previews.")
    return pd.read_csv(path)


def trim_follower(df):
    """
    FIX: Remove leading frozen rows from legacy follower CSVs.

    The old follower node started logging at node init, before any commands
    arrived. This produced a long prefix of rows where the robot was stationary
    (vx==0, wz==0) and had not yet moved from its spawn position.

    Strategy:
      1. Find the index where vx or wz first becomes non-zero.
      2. Trim everything before that index.
      3. Re-zero t_sec so t=0 is the moment the first command was received.

    If the CSV was produced with the fixed follower node, t_sec already starts
    at 0 when the first command arrives, so this function is a no-op.
    """
    if not STALE_TRIM_ENABLED:
        return df

    # Check if t_sec already starts near 0 — then it's already fixed
    if df["t_sec"].iloc[0] < 1.0:
        return df

    # Find first row with a non-zero velocity command
    moving = df[(df["vx"] != 0) | (df["wz"] != 0)]
    if moving.empty:
        print("[WARN] Follower has no non-zero commands — returning as-is")
        return df

    first_idx = moving.index[0]
    df_trimmed = df.loc[first_idx:].copy()
    df_trimmed["t_sec"] = df_trimmed["t_sec"] - df_trimmed["t_sec"].iloc[0]
    print(f"[trim_follower] Removed {first_idx} frozen rows. "
          f"Active duration: {df_trimmed['t_sec'].max():.1f}s")
    return df_trimmed


def resample_to_common_time(leader_df, follower_df):
    """Interpolate both onto a shared time axis covering their overlap."""
    t_min = max(leader_df["t_sec"].min(),   follower_df["t_sec"].min())
    t_max = min(leader_df["t_sec"].max(),   follower_df["t_sec"].max())

    if t_max <= t_min:
        print("[WARN] No time overlap between leader and follower after trimming.")
        print(f"       Leader:   {leader_df['t_sec'].min():.1f} – {leader_df['t_sec'].max():.1f}s")
        print(f"       Follower: {follower_df['t_sec'].min():.1f} – {follower_df['t_sec'].max():.1f}s")
        raise ValueError("Leader/follower logs have no overlapping time interval.")

    t_common = np.linspace(t_min, t_max, 300)

    def interp(df, col):
        return interp1d(df["t_sec"], df[col],
                        bounds_error=False, fill_value="extrapolate")(t_common)

    return (t_common,
            interp(leader_df,   "x"), interp(leader_df,   "y"),
            interp(follower_df, "x"), interp(follower_df, "y"))


def mean_deviation(lx, ly, fx, fy):
    return np.mean(np.sqrt((lx - fx)**2 + (ly - fy)**2))


def synthetic_data(cqi):
    """Generate reproducible demo data when real logs aren't available."""
    t  = np.linspace(0, 22, 300)
    dt = t[1] - t[0]
    # Leader heading and position
    yaw = np.zeros(len(t))
    lx  = np.zeros(len(t))
    ly  = np.zeros(len(t))
    vx_seq = np.where(t < 4,  0.3,
             np.where(t < 5.5, 0.0,
             np.where(t < 8,   0.3,
             np.where(t < 9,   0.0,
             np.where(t < 11,  0.3,
             np.where(t < 13,  0.0,
             np.where(t < 14.5,0.3,
             np.where(t < 16,  0.0,
             np.where(t < 18,  0.3, 0.0)))))))))
    wz_seq = np.where(t < 4,   0.0,
             np.where(t < 5.5, 0.5,
             np.where(t < 8,   0.0,
             np.where(t < 9,  -0.5,
             np.where(t < 11,  0.0,
             np.where(t < 13,  0.5,
             np.where(t < 14.5, 0.0,
             np.where(t < 16, -0.5,
             np.where(t < 18,  0.0, 0.0)))))))))
    for i in range(1, len(t)):
        yaw[i] = yaw[i-1] + wz_seq[i-1] * dt
        lx[i]  = lx[i-1]  + vx_seq[i-1] * np.cos(yaw[i-1]) * dt
        ly[i]  = ly[i-1]  + vx_seq[i-1] * np.sin(yaw[i-1]) * dt

    lag   = {"high": 2,    "mid": 6,    "low": 14   }[cqi]
    noise = {"high": 0.01, "mid": 0.03, "low": 0.07 }[cqi]
    rng   = np.random.default_rng(42)
    fx    = np.roll(lx, lag) + rng.normal(0, noise, len(lx))
    fy    = np.roll(ly, lag) + rng.normal(0, noise, len(ly))
    fx[:lag] = lx[0]
    fy[:lag] = ly[0]
    return t, lx, ly, fx, fy


# ─── Build figure ────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.6))
fig.subplots_adjust(wspace=0.35)

for ax, cqi, title in zip(axes, CQI_LABELS, CQI_TITLES):
    leader_df   = load("leader",   cqi)
    follower_df = load("follower", cqi)

    if not DEMO and leader_df is not None and follower_df is not None:
        # FIX: trim legacy frozen prefix before resampling
        follower_df = trim_follower(follower_df)
        t, lx, ly, fx, fy = resample_to_common_time(leader_df, follower_df)
    else:
        t, lx, ly, fx, fy = synthetic_data(cqi)

    dev = mean_deviation(lx, ly, fx, fy)

    ax.plot(lx, ly, color=LEADER_COLOR,
            label="Leader", zorder=3)
    ax.plot(fx, fy, color=FOLLOWER_COLORS[cqi],
            linestyle="--", label="Follower", zorder=2)

    # Mark start points
    ax.plot(lx[0], ly[0], "o", color=LEADER_COLOR,
            markersize=5, zorder=4)
    ax.plot(fx[0], fy[0], "o", color=FOLLOWER_COLORS[cqi],
            markersize=5, zorder=4)

    # Mark end points
    ax.plot(lx[-1], ly[-1], "s", color=LEADER_COLOR,
            markersize=5, zorder=4)
    ax.plot(fx[-1], fy[-1], "s", color=FOLLOWER_COLORS[cqi],
            markersize=5, zorder=4)

    ax.set_title(f"{title}\nMean separation = {dev:.3f} m", pad=4)
    ax.set_xlabel("X Position (m)")
    if ax is axes[0]:
        ax.set_ylabel("Y Position (m)")
    ax.legend(loc="upper right", framealpha=0.7)
    ax.set_aspect("equal", adjustable="datalim")

fig.suptitle(
    ("SYNTHETIC DEMO — " if DEMO else "") +
    "Leader–Follower Platooning Trajectories under Different CQI Conditions",
    fontsize=9, y=1.02
)

if SAVE:
    output_stem = "synthetic_demo" if DEMO else "platooning_trajectories"
    fig.savefig(output_stem + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(output_stem + ".pdf",            bbox_inches="tight")
    print(f"Saved {output_stem}.png and .pdf")
else:
    plt.tight_layout()
    plt.show()
