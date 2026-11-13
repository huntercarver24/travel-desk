---
name: new-client
description: Create or update a client file on the travel desk, covering who they are, home airports, who travels, usual cabin, which credit cards they hold, points and miles balances by program, and preferences. Use when the user says "new client", "add a client", "client intake", "update <client>'s points", "<client> now has X points", or mentions a client the desk doesn't know yet.
argument-hint: "<client name> [details in plain English]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/desk.py" *)
---

# New client / update client

One JSON file per client in `clients/`. This file is what every consult starts from, so the balances and cards matter most.

## Step 1: Find or create

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py slug "<client name>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug>
```

Exit code 1 means the client doesn't exist yet. Exit 0 or 2 means it exists (2 means it has problems to fix). For an update, read the existing file, merge the new facts, bump `updated`, and append a dated line to `notes`. Never drop fields you weren't asked to change.

## Step 2: Intake, in one message

If the user already gave details, use them. Otherwise ask **once**, as a short checklist they can answer in a few lines. Partial answers are fine; fill in what you can and leave the rest empty.

> To set up the file I need, roughly:
> 1. Who travels (names, and whether any are children or infants)
> 2. Home airport(s)
> 3. Usual cabin: economy, premium economy, business, or first
> 4. Credit cards they hold (Chase Sapphire Reserve, Amex Platinum, Capital One Venture X, Bilt, Citi Strata Premier, etc.)
> 5. Points and miles balances, ballpark is fine (card points and any airline or hotel programs)
> 6. Preferences or constraints (nonstop only, no red-eyes, airlines to avoid, aisle or window, mobility needs)
> 7. Anything else worth remembering

## Step 3: Map balances to canonical keys

Balance keys must come from `${CLAUDE_PLUGIN_ROOT}/data/programs.json`. The common ones:

| Key | Program |
|---|---|
| `chase_ur` | Chase Ultimate Rewards |
| `amex_mr` | American Express Membership Rewards |
| `capital_one` | Capital One Miles |
| `citi_ty` | Citi ThankYou Points |
| `bilt` | Bilt Rewards |
| `wells_fargo` | Wells Fargo Rewards |
| `united`, `american`, `delta`, `alaska`, `southwest`, `jetblue` | US airline programs |
| `aeroplan`, `flying_blue`, `virgin_atlantic`, `avios`, `lufthansa`, `turkish`, `emirates`, `etihad`, `singapore`, `ana`, `cathay`, `qantas`, `avianca` | Partner airline programs |
| `hyatt`, `marriott`, `hilton`, `ihg`, `wyndham`, `choice`, `accor` | Hotel programs |

`cat ${CLAUDE_PLUGIN_ROOT}/data/programs.json` for the full list. A program not in the list goes under `balances_other` as `{"Display Name": amount}` so nothing is lost. Credit card points count as the issuer's currency: Sapphire, Freedom, and Ink points are all `chase_ur`; Platinum, Gold, and Blue Business Plus points are all `amex_mr`.

## Step 4: Write the file

Write `clients/<slug>.json` in the desk folder (`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py paths` prints the folder). Shape:

```json
{
  "name": "Dana and Mark Henderson",
  "slug": "hendersons",
  "created": "2026-11-12",
  "updated": "2026-11-12",
  "contact": { "email": "", "phone": "" },
  "home_airports": ["SFO", "OAK"],
  "travelers": [
    { "name": "Dana", "type": "adult" },
    { "name": "Mark", "type": "adult" }
  ],
  "default_cabin": "business",
  "cards": ["Chase Sapphire Reserve", "Amex Platinum"],
  "balances": { "chase_ur": 120000, "amex_mr": 80000, "united": 16000, "hyatt": 30000 },
  "balances_other": {},
  "balances_as_of": "2026-11-12",
  "preferences": {
    "nonstop_only": false,
    "max_stops": 1,
    "no_redeyes": true,
    "seat": "aisle",
    "airlines_prefer": [],
    "airlines_avoid": [],
    "notes": "Mark needs extra legroom; knee surgery in 2025."
  },
  "notes": [
    "2026-11-12: Anniversary trip to Rome next May. Want business class if the points stretch."
  ]
}
```

`type` is `adult`, `child`, or `infant`. Dates are `YYYY-MM-DD`. Balances are whole numbers.

## Step 5: Validate and confirm

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py client <slug>
```

Fix anything listed under "Problems". Then confirm in three or four lines: who, home airports, the top balances, and one line on reach, for example "Their Chase points reach United, Aeroplan, Flying Blue, Virgin Atlantic, Hyatt and more (travel-hacker's transfer-partners skill has the full map)". Close with the natural next command: `/travel-desk:consult <slug> <trip>`.

## Privacy rules (not optional)

- Store: names, home airports, traveler types, cards held (by product name), balances, preferences, notes, confirmation codes.
- Never store: passport numbers, dates of birth, card numbers, loyalty account numbers, usernames, passwords, or security answers. If the user offers them, decline in one sentence and continue. The validator flags fields named like these.
- A rough balance is better than none. Mark the date in `balances_as_of` so consults can say how fresh it is.
