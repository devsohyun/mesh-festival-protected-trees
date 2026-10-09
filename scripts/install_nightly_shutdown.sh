#!/bin/bash
# Installs a LaunchDaemon that shuts the Mac down cleanly every night at 21:30.
# Uses /sbin/shutdown as root, so a TouchDesigner "save changes?" dialog can't block it.
# Run once on the installation Mac:
#   sudo ./scripts/install_nightly_shutdown.sh            install
#   ./scripts/install_nightly_shutdown.sh --print         only print the generated plist

LABEL="com.protectedtrees.nightly-shutdown"
PLIST="/Library/LaunchDaemons/$LABEL.plist"
SHUTDOWN_HOUR=21
SHUTDOWN_MINUTE=30

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
        <string>/sbin/shutdown</string>
        <string>-h</string>
        <string>now</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$SHUTDOWN_HOUR</integer>
        <key>Minute</key>
        <integer>$SHUTDOWN_MINUTE</integer>
    </dict>
</dict>
</plist>
EOF
}

if [ "$1" = "--print" ]; then
    plist_content
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0"
    exit 1
fi

# Replace any previous install.
launchctl bootout "system/$LABEL" 2>/dev/null

plist_content > "$PLIST"
chown root:wheel "$PLIST"
chmod 644 "$PLIST"
plutil -lint "$PLIST" || exit 1

launchctl bootstrap system "$PLIST" || exit 1
printf "Installed %s\nThe Mac will shut down every day at %02d:%02d.\n" "$PLIST" "$SHUTDOWN_HOUR" "$SHUTDOWN_MINUTE"
