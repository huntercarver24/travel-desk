---
name: audit
description: Audit clients' upcoming bookings for price drops, better cabins, better routings, schedule changes, and seat problems, using the Travel Hacking Toolkit's gardening checklist, then write a report with a client-outreach list. Works across all clients or one. Use when the user says "audit", "garden", "check the bookings", "any price drops", "did anything change", "morning check", or when the desk shows bookings due.
argument-hint: "[client] [--all]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/desk.py" *)
---

# Booking audit

"Gardening" is the travel-hacker term: tend every live reservation on a cadence and catch problems or savings early. For a travel agent this is also the easiest reason to call a client with good news.

## Step 1: Decide the scope

Default is what's due:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py due [--client <slug>]
```

With `--all` (or "check everything"), take every upcoming booking instead:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py reservations --upcoming [--client <slug>]
```

`reservations` prints a JSON array in exactly the format the toolkit's `gardening` skill expects. Show the scope in one line ("5 bookings across 3 clients, 2 departing within a week") before starting.

If nothing is due, say so and stop, unless the user asked for `--all`.

## Step 2: Run the gardening checklist

Load travel-hacker's `gardening` skill and follow its checklist for every reservation in scope:

1. **Price drop** (the priority). Cash bookings: current fare on the same flights plus nearby airports, flag at 10% or $50 lower. Award bookings: same flight for fewer miles, a better cabin at similar miles, or a different reachable program pricing it cheaper. Hotels: current rate and points price.
2. **Better routing**: a nonstop that opened, or an hour or more saved.
3. **Better cabin**: business or first space that opened on the same flight, with the incremental cost.
4. **Schedule change**: departure or aircraft changes. Flag aircraft swaps that invalidate seats.
5. **Seat check** after any aircraft change.

For the client's "reachable programs" in the award checks, read the client file (`desk.py client <slug> --json`). A cheaper award in a program the client can't reach is a note, not an action.

**Parallelize.** For more than three reservations, fan out with subagents, one per client, each given that client's reservations JSON, the client's balances, and the checklist, returning the per-reservation status table and a list of sources checked. Run them at the same time.

Track every source per reservation as ok / error / skipped. An unchecked item is marked `not checked: <reason>`, never `OK`.

## Step 3: Write the report

Write `reports/YYYY-MM-DD_audit.md` (or `_audit_<slug>.md` for a single client) in the desk folder:

```markdown
# Booking audit · 2026-12-15

Scope: 5 bookings, 3 clients. Sources: Seats.aero (ok), Duffel (skipped: no key), Kiwi (ok), Trivago (ok).

## Client outreach

1. **Hendersons** · SFO–FCO May 18 · **Price drop.** The Delta One cash fare for these dates is now $4,100 (was $4,900). Their award is still the better deal, no action, but worth a line if they ask.
2. **Patel family** · LAX–HNL Dec 22 · **Rebook now.** Same United flights now $312 per person (was $389). Free to rebook on United; saves $308 for four. Script: "Good news, the fare on your Hawaii flights dropped, I've rebooked you and you'll see a $308 credit..."
3. **Ms. Okafor** · JFK–LHR Jan 9 · **Aircraft changed** 777 → 787. Seat 4A no longer exists. Pick a new seat with her this week.

## No action needed

- Hendersons · Park Hyatt Rome · rate up, points price unchanged.
- ...

## Per-reservation detail

### Hendersons · ABC123 · SFO–CDG–FCO · 2027-05-18

| Check | Status | Details |
|---|---|---|
| Price | OK | ... |
| Nearby airports | OK | ... |
| Better cabin | NOTE | ... |
| Routing | OK | ... |
| Schedule | OK | ... |
| Seat | OK | ... |

(repeat per reservation)

## Not checked

- Duffel cash fares: no key set. Kiwi used instead.
```

The outreach list leads. Each item names the client, the trip, the finding, the number, and what to do or say. Plain English, because the agent will read it on the phone.

## Step 4: Stamp what you checked

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py mark-audited bookings/<slug>/<file>.json ...
```

Only files you actually ran the checklist on. If a reservation was skipped because a source failed, leave it unstamped and say so.

## Step 5: Report back

In chat: the outreach list, the "not checked" list, and the report path. Three to ten lines. End declaratively.

## Don't

- Don't cancel, rebook, or change any reservation. The audit finds; the agent acts, with the client.
- Don't mark something OK that wasn't checked.
- Don't bury a price drop under six "OK" rows. Outreach first, detail after.
- Don't skip the cash benchmark on award bookings; "still the better deal" is a finding the client likes to hear.
