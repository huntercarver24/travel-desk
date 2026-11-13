# Travel Desk

A travel agent's desk for Claude Code, built on top of the free, open-source [Travel Hacking Toolkit](https://github.com/borski/travel-hacking-toolkit) (the plugin in the "free Claude travel agent that turns your points into flights" videos).

The toolkit already does the hard part: it searches award seats across 27 mileage programs through Seats.aero, compares them with cash fares, finds the cheapest way to move credit-card points into an airline program, and audits a booking for price drops and schedule changes. It is built for one person planning their own trips.

Travel Desk adds what a working agent needs on top of that:

| Command | What it does |
|---|---|
| `/travel-desk:setup` | First run. Checks the toolkit is installed, creates the desk folder, records your agency details. |
| `/travel-desk:new-client` | A file per client: home airports, who travels, cards, points balances, preferences. |
| `/travel-desk:consult` | For one client and one trip: award seats vs cash, limited to programs that client can actually reach, with the cents-per-point math and booking steps. Saved to the desk. |
| `/travel-desk:proposal` | Turns a consult into a branded, plain-English document to email the client. Prints to PDF. |
| `/travel-desk:book` | Records the booking so it can be audited later. Updates the client's balances. |
| `/travel-desk:audit` | Runs the toolkit's gardening checklist across every client's upcoming trips and writes a report with a client-outreach list. |
| `/travel-desk:desk` | The morning view: departures, audits due, holds expiring, consults waiting on a yes. |

Everything lives in one folder, `~/TravelDesk`:

```
~/TravelDesk/
  agency.json        your name, contact, brand color, award-fee policy (shown on proposals)
  clients/           one JSON file per client
  consults/          research write-ups, one per client trip
  proposals/         client documents (.json spec + rendered .html)
  bookings/<client>/ one file per reservation
  reports/           audit reports
```

Travel Desk never books, cancels, or moves points. It researches, writes, and reminds. The agent and the client act.

## Install (for whoever sets it up)

You need:

- A Mac or Linux machine with [Claude Code](https://claude.com/claude-code) installed and signed in (a Claude Pro or Max plan, or an API key).
- Python 3.9 or newer (`python3 --version`; on a Mac, `xcode-select --install` provides it).

Then:

```bash
git clone https://github.com/huntercarver24/travel-desk.git ~/travel-desk
cd ~/travel-desk
bash install.sh
```

The installer:

1. Adds the `borski` marketplace and installs the `travel-hacker` plugin (42 skills, 7 search connectors).
2. Adds this folder as a marketplace and installs `travel-desk`.
3. Creates `~/TravelDesk`.
4. On a Mac, puts a double-clickable **Travel Desk** launcher on the Desktop that opens Claude Code inside the desk folder.

Keep the clone where it is. The plugin loads from this folder, so moving or deleting it removes the plugin. To update later: `cd ~/travel-desk && git pull`, then `/reload-plugins` inside Claude Code.

To have Claude Code pull the plugin from GitHub instead of the local folder (updates then come through `claude plugin update travel-desk`), run the installer as `TRAVEL_DESK_SOURCE=huntercarver24/travel-desk bash install.sh`. The repository must be reachable from that machine: public, or signed in with `gh auth login`.

Manual equivalent, inside Claude Code:

```
/plugin marketplace add borski/travel-hacking-toolkit
/plugin install travel-hacker@borski
/plugin marketplace add ~/travel-desk        (or: huntercarver24/travel-desk)
/plugin install travel-desk@travel-desk
```

### Keys and subscriptions

With nothing configured, the desk already does cash flight search, hotel search, and award seats departing in the next 60 days.

| What | Why | Cost |
|---|---|---|
| **Seats.aero Pro** | Award search up to a year out. Most client trips are more than 60 days away, so this is the one subscription that matters. Sign in inside Claude Code: `/mcp`, choose `seats-aero`, Authenticate. | About $8 to $10 a month |
| Duffel API key | Clean, bookable cash fares for the cash-vs-points comparison. | Free to search |
| Everything else | Hotels via Booking/Google, loyalty balances via AwardWallet, card portals via Docker. See the toolkit README. | Optional |

Run `/travel-hacker:getting-started` to set keys. It uses a local script with masked input; keys never go through the chat.

## Daily use (for the agent)

Open the desk (double-click **Travel Desk**, or `cd ~/TravelDesk && claude`) and talk to it in plain English. The slash commands are there when you want them.

**A new client calls.**
> `/travel-desk:new-client The Hendersons` and answer the short checklist (home airport, cards, rough points, preferences). Thirty seconds.

**They want to go somewhere.**
> `/travel-desk:consult hendersons Rome, second half of May, two adults, business class`
>
> You get: which of their points reach which programs, a ranked table of award and cash options, the recommended play, what they pay in cash, which points to move where, hold and transfer timing, booking steps, and a note on what's commissionable. Saved to `consults/`.

**Send them something.**
> `/travel-desk:proposal hendersons`
>
> A one-page document with your agency's name and colors: the trip, two or three options in plain English, the recommendation, their points before and after, next steps, and the fine print. Open it in a browser, File → Print → Save as PDF, attach.

**They said yes and you booked it.**
> `/travel-desk:book hendersons confirmation ABC123 ...` (or paste the confirmation email)
>
> The booking is recorded, the consult is closed, their balances are updated, and you get the post-booking checklist.

**Any morning.**
> `/travel-desk:desk` shows what needs attention. `/travel-desk:audit` works through the bookings that are due: price drops, better cabins, schedule changes, seat problems, written up as a list of clients to call.

## Privacy

- Client files hold names, home airports, cards held, balances, preferences, and confirmation codes. They never hold passport numbers, dates of birth, card numbers, loyalty logins, or passwords, and the skills refuse to store them.
- Everything stays in `~/TravelDesk` on this machine. The only things that leave it are the searches themselves (routes, dates, cabins) sent to the toolkit's sources, and your conversations with Claude.
- Points transfers and bookings happen in the client's own accounts. The desk never asks for their logins.

## For developers

Test without installing, loading both plugins for one session:

```bash
git clone https://github.com/borski/travel-hacking-toolkit ../travel-hacking-toolkit
claude --plugin-dir ../travel-hacking-toolkit --plugin-dir .
```

Validate the manifests:

```bash
claude plugin validate .
```

The helper script needs no dependencies. Point it at the examples to see every command work:

```bash
TRAVEL_DESK_HOME=./examples TRAVEL_DESK_TODAY=2026-11-12 python3 scripts/desk.py status
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py client hendersons
TRAVEL_DESK_HOME=./examples python3 scripts/desk.py render-proposal hendersons_SFO-FCO_2026-11-12.json -o /tmp/proposal.html
```

Layout:

```
.claude-plugin/   plugin.json and marketplace.json (depends on travel-hacker@borski)
skills/           one SKILL.md per command
scripts/desk.py   folder setup, status, client validation, reservations export, proposal rendering
templates/        proposal.html, the client document template
data/programs.json canonical balance keys mapped to the toolkit's data files
examples/         a sample desk (two clients, bookings, a consult, a proposal) used by the tests above
```

## Credits and license

Built on [borski/travel-hacking-toolkit](https://github.com/borski/travel-hacking-toolkit) (MIT) by Michael Borohovski, which does all the searching and the points math. Award data from [Seats.aero](https://seats.aero). Travel Desk is MIT licensed; see `LICENSE`.
