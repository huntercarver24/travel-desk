---
name: setup
description: First-run setup for Travel Desk. Checks that the Travel Hacking Toolkit is installed, creates the desk folder, records the agency's details for proposals, explains which API keys matter for a travel agent, and shows what to try first. Run on first use or when the user says "set up travel desk", "get started", or "setup".
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py *)
---

# Travel Desk setup

The user invoked this explicitly. Get them from zero to a working desk in a few minutes. Be concrete and brief. Never ask for API keys in chat.

## Step 1: Check the toolkit is installed

Travel Desk does no searching of its own. Every award search, cash fare, transfer ratio, and cents-per-point calculation comes from the **travel-hacker** plugin (the Travel Hacking Toolkit by borski).

Look at your own list of available skills for names that start with `travel-hacker:` (for example `travel-hacker:seats-aero`, `travel-hacker:compare-flights`, `travel-hacker:gardening`).

- If they are present: say so in one line and continue.
- If they are missing: stop here and give these two commands to run inside Claude Code, then `/reload-plugins` or restart:

  ```
  /plugin marketplace add borski/travel-hacking-toolkit
  /plugin install travel-hacker@borski
  ```

  Then re-run `/travel-desk:setup`.

## Step 2: Create the desk folder

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py init
```

It creates `~/TravelDesk` (or `$TRAVEL_DESK_HOME`) with `clients/`, `consults/`, `proposals/`, `bookings/`, `reports/`, a starter `agency.json`, and a README. It never overwrites existing files. Tell the user where the folder is and that this folder is where every client file, proposal, and report lives. Recommend starting Claude Code from inside that folder (`cd ~/TravelDesk && claude`) so file writes don't prompt every time.

## Step 3: Agency details

If the output says `"agency_is_starter": true`, ask for the agency details in **one message**, as a short checklist the user can answer in a few lines:

- Agency name
- Your name, as it should appear on proposals
- Phone, email, website (any that should be on proposals)
- A one-line tagline (optional)
- A brand color as a hex code like `#1f4e79` (optional; proposals use it for the header band)
- Your policy for award bookings, in one sentence, if you charge for them (for example "Award booking service: $150 per ticket"). Award tickets pay no commission, so many agents charge a flat fee. Leave blank if not applicable.
- Home airports most of your clients fly from (optional)

Write the answers to `agency.json` in the desk folder with this shape (keep keys exactly):

```json
{
  "name": "Sunrise Travel",
  "agent_name": "Linda Carver",
  "phone": "(555) 010-2000",
  "email": "linda@example.com",
  "website": "sunrisetravel.example",
  "tagline": "Thoughtful trips, planned personally.",
  "brand_color": "#1f4e79",
  "award_booking_fee": "Award booking service: $150 per ticket, credited back if you book a cash fare through us.",
  "home_airports": ["SFO", "OAK"],
  "notes": ""
}
```

Skip anything they left blank (empty string). Don't invent values.

## Step 4: API keys, explained for a travel agent

Do **not** collect keys here. The toolkit ships a local script that takes keys with masked input. Say this, in your own words:

- **With no keys at all** the desk already works for: cash flight search, hotel search, and award seats departing in the **next 60 days** (through the free Seats.aero connection).
- **Seats.aero Pro** (about $8 to $10 a month) is the one subscription worth having. It unlocks award search up to a year out, which is where most client trips live. Sign in with `/mcp`, pick `seats-aero`, Authenticate. For the API key route, run `/travel-hacker:getting-started` and follow its script.
- **Duffel** (free to search) gives clean, bookable cash fares for the cash-vs-points comparison.
- Everything else is optional.

Point them at `/travel-hacker:getting-started` for the key setup. That skill detects what's set and never prints secrets.

## Step 5: Show them what to try

Give four prompts, in this order:

1. `/travel-desk:new-client The Hendersons` to add the first client (home airport, cards, rough points balances).
2. `/travel-desk:consult hendersons Rome, second half of May, 2 adults, business class` to get the points-vs-cash play.
3. `/travel-desk:proposal hendersons` to turn the consult into a document to email.
4. `/travel-desk:desk` any morning to see departures, audits due, and open consults.

End with a declarative sentence (no "want me to"), for example: "You're set. Add your first client with `/travel-desk:new-client`."

## Don't

- Don't ask for API keys, passwords, or loyalty logins in chat, ever.
- Don't store anything in the plugin folder. All data goes in the desk folder.
- Don't lecture about points. One line per concept, then the next step.
