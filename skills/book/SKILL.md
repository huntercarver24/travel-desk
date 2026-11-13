---
name: book
description: Record a booked reservation (flight or hotel) for a client so the desk can audit it later for price drops, schedule changes, and better cabins. Also updates the consult and the client's balances. Use when the user says "booked", "ticketed", "record this booking", "log the reservation", "confirmation", or pastes a confirmation email.
argument-hint: "<client> <confirmation code and details>"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *)
---

# Record a booking

One JSON file per reservation in `bookings/<client-slug>/`. The format is the Travel Hacking Toolkit's gardening format, plus a few desk fields, so `/travel-desk:audit` can hand these files straight to the toolkit's `gardening` skill.

## Step 1: Start from the consult

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug-or-name>
```

If the latest consult has `status: proposed` or `researched`, pull the recommended option's route, program, points, taxes, and cash benchmark as defaults. If the user pasted a confirmation email, parse it: confirmation code, passengers, flights, dates, times, cabin, seats, ticket numbers.

## Step 2: Collect what's missing, once

Ask in one message for anything not yet known:

- Confirmation code (and ticket numbers if handy)
- Program or airline it's booked with, and whether it's ticketed or on hold (hold expiry date if so)
- Paid with points (how many, plus taxes paid) or cash (total)
- Flights: flight numbers, dates, departure and arrival times, cabin, seats
- Number of passengers
- The cash price the same seats were selling for at booking (for later price-drop and value math)

## Step 3: Write the file

Path: `bookings/<slug>/<first-travel-date>_<ORIG>-<DEST>_<CONF>.json` in the desk folder. One reservation per file; a hotel is its own file.

Flight:

```json
{
  "client": "hendersons",
  "trip_name": "Rome anniversary",
  "confirmation": "ABC123",
  "ticket_numbers": [],
  "type": "flight",
  "status": "booked",
  "booking_date": "2026-11-20",
  "program": "Air France/KLM Flying Blue",
  "paid_with": "points",
  "cost": { "miles": 220000, "taxes_usd": 760 },
  "cash_price_at_booking": 9800,
  "passengers": 2,
  "segments": [
    { "airline": "AF", "flight": "AF83", "origin": "SFO", "destination": "CDG", "date": "2027-05-18", "departure": "15:40", "arrival": "11:15+1", "cabin": "business", "fare_class": "O", "seat": "2A, 2L", "aircraft": "777-300ER" },
    { "airline": "AF", "flight": "AF1204", "origin": "CDG", "destination": "FCO", "date": "2027-05-19", "departure": "13:05", "arrival": "15:15", "cabin": "business", "fare_class": "O", "seat": "", "aircraft": "A320" }
  ],
  "hold_expires": null,
  "last_audited": null,
  "consult": "consults/2026-11-12_hendersons_SFO-FCO.md",
  "notes": "220,000 Chase UR transferred to Flying Blue on 2026-11-20. Return booked separately: see 2027-05-28_FCO-SFO_DEF456.json",
  "agent_notes": "Award booking fee invoiced 2026-11-20."
}
```

Hotel:

```json
{
  "client": "hendersons",
  "trip_name": "Rome anniversary",
  "confirmation": "HTL-9876",
  "type": "hotel",
  "status": "booked",
  "booking_date": "2026-11-20",
  "hotel_name": "Park Hyatt Rome",
  "program": "World of Hyatt",
  "paid_with": "points",
  "cost": { "points": 35000, "per_night": true },
  "cash_price_at_booking": 950,
  "checkin": "2027-05-19",
  "checkout": "2027-05-24",
  "room_type": "Park King",
  "guests": 2,
  "last_audited": null,
  "notes": ""
}
```

`cost.miles` and `cost.taxes_usd` are totals for all passengers. `status` is `booked`, `completed`, or `cancelled`. Times are local, 24-hour; `+1` means next day. Leave unknown fields empty rather than guessing.

## Step 4: Update the consult and the client

- Consult header: `status: booked`, `booking: bookings/<slug>/<file>.json`.
- Client file: if paid with points, subtract the points from the right balance (the card currency if transferred, the airline if direct), set `balances_as_of` to today, bump `updated`, append a dated note. Confirm the new balance in one line so the agent can correct it.

## Step 5: Post-booking checklist

Print this, adapted to the booking (from the toolkit's booking-guidance and gardening skills):

1. Ticket numbers issued (13 digits). An award without ticket numbers is a reservation, not a ticket.
2. The confirmation pulls up on the **operating** airline's site, not just the program that booked it. Seats assigned there.
3. The 24-hour free-cancellation window (US departures) closes at `<booking time + 24h>`.
4. Calendar: audit cadence is monthly until 30 days out, weekly inside 30, daily inside 7. `/travel-desk:desk` tracks it.
5. If any points are left in the card account that were meant for this trip, note it.

End declaratively. Mention `/travel-desk:audit <slug>` for the first check in a month.

## Don't

- Don't store card numbers, passport numbers, dates of birth, or loyalty logins. Ticket numbers and confirmation codes are fine.
- Don't mark a hold as `booked` without `hold_expires`; the desk uses it to warn before it lapses.
- Don't invent segment times. Leave them blank and say so.
