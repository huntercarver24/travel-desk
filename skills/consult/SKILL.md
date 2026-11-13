---
name: consult
description: Run a points-vs-cash consult for a client's trip. Loads the client's balances and cards, searches award seats and cash fares through the Travel Hacking Toolkit, keeps only awards the client can actually reach with their points, does the cents-per-point math, and writes up the recommended play with transfer and booking steps. Saves the consult to the desk. Use when the user asks what a client should do for a flight or trip, says "consult", "best play for <client>", "can <client> get to <place> on points", or asks about award seats or cash fares for a client.
argument-hint: "<client> <destination, dates, travelers, cabin>"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *)
---

# Client consult

The core of the desk. A consult answers one question for one client: **what is the best way to get this client on this trip, with the points they have and the cash they'd otherwise spend?**

All searching and math goes through the **travel-hacker** plugin. If its skills are not in your list, stop and point to `/travel-desk:setup`.

## Step 1: Load the client

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug-or-name> --json
```

Use the file's home airports, default cabin, travelers, and preferences as defaults. Note `balances_as_of`; if it is older than 90 days, say so and ask whether the balances still hold (one line, don't block on it).

**Walk-in** (no client file): if the user gives balances inline, run the consult with those and label it `client: walk-in-<slug>`. Suggest `/travel-desk:new-client` at the end so next time is faster.

## Step 2: Pin down the trip

Needed: destination, dates (and how flexible), travelers, cabin, one-way or round trip. Take what the user gave; ask for the rest **once, in one message**. Flexibility matters more than anything else for award space, so always capture it ("exact dates" vs "any week in May").

Confirm the plan back in one sentence and go.

## Step 3: Build the client's reach

Points the client can use for a given award = direct balance in that program + the most they could transfer in from each card currency.

Load travel-hacker's `transfer-partners` skill and read its `data/transfer-partners.json` for ratios, and `transfer-bonuses` for anything active right now. Produce a short reach table before searching:

| Program | Direct | Via cards | Effective |
|---|---:|---|---:|
| United | 16,000 | 120,000 Chase UR at 1:1 | 136,000 |
| Flying Blue | 0 | 120,000 Chase UR or 80,000 Amex MR at 1:1 | 200,000 (combined) |

Programs with no path from the client's cards and no direct balance are **unreachable**. They still appear in search results as signals (same alliance space is often bookable elsewhere), but they are never the recommendation.

## Step 4: Search

Follow travel-hacker's order: load `lessons-learned`, then `flight-search-strategy`. Then, in parallel:

- **Award space** via `seats-aero`. All programs first, no source filter. Anonymous MCP covers departures in the next 60 days; the Partner API or a Pro sign-in covers further out. Set `max_stops` from the client's preferences (default 1). Round trips are two one-way searches.
- **Cash fares** via `duffel` and `ignav` if keyed, and the free Kiwi and Skiplagged MCPs otherwise. Cash is the benchmark every award is measured against, so never skip it.
- **Southwest** via its skill only if Southwest flies the route and the client holds Rapid Rewards or a Companion Pass.

Track every source as ok / error / skipped. Never fail silently. If award search beyond 60 days is unavailable (no Pro), say so plainly: the consult is still useful for cash, and the dates can be re-checked when the window opens.

## Step 5: Gate and do the math

1. Drop award options in programs the client cannot reach (Step 3).
2. For each remaining option, use `trip-calculator`: cents per point = (cash fare − award taxes) ÷ points × 100, using the **client's cheapest currency path** (ratio and any active bonus applied).
3. Rate each against `points-valuations` floors. Flag anything in `award-sweet-spots`.
4. Check `award-holds` for the recommended program (can it be held before the transfer?) and `booking-guidance` for how it's actually ticketed (online, phone, which partner site).
5. Apply the decision rule: if the cash fare is below the opportunity cost of the points, cash wins; ties go to cash. For a travel agent there is a second axis: a cash fare can be booked and commissioned through the agency; an award cannot. Say which is which. Don't let it bias the recommendation, but never hide it.

## Step 6: Write it up in chat

Keep it tight. The structure:

**Reach** (the table from Step 3, trimmed to programs that matter)

**Options** (3 to 5 rows, ranked; always include the cash benchmark as a row)

| # | Option | Program | Points per person | Taxes | Routing | ¢/pt | Rating | Client can reach? |
|---|---|---|---:|---:|---|---:|---|---|

**The play.** One option, two or three sentences: what to book, what it costs in points and cash for the whole party, why it beats the alternatives.

**Backup.** One option, one sentence, and when to fall back to it.

**Client pays.** Cash out of pocket (taxes, fees, any cash segments), per person and total.

**Points to move.** From which card currency, to which program, how many, the ratio, any bonus, and the balance left afterward.

**Timing.** Hold rules for that program, then the rule that is never broken: confirm the seats on the airline's site before any points move. Transfers are irreversible.

**Booking steps.** Numbered. Who does what: card-to-airline transfers happen inside the client's own card account, so either the client does it while on the phone with the agent, or the agent walks them through it. The award itself is booked in the traveler's loyalty account. Cash fares go through the agency's usual channel.

**Agent notes.** Commissionable or not; the agency's award fee policy from `agency.json` if one is set; anything to tell the client up front (phantom availability risk, mixed cabin, long connection).

**Sources checked.** One line per source with ok / error / skipped, and the freshness of the award data.

Plain English in the parts the agent will read aloud. The ¢/pt column is for the agent; the proposal skill translates it for the client.

## Step 7: Save the consult

Always save (this is the agent's work record). Only skip if the user says not to. Write to `consults/YYYY-MM-DD_<slug>_<ORIG>-<DEST>.md` in the desk folder (`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py paths`), with this header exactly (flat `key: value` lines; the desk reads them):

```markdown
---
client: hendersons
status: researched
route: SFO-FCO
travel_dates: 2027-05-18 to 2027-05-28
cabin: business
travelers: 2
searched_on: 2026-11-12
recommended: Flying Blue business, 110,000 miles + $380 per person via Chase UR
points_needed: 220,000 Chase UR
cash_due: $760 total taxes
cash_benchmark: $4,900 per person round trip (Delta, lowest found)
proposal:
booking:
---

# Hendersons · Rome, May 2027 · Business

(the full write-up from Step 6, including the options table, the play, points to move, timing, booking steps, agent notes, and sources checked)
```

`status` is one of `researched`, `proposed`, `booked`, `cancelled`. Leave `proposal` and `booking` blank; the proposal and book skills fill them.

## Step 8: Close

End with a declarative line naming the next commands: `/travel-desk:proposal <slug>` to make the client document, `/travel-desk:book <slug>` once it's ticketed.

## Don't

- Don't recommend a program the client can't reach. Check the reach table, every time.
- Don't present award-only results without the cash benchmark, or cash-only results without saying the award search didn't run and why.
- Don't suggest transferring points before the space is confirmed, or more points than the award needs.
- Don't compare a one-way award to a round-trip cash fare. Match the denominators.
- Don't collect API keys or logins in chat. If a source needs a key, say which skill would unlock it, in one line at the end.
- Don't write anything to the plugin folder. Consults go in the desk folder.
