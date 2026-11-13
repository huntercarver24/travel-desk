#!/usr/bin/env bash
# Travel Desk installer.
#
# Run this once on the agent's computer, from a Terminal, inside the cloned folder:
#     bash install.sh
#
# It installs two Claude Code plugins (the Travel Hacking Toolkit, then Travel Desk),
# creates the ~/TravelDesk folder, and on a Mac adds a double-clickable launcher to the Desktop.
# It never asks for or stores any API key. Keys are set later with /travel-hacker:getting-started.

set -euo pipefail

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Where Claude Code should load Travel Desk from. Default: this folder. Set TRAVEL_DESK_SOURCE
# to a GitHub "owner/repo" once the plugin is published there.
SOURCE="${TRAVEL_DESK_SOURCE:-$HERE}"
DESK="${TRAVEL_DESK_HOME:-$HOME/TravelDesk}"

if ! command -v claude >/dev/null 2>&1; then
  say "Claude Code isn't installed on this computer."
  note "Install it first: https://claude.com/claude-code"
  note "Then open a new Terminal window and run this installer again."
  exit 1
fi
say "Claude Code found: $(claude --version 2>/dev/null | head -1)"

if ! command -v python3 >/dev/null 2>&1; then
  say "python3 is missing."
  if [[ "$(uname)" == "Darwin" ]]; then
    note "Run:  xcode-select --install   and accept the prompt, then run this installer again."
  else
    note "Install Python 3 with your package manager, then run this installer again."
  fi
  exit 1
fi

if [[ ! -f "$HERE/.claude-plugin/plugin.json" ]]; then
  say "Run this script from inside the travel-desk folder (plugin.json not found next to it)."
  exit 1
fi

say "1/4  Travel Hacking Toolkit (borski/travel-hacking-toolkit)"
if claude plugin marketplace add borski/travel-hacking-toolkit >/tmp/travel-desk-install.log 2>&1; then
  note "marketplace added"
else
  note "marketplace already added or unreachable (continuing): $(tail -1 /tmp/travel-desk-install.log)"
fi
if claude plugin install travel-hacker@borski >>/tmp/travel-desk-install.log 2>&1; then
  note "travel-hacker installed"
else
  note "travel-hacker install reported: $(tail -1 /tmp/travel-desk-install.log)"
fi

say "2/4  Travel Desk (from $SOURCE)"
if claude plugin marketplace add "$SOURCE" >>/tmp/travel-desk-install.log 2>&1; then
  note "marketplace added"
else
  note "marketplace already added (continuing): $(tail -1 /tmp/travel-desk-install.log)"
fi
if claude plugin install travel-desk@travel-desk >>/tmp/travel-desk-install.log 2>&1; then
  note "travel-desk installed"
else
  note "travel-desk install reported: $(tail -1 /tmp/travel-desk-install.log)"
  note "Full log: /tmp/travel-desk-install.log"
fi

say "3/4  Desk folder"
TRAVEL_DESK_HOME="$DESK" python3 "$HERE/scripts/desk.py" init | sed 's/^/  /'

say "4/4  Launcher"
if [[ "$(uname)" == "Darwin" && -d "$HOME/Desktop" ]]; then
  LAUNCHER="$HOME/Desktop/Travel Desk.command"
  cat > "$LAUNCHER" <<LAUNCH
#!/bin/bash
# Opens Claude Code inside the Travel Desk folder.
# A double-clicked .command runs in a bare shell without your PATH, so find claude explicitly.
cd "$DESK" || exit 1
export TRAVEL_DESK_HOME="$DESK"
for c in "\$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude "\$HOME/.claude/local/claude" "\$(command -v claude 2>/dev/null)"; do
  if [ -n "\$c" ] && [ -x "\$c" ]; then exec "\$c"; fi
done
echo "Claude Code was not found. Install it from https://claude.com/claude-code and try again."
read -r -p "Press Return to close."
LAUNCH
  chmod +x "$LAUNCHER"
  note "Added '$LAUNCHER'. Double-click it to open the desk."
  note "(If macOS blocks it the first time: right-click it, choose Open, then Open again.)"
else
  note "No Desktop launcher on this platform. Open the desk with:  cd \"$DESK\" && claude"
fi

say "Done. Next steps"
note "1. Open the desk (double-click 'Travel Desk' on the Desktop, or: cd \"$DESK\" && claude)."
note "2. Type:  /travel-desk:setup"
note "3. For award search beyond the next 60 days, sign in to Seats.aero Pro inside Claude Code:"
note "   /mcp  →  seats-aero  →  Authenticate"
note "Installed plugins:"
claude plugin list 2>/dev/null | sed 's/^/     /' || true
