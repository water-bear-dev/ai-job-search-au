#!/bin/sh
# Uninstall the daily job digest launchd job.

set -e
LABEL="com.ai-job-search-au.daily-digest"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
rm -f "$PLIST"
echo "Uninstalled $LABEL"
