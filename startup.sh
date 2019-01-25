#!/bin/bash
# Using the technology of systemd to keep gofer service running even after system restarts
# place a corresponding unit service file in your systemd unit path (/etc/systemd/system/ for most)
source ~/gradingenv/bin/activate
python gofer_nb.py
