#!/usr/bin/env bash
# shot.sh <name> <command> [extra_delay_seconds]
set -euo pipefail
PROJ="/Users/ndanyuzweduncan/Desktop/Masters/Semester_3/Big Data Analytics/Advanced-Big-Data-Analytics-Project-2"
OUT="$PROJ/screenshots"
mkdir -p "$OUT"
name="$1"; cmd="$2"; extra="${3:-0}"
setup="cd \"$PROJ\" && source .venv/bin/activate && set -a && . ./.env && set +a && export JAVA_HOME=/opt/homebrew/opt/openjdk@17 NEO4J_HOME=~/neo4j-mm/neo4j-community-5.26.0 && clear"

wid=$(osascript - "$setup" "$cmd" <<'EOF'
on run argv
  tell application "Terminal"
    activate
    set t to do script (item 1 of argv)
    delay 1
    set w to first window whose tabs contains t
    set font size of current settings of t to 12
    set bounds of w to {0, 25, 1440, 830}
    set index of w to 1
    delay 1
    do script (item 2 of argv) in t
    return id of w
  end tell
end run
EOF
)

sleep 2
idle() { osascript -e "tell application \"Terminal\" to get processes of tab 1 of window id $wid" | tr -d ' ' | grep -qE '^(login,)?-?zsh$'; }
until idle && sleep 2 && idle; do sleep 1; done
sleep "$((1 + extra))"
if [ "${NOFRONT:-0}" != 1 ]; then
  osascript -e "tell application \"Terminal\" to set index of window id $wid to 1" -e 'tell application "Terminal" to activate'
  sleep 1
fi
screencapture -x "$OUT/$name.png"
echo "saved $OUT/$name.png (window $wid)"
if [ "${KEEP:-0}" != 1 ]; then
  osascript -e "tell application \"Terminal\" to if not busy of tab 1 of window id $wid then close window id $wid saving no" >/dev/null 2>&1 || true
fi
