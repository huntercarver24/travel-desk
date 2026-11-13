---
name: desk
description: The morning view of the travel desk. Shows clients, departures in the next two weeks, bookings due for an audit, holds about to expire, and consults waiting on a proposal or a client's yes. Use when the user says "desk", "what needs attention", "morning", "show my clients", "status", or asks about a specific client ("what's going on with the Hendersons", "show me <client>").
argument-hint: "[client] [--days N]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *)
---

# The desk

A read-only overview. Nothing here searches the internet or changes files.

## If no client is named

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py status --days 14
```

(`--days N` if the user asked for a different window.) The output is already Markdown. Show it as-is, then add a short "Today" section of at most three lines, choosing the most urgent items in this order:

1. Holds expiring today or tomorrow.
2. Bookings departing within 7 days that are due for an audit (recommend `/travel-desk:audit <client>`).
3. Consults with status `proposed` older than 5 days (a nudge to the client), then `researched` consults with no proposal (recommend `/travel-desk:proposal <client>`).
4. Trips in the past still marked booked (ask to mark completed; do it if they say yes by editing `"status": "completed"` in the booking file).

If the output notes that `agency.json` still has starter values, say so in one line and point at `/travel-desk:setup`.

## If a client is named

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug-or-name>
```

It prints the profile, balances, consults, and bookings for that client, and lists problems at the end (unknown balance keys, missing airports, fields that look like sensitive data). Show it, then:

- If there are problems, offer the fix in one line each and apply them when the user agrees (edit the JSON file).
- If the user asked a question about the client ("do they have enough for business class to Rome?"), answer from the file, and point to `/travel-desk:consult` for anything that needs a live search.

## Desk conventions

- The desk lives at `$TRAVEL_DESK_HOME`, default `~/TravelDesk`. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py paths` prints every path.
- The audit cadence (from the toolkit's gardening skill): daily inside 7 days of departure, weekly inside 30, monthly beyond.
- Keep the chat short. The tables carry the detail.
