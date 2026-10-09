#!/bin/bash
# Removes the LaunchAgent installed by install_autostart.sh. This also quits TouchDesigner
# if the agent started it.

LABEL="com.protectedtrees.start"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$PLIST"
echo "Removed $PLIST"
