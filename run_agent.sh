#!/usr/bin/env bash
set -euo pipefail

# Throttle so you stay under 15 calls/minute
sleep "${SLEEP_SECONDS:-5}"

# Launch the Python agent
python3 adk_agent/agent.py
