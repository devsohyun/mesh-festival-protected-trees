#!/bin/bash
# Installs a LaunchAgent that runs start.sh at login and restarts TouchDesigner if it crashes.
# Run once on the installation Mac, as the user that auto-logs in:
#   ./scripts/install_autostart.sh            install and start now
#   ./scripts/install_autostart.sh --print    only print the generated plist

LABEL="com.protectedtrees.start"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
START_SCRIPT="$SCRIPT_DIR/start.sh"
LOG_DIR="$HOME/Library/Logs/ProtectedTrees"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

# KeepAlive/SuccessfulExit=false: relaunch only after a crash, so quitting
# TouchDesigner normally (Cmd+Q) for maintenance keeps it closed.
plist_content() {
cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$START_SCRIPT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/start.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/start.log</string>
</dict>
</plist>
EOF
}

if [ "$1" = "--print" ]; then
    plist_content
    exit 0
fi

chmod +x "$START_SCRIPT"
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

# Replace any previous install.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null

plist_content > "$PLIST"
plutil -lint "$PLIST" || exit 1

launchctl bootstrap "gui/$(id -u)" "$PLIST" || exit 1
echo "Installed $PLIST"
echo "TouchDesigner will start now and at every login. Log: $LOG_DIR/start.log"
