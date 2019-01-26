#!/bin/bash
set -euo pipefail
# Using the technology of systemd to keep gofer service running even after system restarts
# place a corresponding unit service file in your systemd unit path (/etc/systemd/system/ for most)
source /home/vipasu/gradingenv/bin/activate
exec python /home/vipasu/gofer_service/gofer_nb.py
