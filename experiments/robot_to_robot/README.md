# Robot-to-robot leader–follower coordination

Video upload pending. See [upload instructions](../../docs/VIDEO_UPLOAD.md).

**Paper: Sections IV-C2 and V-B2; Figures 3b and 8.**

Two quadrotors operate as `robot_alpha` (leader/UE1) and `robot_beta` (follower/UE2). The leader takes off to 2 m and flies a predefined nine-waypoint mission. State `(x,y,z,yaw)` is sampled at 10 Hz and sent to the follower. The desired world-axis offset is `[-2,0,0]` m.

| Setting | Value in the paper |
|---|---|
| Horizontal / vertical / yaw gains | 0.5 / 0.8 / 0.5 |
| Maximum horizontal / vertical speed | 0.5 / 0.3 m/s |
| Maximum yaw rate | 0.5 rad/s |
| Trajectory comparison | Low versus high CQI |

Application code is in [BotSim/robot_to_robot](../../BotSim/robot_to_robot/). The launch package and leader flight driver are in `BotSim/workspaces/quadrotor_ws/src/simple_multi_sim`. [Launch instructions](../../docs/ROBOT_TO_ROBOT.md) describe the normal full-stack path.

`plot_tracking_error.py` plots the supplied follower log's error to its last **received** leader reference. The paper's Equation (2) is `||p_L(k) + d - p_F(k)||_2`. Establish a common time base and the intended leader reference before treating a CSV plot as a synchronized reproduction of that metric. Final comparison logs are not bundled.

## EdgeSim comparison

Section V-C/Figure 9 compares normal full-stack D2D forwarding with the partial MAC bypass, measuring latency and per-process CPU. See [EdgeSim](../../EdgeSim/). This source subset does not include a validated bypass build/runner and does not claim to reproduce that comparison.
