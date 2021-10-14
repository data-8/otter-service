#!/bin/bash
set -euo pipefail
# Using the technology of systemd to keep gofer service running even after system restarts
# place a corresponding unit service file in your systemd unit path (/etc/systemd/system/ for most)
set -a
# source /etc/gofer-creds
exec python3 /opt/gofer_service/gofer_nb.py &
