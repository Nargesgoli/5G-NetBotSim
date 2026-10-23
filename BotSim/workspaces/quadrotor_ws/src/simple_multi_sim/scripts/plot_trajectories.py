#!/usr/bin/env python3
"""
Plot leader-follower drone trajectories from CSV logs.

Usage:
  python3 plot_trajectories.py <leader_csv> <follower_csv>
  python3 plot_trajectories.py ~/catkin_ws_multi_robot/logs/robot_alpha_*.csv ~/catkin_ws_multi_robot/logs/robot_beta_*.csv

Generates 2D (XY) and 3D trajectory plots saved as PNG files.
"""

import sys
import csv
import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np


def load_csv(filepath):
    """Load trajectory CSV into dict of numpy arrays."""
    data = {'ros_time': [], 'x': [], 'y': [], 'z': [], 'phase': []}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data['ros_time'].append(float(row['ros_time']))
            data['x'].append(float(row['x']))
            data['y'].append(float(row['y']))
            data['z'].append(float(row['z']))
            data['phase'].append(row['phase'])
    for key in ['ros_time', 'x', 'y', 'z']:
        data[key] = np.array(data[key])
    return data


def plot_2d_xy(leader, follower, output_path):
    """Plot 2D XY trajectories."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    ax.plot(leader['x'], leader['y'], 'b-', linewidth=2, label='Leader (robot_alpha)', alpha=0.8)
    ax.plot(follower['x'], follower['y'], 'r--', linewidth=2, label='Follower (robot_beta)', alpha=0.8)

    # Mark start and end
    ax.plot(leader['x'][0], leader['y'][0], 'bo', markersize=12, label='Leader start')
    ax.plot(leader['x'][-1], leader['y'][-1], 'bs', markersize=12, label='Leader end')
    ax.plot(follower['x'][0], follower['y'][0], 'ro', markersize=12, label='Follower start')
    ax.plot(follower['x'][-1], follower['y'][-1], 'rs', markersize=12, label='Follower end')

    # Mark leader waypoints (where phase changes)
    prev_phase = ''
    for i, phase in enumerate(leader['phase']):
        if phase != prev_phase and 'waypoint' in phase:
            ax.annotate(phase, (leader['x'][i], leader['y'][i]),
                       fontsize=7, alpha=0.6, ha='center')
        prev_phase = phase

    ax.set_xlabel('X position (m)', fontsize=12)
    ax.set_ylabel('Y position (m)', fontsize=12)
    ax.set_title('Leader-Follower 2D Trajectory (XY Plane)', fontsize=14)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved: {output_path}")
    plt.close()


def plot_2d_altitude(leader, follower, output_path):
    """Plot altitude over time."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 5))

    # Normalize time to start at 0
    t0 = min(leader['ros_time'][0], follower['ros_time'][0])
    leader_t = leader['ros_time'] - t0
    follower_t = follower['ros_time'] - t0

    ax.plot(leader_t, leader['z'], 'b-', linewidth=2, label='Leader (robot_alpha)', alpha=0.8)
    ax.plot(follower_t, follower['z'], 'r--', linewidth=2, label='Follower (robot_beta)', alpha=0.8)

    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Altitude (m)', fontsize=12)
    ax.set_title('Leader-Follower Altitude Profile', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved: {output_path}")
    plt.close()


def plot_3d(leader, follower, output_path):
    """Plot 3D trajectories."""
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    ax.plot(leader['x'], leader['y'], leader['z'],
            'b-', linewidth=2, label='Leader (robot_alpha)', alpha=0.8)
    ax.plot(follower['x'], follower['y'], follower['z'],
            'r--', linewidth=2, label='Follower (robot_beta)', alpha=0.8)

    # Mark start and end
    ax.scatter(*[leader['x'][0]], *[leader['y'][0]], *[leader['z'][0]],
              c='blue', s=100, marker='o', label='Leader start')
    ax.scatter(*[leader['x'][-1]], *[leader['y'][-1]], *[leader['z'][-1]],
              c='blue', s=100, marker='s', label='Leader end')
    ax.scatter(*[follower['x'][0]], *[follower['y'][0]], *[follower['z'][0]],
              c='red', s=100, marker='o', label='Follower start')
    ax.scatter(*[follower['x'][-1]], *[follower['y'][-1]], *[follower['z'][-1]],
              c='red', s=100, marker='s', label='Follower end')

    # Project trajectories onto XY ground plane
    ax.plot(leader['x'], leader['y'], np.zeros_like(leader['z']),
            'b:', linewidth=0.5, alpha=0.3)
    ax.plot(follower['x'], follower['y'], np.zeros_like(follower['z']),
            'r:', linewidth=0.5, alpha=0.3)

    ax.set_xlabel('X (m)', fontsize=11)
    ax.set_ylabel('Y (m)', fontsize=11)
    ax.set_zlabel('Z (m)', fontsize=11)
    ax.set_title('Leader-Follower 3D Trajectory', fontsize=14)
    ax.legend(loc='upper left', fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved: {output_path}")
    plt.close()


def plot_following_error(leader, follower, offset_x, offset_y, output_path):
    """Plot the follower's tracking error over time."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 5))

    # Interpolate follower data to leader timestamps for comparison
    # Simple approach: use overlapping time range
    t_start = max(leader['ros_time'][0], follower['ros_time'][0])
    t_end = min(leader['ros_time'][-1], follower['ros_time'][-1])

    leader_mask = (leader['ros_time'] >= t_start) & (leader['ros_time'] <= t_end)
    follower_mask = (follower['ros_time'] >= t_start) & (follower['ros_time'] <= t_end)

    # Subsample to shorter length
    l_x = leader['x'][leader_mask]
    l_y = leader['y'][leader_mask]
    f_x = follower['x'][follower_mask]
    f_y = follower['y'][follower_mask]
    min_len = min(len(l_x), len(f_x))
    l_x, l_y = l_x[:min_len], l_y[:min_len]
    f_x, f_y = f_x[:min_len], f_y[:min_len]

    # Desired follower position
    desired_x = l_x + offset_x
    desired_y = l_y + offset_y

    error = np.sqrt((f_x - desired_x)**2 + (f_y - desired_y)**2)

    t0 = leader['ros_time'][leader_mask][0]
    time_axis = leader['ros_time'][leader_mask][:min_len] - t0

    ax.plot(time_axis, error, 'g-', linewidth=1.5, alpha=0.8)
    ax.axhline(y=np.mean(error), color='k', linestyle='--', alpha=0.5,
               label=f'Mean error: {np.mean(error):.3f}m')

    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Tracking Error (m)', fontsize=12)
    ax.set_title('Follower Tracking Error', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved: {output_path}")
    plt.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 plot_trajectories.py <leader.csv> <follower.csv>")
        sys.exit(1)

    leader_csv = sys.argv[1]
    follower_csv = sys.argv[2]

    print(f"Loading leader:   {leader_csv}")
    print(f"Loading follower: {follower_csv}")

    leader = load_csv(leader_csv)
    follower = load_csv(follower_csv)

    out_dir = os.path.dirname(leader_csv)

    plot_2d_xy(leader, follower, os.path.join(out_dir, 'trajectory_2d_xy.png'))
    plot_2d_altitude(leader, follower, os.path.join(out_dir, 'trajectory_altitude.png'))
    plot_3d(leader, follower, os.path.join(out_dir, 'trajectory_3d.png'))
    plot_following_error(leader, follower, -2.0, 0.0, os.path.join(out_dir, 'tracking_error.png'))

    print(f"\nAll plots saved to: {out_dir}")
