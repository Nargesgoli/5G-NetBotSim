# Attribution

The external network dependency is [EdgeRIC-A-real-time-RIC](https://github.com/ucsdwcsng/EdgeRIC-A-real-time-RIC), recorded at commit `334c0ed9519d0d565007ec13f33a711cdf9a9fc3`. It supplies modified srsRAN code, scheduling, and messaging. Fetch it into the ignored `vendor/network-stack` folder; its own license files/notices apply. The public baseline is not asserted to include every local paper-experiment patch.

`5G-NetSim/radio_broker.py` retains its supplied generated-tool header and GPL-3.0 SPDX identifier. The GPL-3 text is under `LICENSES/`. This does not assign that license to every file.

The custom quadrotor launch package uses [Hector Quadrotor Noetic](https://github.com/RAFALAMAO/hector_quadrotor_noetic). This compact release excludes the Hector and other third-party ROS trees. Their own terms apply when installed separately. Original custom package metadata, including unresolved license fields, is preserved.

`docs/reference/automation.sh` and `docs/reference/dockerrun_edgeric_oaic.sh` are the supplied working-startup references. They retain historical names/paths and host-service changes. They are retained for comparison, not executed automatically. Integration adaptations are documented in `docs/RELEASE_STATUS.md`.
