---
name: proposal
description: Turn a saved consult into a client-ready proposal document with the agency's branding, covering the trip, two or three options in plain English, the recommendation, what the client pays in cash and points, and what happens next. Renders to HTML that prints cleanly to PDF. Use when the user says "proposal", "write this up for the client", "client version", "something I can send <client>", or "make the PDF".
argument-hint: "<client or consult file> [notes on tone or options to include]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/desk.py" *)
---

# Client proposal

A consult is written for the agent. A proposal is written for the client. Same facts, different reader.

## Step 1: Find the consult

If the user gave a consult file, read it. Otherwise:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug-or-name>
```

lists the client's consults with status. Use the most recent one that isn't `cancelled` unless told otherwise. Also read `agency.json` (the desk root) and the client file. If there is no consult, say so and point to `/travel-desk:consult`.

## Step 2: Translate for the client

Rules for every sentence in the document:

- Second person, warm, specific. "You'd fly Air France from San Francisco, change planes in Paris, and land in Rome before lunch."
- No jargon. Not "cpp", "saver space", "UR", "MR", "J", "PNR". Say "about 4 cents per point, which is excellent value", "business class", "Chase points", "confirmation number".
- Full program names: "Air France/KLM Flying Blue", not `flyingblue`.
- Two or three options at most, the recommendation first and marked `recommended`. The cash fare appears as the benchmark (and as an option when it's a reasonable choice).
- Honest numbers. Taxes and fees are estimates until ticketed; say "about $380". Point counts are per person unless the option says "for both of you".
- No internal source names (seats.aero, Duffel, Kiwi) in the body. The fine print says "based on award availability and fares as of <date>".
- Nothing from the consult's **Agent notes** section. Commission and fee policy are the agent's business; the fee line, if the agency has one, appears once, from `agency.json`, and the user can turn it off.
- Never promise availability. Award seats change daily; the fine print says so and the next steps say the agent confirms before anything moves.

## Step 3: Write the spec

Write `proposals/<slug>_<ORIG>-<DEST>_<YYYY-MM-DD>.json` in the desk folder. The renderer reads exactly this shape; every key except `client` and `options` is optional:

```json
{
  "title": "Rome in Business Class",
  "client": { "name": "Dana and Mark", "slug": "hendersons" },
  "prepared_on": "2026-11-12",
  "trip": {
    "route": "San Francisco → Rome",
    "dates": "May 18 – May 28, 2027",
    "travelers": "2 adults",
    "cabin": "Business class",
    "flexibility": "Within a day or two of these dates"
  },
  "summary": "Your Chase points can cover both business-class seats to Rome and back, with about $380 per person in taxes. Paying cash for the same seats runs about $4,900 per person, so this is one of the best uses of your points we've seen.",
  "options": [
    {
      "recommended": true,
      "label": "Recommended",
      "name": "Air France business class via Flying Blue",
      "how": "Move 110,000 Chase points per person to Air France/KLM Flying Blue, then we book the seats in your Flying Blue account.",
      "routing": "SFO → Paris → Rome outbound, Rome → Paris → SFO home. One change each way, lie-flat seats on the ocean legs.",
      "points": "110,000 Chase points per person (220,000 total)",
      "cash": "About $380 per person in taxes and fees",
      "value": "Roughly 4.1 cents per point. Anything above 2 is a good use of Chase points.",
      "notes": "Seats were available on your dates as of November 12. We confirm them again on the phone with you before any points move."
    },
    {
      "label": "Also good",
      "name": "United Polaris via United MileagePlus",
      "how": "Move 72,000 Chase points per person to United, combined with the 16,000 United miles you already have.",
      "routing": "Nonstop SFO → Rome on United, nonstop home.",
      "points": "88,000 United miles per person",
      "cash": "About $90 per person in taxes",
      "value": "Roughly 5.4 cents per point, but only two seats showed and only on May 19 outbound.",
      "notes": "Best value if the May 19 departure works for you."
    },
    {
      "label": "Cash",
      "name": "Delta One business class, paid fare",
      "how": "We book it for you; no points involved.",
      "points": "None",
      "cash": "About $4,900 per person",
      "value": "Keeps all 200,000 of your points for a future trip.",
      "notes": "Refundable fares run higher; ask if you want that option."
    }
  ],
  "cash_benchmark": "The lowest business-class cash fare we found for these dates is about $4,900 per person round trip.",
  "why": [
    "Your points cover both seats with room to spare; you'd keep about 10,000 Chase points and all 80,000 Amex points.",
    "No red-eye on the way out, which you asked us to avoid.",
    "Air France's business seat is a fully flat bed on both ocean legs."
  ],
  "balances_after": [
    { "program": "Chase Ultimate Rewards", "before": 120000, "after": 10000 },
    { "program": "American Express Membership Rewards", "before": 80000, "after": 80000 }
  ],
  "next_steps": [
    "Reply with the option you'd like, or call us with questions.",
    "We schedule a 15-minute call. On the call, we confirm the seats are still open, then you move the points from your Chase account while we're on the line (transfers are instant for Air France).",
    "We book the seats in your Flying Blue account and pay the taxes on the card you choose.",
    "You receive the confirmation the same day, and we keep watching the booking for schedule changes and better seats."
  ],
  "fee": "",
  "fine_print": [
    "Award seats and fares change daily. Everything here is based on availability and fares as of November 12, 2026, and is confirmed again before any points are transferred.",
    "Taxes and fees are estimates until the ticket is issued.",
    "Points transfers from a credit card to an airline cannot be reversed, which is why we confirm seats first.",
    "Points and miles are held in your own accounts; we never ask for your passwords."
  ]
}
```

Notes on fields:

- `fee`: leave out (or empty) to use `award_booking_fee` from `agency.json`; set to a string to override; set to `" "` (a single space) to suppress the fee line entirely.
- `balances_after` and `points_snapshot` are alternatives; use `balances_after` when the recommendation uses points.
- `agency` can be added to override agency.json fields for one proposal (rare).

## Step 4: Render

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py render-proposal proposals/<file>.json
```

It prints the path of the HTML file (same name, `.html`). Warnings on stderr mean a placeholder was left empty; fix the spec and re-run.

## Step 5: Update the consult

In the consult's header set `status: proposed` and `proposal: proposals/<file>.html`.

## Step 6: Hand it over

Tell the user, in three lines:

1. Where the file is.
2. How to send it: open the HTML in a browser (on a Mac, `open "<path>"`), then File → Print → Save as PDF, and attach the PDF to the email. The page is laid out for letter paper.
3. That edits are one sentence away ("make the summary shorter", "drop the United option", "add a hotel line"): edit the JSON, re-render.

End declaratively. Mention `/travel-desk:book <slug>` for when the client says yes.

## Don't

- Don't put the agent's commission notes, source names, or internal ratings in the client document.
- Don't include options the client can't reach with their points, or options the consult rejected.
- Don't change the facts. If the proposal needs a number the consult doesn't have, run the consult again rather than guessing.
- Don't open the browser without being asked; print the path and the command.
