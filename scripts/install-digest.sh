#!/bin/sh
# Install a macOS launchd job to send the daily job digest Mon–Fri at the hour
# from config/digest.json (default 08:00 local). Intended for GMT+10.
# Uninstall: scripts/uninstall-digest.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.ai-job-search-au.daily-digest"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$(command -v python3)"
HOUR="$("$PYTHON" -c "import json; from pathlib import Path; p=Path(r'$ROOT')/'config'/'digest.json'; h=8
print(json.load(p.open())['hour'] if p.is_file() else h)" 2>/dev/null || echo 8)"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$ROOT/job_scraper"

# launchd StartCalendarInterval: Weekday 0=Sunday … 6=Saturday. Mon–Fri = 1..5.
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
    <string>${ROOT}/tools/daily_digest.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Weekday</key><integer>1</integer>
      <key>Hour</key><integer>${HOUR}</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Weekday</key><integer>2</integer>
      <key>Hour</key><integer>${HOUR}</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Weekday</key><integer>3</integer>
      <key>Hour</key><integer>${HOUR}</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Weekday</key><integer>4</integer>
      <key>Hour</key><integer>${HOUR}</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Weekday</key><integer>5</integer>
      <key>Hour</key><integer>${HOUR}</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
  </array>
  <key>StandardOutPath</key>
  <string>${ROOT}/job_scraper/digest.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/job_scraper/digest.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "Installed daily digest Mon–Fri at ${HOUR}:00 local time"
echo "  Plist: $PLIST"
echo "  Log:   $ROOT/job_scraper/digest.log"
echo "  Enable digest in config/digest.json (\"enabled\": true) and set SMTP in .env"
echo "  After changing the hour in Settings, re-run this script to update launchd."
echo "Dry-run:  python3 $ROOT/tools/daily_digest.py --dry-run --force"
echo "Send now: python3 $ROOT/tools/daily_digest.py --send-now"
