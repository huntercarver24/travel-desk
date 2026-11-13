# Example desk

A small, made-up desk: two clients, three bookings, two consults, one proposal. Names and numbers are invented.

Use it to see every command work without touching a real desk:

```bash
TRAVEL_DESK_HOME=./examples TRAVEL_DESK_TODAY=2026-11-12 python3 scripts/desk.py status
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py clients
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py client hendersons
TRAVEL_DESK_HOME=./examples TRAVEL_DESK_TODAY=2026-11-12 python3 scripts/desk.py due
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py reservations --upcoming
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py render-proposal hendersons_SFO-FCO_2026-11-12.json
```

`TRAVEL_DESK_TODAY` pins "today" so the departure and audit windows are stable. Copy this folder somewhere else before running `mark-audited` against it.
