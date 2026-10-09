#!/bin/bash
# Removes the LaunchDaemon installed by install_nightly_shutdown.sh.
#   sudo ./scripts/uninstall_nightly_shutdown.sh

LABEL="com.protectedtrees.nightly-shutdown"
PLIST="/Library/LaunchDaemons/$LABEL.plist"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0"
    exit 1
fi

launchctl bootout "system/$LABEL" 2>/dev/null
rm -f "$PLIST"
echo "Removed $PLIST"
