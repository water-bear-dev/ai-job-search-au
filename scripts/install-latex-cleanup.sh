#!/bin/sh
# Install a macOS launchd job to purge LaTeX build artifacts daily at 11:00 PM.
# Uninstall: launchctl unload ~/Library/LaunchAgents/com.ai-job-search-au.latex-cleanup.plist

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.ai-job-search-au.latex-cleanup"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$(command -v python3)"

mkdir -p "$HOME/Library/LaunchAgents"

cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${ROOT}/tools/cleanup_latex.py</string>
    <string>--daily</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>23</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/tracker/latex-cleanup.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/tracker/latex-cleanup.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "Installed daily cleanup at 11:00 PM"
echo "  Plist: $PLIST"
echo "  Log:   $ROOT/tracker/latex-cleanup.log"
echo "Test now: python3 $ROOT/tools/cleanup_latex.py --daily"
