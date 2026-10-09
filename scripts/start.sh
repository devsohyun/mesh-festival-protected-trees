#!/bin/bash
# Launches the Protected Trees show file in TouchDesigner.
# Run by the LaunchAgent installed with install_autostart.sh, but can also be run by hand.

TD_BIN="/Applications/TouchDesigner.app/Contents/MacOS/TouchDesigner"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOE_FILE="$REPO_DIR/builds/protected_trees_v2_json.toe"

STARTUP_DELAY=15     # seconds to let the desktop, Ultraleap service, and USB devices settle
SERIAL_WAIT=30       # max extra seconds to wait for the Pico's USB serial port

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

if [ ! -x "$TD_BIN" ]; then
    log "ERROR: TouchDesigner not found at $TD_BIN"
    exit 1
fi
if [ ! -f "$TOE_FILE" ]; then
    log "ERROR: show file not found at $TOE_FILE"
    exit 1
fi

log "Waiting ${STARTUP_DELAY}s for system to settle"
sleep "$STARTUP_DELAY"

# Pico shows up as /dev/cu.usbmodem*. Don't block the show if it's missing.
for ((i = 0; i < SERIAL_WAIT; i++)); do
    if ls /dev/cu.usbmodem* >/dev/null 2>&1; then
        log "Pico serial port found: $(ls /dev/cu.usbmodem* | tr '\n' ' ')"
        break
    fi
    sleep 1
done
if ! ls /dev/cu.usbmodem* >/dev/null 2>&1; then
    log "WARNING: no Pico serial port found, starting anyway"
fi

# Keep display and system awake for as long as this process (TouchDesigner, after exec) lives.
/usr/bin/caffeinate -dims -w $$ &

log "Starting TouchDesigner: $TOE_FILE"
# exec so launchd tracks TouchDesigner itself and can restart it if it crashes.
exec "$TD_BIN" "$TOE_FILE"
