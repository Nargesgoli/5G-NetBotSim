#!/bin/bash


apt-get update
apt-get install -y tmux
pip3 install opencv-python

sleep 10

# Create a new tmux session named 'automation' and detach
tmux new-session -d -s automation

# Split the first pane horizontally (left and right split)
tmux split-window -h -t automation:0.0

# Split both the left and right panes vertically to create four equal-sized panes
tmux split-window -v -t automation:0.0
tmux split-window -v -t automation:0.1

# Pane 0: Execute python3 top_block_2ue_no_gui.py
tmux send-keys -t automation:0.0 'python3 top_block_2ue_no_gui.py' C-m

# Pane 1: Execute ./run_epc.sh
tmux send-keys -t automation:0.1 './run_epc.sh' C-m

# Pane 2: Execute ./run_enb.sh
tmux send-keys -t automation:0.2 './run_enb.sh' C-m

# Pane 3: Execute multiple commands with a delay
tmux send-keys -t automation:0.3 'ip netns add ue1' C-m
tmux send-keys -t automation:0.3 'ip netns add ue2' C-m
tmux send-keys -t automation:0.3 'sleep 10' C-m  # 10-second break
tmux send-keys -t automation:0.3 './run_srsran_2ue.sh' C-m

# Attach to the tmux session to display the split screen
tmux attach-session -t automation


# Install UHD and Download Firmware
#RUN apt update && \
#   apt install uhd-host -y && \
#   /usr/lib/uhd/utils/uhd_images_downloader.py && \
#    echo "export UHD_IMAGES_DIR=/usr/share/uhd/images" >> ~/.bashrc


