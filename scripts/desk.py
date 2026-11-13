#!/usr/bin/env python3
"""desk.py: the Travel Desk helper. Python 3.9+, standard library only.

The desk lives at $TRAVEL_DESK_HOME (default: ~/TravelDesk):

  agency.json               who the agent is (name, contact, brand color, fee policy)
  clients/<slug>.json       one file per client
  consults/*.md             research write-ups, one per client trip
  proposals/*.json, *.html  client-facing documents (JSON spec + rendered HTML)
  bookings/<slug>/*.json    one file per booked reservation (gardening format)
  reports/*.md              audit reports

Subcommands (run with -h for flags):

  init                 create the folder structure and a starter agency.json
  paths                print the resolved desk paths (JSON)
  status               the morning view: clients, departures, audits due, open consults
  clients              one line per client
  client <slug>        print one client file, with validation warnings
  reservations         merge bookings into one JSON array (input for gardening)
  due                  bookings that are due for an audit, by cadence
  mark-audited <file>  stamp bookings as audited today
  render-proposal      render proposals/<name>.json into HTML
  slug "<name>"        print the slug for a client name

Nothing here talks to the network. Secrets never belong in these files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PLUGIN_ROOT / "templates" / "proposal.html"
PROGRAMS = PLUGIN_ROOT / "data" / "programs.json"

SUBDIRS = ["clients", "consults", "proposals", "bookings", "reports"]
CONSULT_STATUSES = ("researched", "proposed", "booked", "cancelled")
BOOKING_STATUSES = ("booked", "completed", "cancelled")

STARTER_AGENCY = {
    "name": "Your Agency Name",
    "agent_name": "Your Name",
    "phone": "",
    "email": "",
    "website": "",
    "tagline": "",
    "brand_color": "#0f4c5c",
    "award_booking_fee": "",
    "home_airports": [],
    "notes": "Fill this in once. Everything client-facing (proposals) pulls from it.",
}


# ----------------------------------------------------------------------------
# paths and io
# ----------------------------------------------------------------------------

def home() -> Path:
    raw = os.environ.get("TRAVEL_DESK_HOME", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / "TravelDesk"


def paths() -> dict:
    h = home()
    out = {"home": str(h), "agency": str(h / "agency.json")}
    for d in SUBDIRS:
        out[d] = str(h / d)
    return out


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def today() -> dt.date:
    forced = os.environ.get("TRAVEL_DESK_TODAY")  # for tests
    return dt.date.fromisoformat(forced) if forced else dt.date.today()


def parse_date(s) -> dt.date | None:
    if not s or not isinstance(s, str):
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s.strip())
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def human_date(d: dt.date | None) -> str:
    if not d:
        return ""
    return d.strftime("%a, %b %-d, %Y") if os.name != "nt" else d.strftime("%a, %b %d, %Y")


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "client"


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(home()))
    except ValueError:
        return str(p)


def agency() -> dict:
    p = home() / "agency.json"
    if p.exists():
        try:
            data = load_json(p)
            if isinstance(data, dict):
                return {**STARTER_AGENCY, **data}
        except json.JSONDecodeError as e:
            warn(f"agency.json is not valid JSON: {e}")
    return dict(STARTER_AGENCY)


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


# ----------------------------------------------------------------------------
# clients
# ----------------------------------------------------------------------------

def known_programs() -> dict:
    try:
        return load_json(PROGRAMS)["programs"]
    except (OSError, KeyError, json.JSONDecodeError):
        return {}


def iter_clients() -> list[dict]:
    out = []
    d = home() / "clients"
    if not d.exists():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            c = load_json(p)
        except json.JSONDecodeError as e:
            warn(f"{rel(p)}: invalid JSON ({e}), skipped")
            continue
        if not isinstance(c, dict):
            warn(f"{rel(p)}: not an object, skipped")
            continue
        c.setdefault("slug", p.stem)
        c["_path"] = str(p)
        out.append(c)
    return out


def find_client(slug: str) -> dict | None:
    p = home() / "clients" / f"{slug}.json"
    if p.exists():
        c = load_json(p)
        c.setdefault("slug", slug)
        c["_path"] = str(p)
        return c
    # forgiving lookup: by name substring
    s = slugify(slug)
    for c in iter_clients():
        if c["slug"] == s or s in slugify(c.get("name", "")):
            return c
    return None


def validate_client(c: dict) -> list[str]:
    problems = []
    progs = known_programs()
    if not c.get("name"):
        problems.append("missing 'name'")
    if not c.get("home_airports"):
        problems.append("missing 'home_airports' (list of IATA codes)")
    for code in c.get("home_airports") or []:
        if not re.fullmatch(r"[A-Z]{3}", str(code)):
            problems.append(f"home airport '{code}' is not a 3-letter IATA code")
    bal = c.get("balances") or {}
    if not isinstance(bal, dict):
        problems.append("'balances' must be an object of program_key: number")
    else:
        for k, v in bal.items():
            if progs and k not in progs:
                problems.append(f"balance key '{k}' is not in data/programs.json (use a canonical key)")
            if not isinstance(v, (int, float)):
                problems.append(f"balance '{k}' must be a number, got {type(v).__name__}")
    if c.get("default_cabin") not in (None, "", "economy", "premium", "business", "first"):
        problems.append("default_cabin must be economy, premium, business, or first")
    blob = json.dumps(c).lower()
    for red_flag in ("passport", "password", "card_number", "cvv", "ssn", "date_of_birth", "dob"):
        if f'"{red_flag}"' in blob:
            problems.append(f"field '{red_flag}' looks like sensitive data; the desk must not store it")
    return problems


def points_summary(c: dict, limit: int = 3) -> str:
    progs = known_programs()
    bal = c.get("balances") or {}
    if not isinstance(bal, dict) or not bal:
        return "none on file"
    items = sorted(((k, v) for k, v in bal.items() if isinstance(v, (int, float))), key=lambda kv: -kv[1])
    parts = []
    for k, v in items[:limit]:
        name = progs.get(k, {}).get("display", k)
        parts.append(f"{int(v):,} {name}")
    more = len(items) - limit
    return ", ".join(parts) + (f" (+{more} more)" if more > 0 else "")


# ----------------------------------------------------------------------------
# consults
# ----------------------------------------------------------------------------

def parse_header(path: Path) -> dict:
    """Flat 'key: value' header between the first two '---' lines of a Markdown file."""
    out: dict = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def iter_consults() -> list[dict]:
    out = []
    d = home() / "consults"
    if not d.exists():
        return out
    for p in sorted(d.glob("*.md")):
        h = parse_header(p)
        h["_path"] = str(p)
        h["_file"] = p.name
        out.append(h)
    return out


# ----------------------------------------------------------------------------
# bookings
# ----------------------------------------------------------------------------

def iter_bookings(client: str | None = None) -> list[dict]:
    out = []
    d = home() / "bookings"
    if not d.exists():
        return out
    for p in sorted(d.rglob("*.json")):
        try:
            b = load_json(p)
        except json.JSONDecodeError as e:
            warn(f"{rel(p)}: invalid JSON ({e}), skipped")
            continue
        items = b if isinstance(b, list) else [b]
        for item in items:
            if not isinstance(item, dict):
                continue
            item.setdefault("client", p.parent.name if p.parent != d else "")
            item["_path"] = str(p)
            if client and item.get("client") != client:
                continue
            out.append(item)
    return out


def booking_dates(b: dict) -> tuple[dt.date | None, dt.date | None]:
    """(first travel date, last travel date) for a reservation."""
    dates = []
    for seg in b.get("segments") or []:
        d = parse_date(seg.get("date"))
        if d:
            dates.append(d)
    for key in ("checkin", "checkout", "date", "start_date", "end_date"):
        d = parse_date(b.get(key))
        if d:
            dates.append(d)
    if not dates:
        return None, None
    return min(dates), max(dates)


def cadence_days(days_out: int) -> int:
    """Audit cadence from the toolkit's gardening skill: daily inside a week, weekly inside a month, monthly beyond."""
    if days_out < 7:
        return 1
    if days_out <= 30:
        return 7
    return 30


def audit_state(b: dict, now: dt.date) -> dict:
    start, end = booking_dates(b)
    status = b.get("status", "booked")
    info = {"departs": start, "ends": end, "status": status, "due": False, "reason": ""}
    if status != "booked":
        info["reason"] = f"status is {status}"
        return info
    if not start:
        info["due"] = True
        info["reason"] = "no travel date on file; check it"
        return info
    if (end or start) < now:
        info["reason"] = "travel is in the past; mark completed"
        return info
    days_out = (start - now).days
    cad = cadence_days(days_out)
    last = parse_date(b.get("last_audited"))
    info.update({"days_out": days_out, "cadence": cad, "last_audited": last})
    if last is None:
        info["due"] = True
        info["reason"] = "never audited"
    elif (now - last).days >= cad:
        info["due"] = True
        info["reason"] = f"last audited {(now - last).days}d ago, cadence every {cad}d"
    else:
        info["reason"] = f"audited {(now - last).days}d ago, next in {cad - (now - last).days}d"
    return info


def route_of(b: dict) -> str:
    segs = b.get("segments") or []
    if segs:
        codes = [segs[0].get("origin", "?")] + [s.get("destination", "?") for s in segs]
        # collapse A-B-B-C to A-B-C
        out = [codes[0]]
        for c in codes[1:]:
            if c != out[-1]:
                out.append(c)
        return "-".join(out)
    if b.get("hotel_name"):
        return b["hotel_name"]
    return b.get("route", "")


# ----------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------

def cmd_init(args) -> int:
    h = home()
    created = []
    for d in [h] + [h / s for s in SUBDIRS]:
        if not d.exists():
            d.mkdir(parents=True)
            created.append(str(d))
    ap = h / "agency.json"
    if not ap.exists():
        save_json(ap, STARTER_AGENCY)
        created.append(str(ap))
    readme = h / "README.txt"
    if not readme.exists():
        readme.write_text(
            "This folder is your Travel Desk.\n\n"
            "agency.json   your agency details (shown on client proposals)\n"
            "clients/      one file per client\n"
            "consults/     research write-ups for client trips\n"
            "proposals/    client-ready documents to send\n"
            "bookings/     booked reservations, one file each, grouped by client\n"
            "reports/      audit reports\n\n"
            "Open Claude Code in this folder and type /travel-desk:desk to see what needs attention.\n"
            "Never put passport numbers, card numbers, dates of birth, or passwords in these files.\n",
            encoding="utf-8",
        )
        created.append(str(readme))
    print(json.dumps({"home": str(h), "created": created, "agency_is_starter": agency().get("name") == STARTER_AGENCY["name"]}, indent=2))
    return 0


def cmd_paths(args) -> int:
    print(json.dumps(paths(), indent=2))
    return 0


def cmd_slug(args) -> int:
    print(slugify(" ".join(args.name)))
    return 0


def cmd_clients(args) -> int:
    cs = iter_clients()
    if args.json:
        for c in cs:
            c.pop("_path", None)
        print(json.dumps(cs, indent=2))
        return 0
    if not cs:
        print("No clients yet. Run /travel-desk:new-client to add one.")
        return 0
    print("| Client | Slug | Home | Cabin | Points on file | Updated |")
    print("|---|---|---|---|---|---|")
    for c in cs:
        print(
            f"| {c.get('name','')} | `{c['slug']}` | {', '.join(c.get('home_airports') or [])} | "
            f"{c.get('default_cabin') or ''} | {points_summary(c)} | {c.get('updated') or c.get('created') or ''} |"
        )
    return 0


def cmd_client(args) -> int:
    c = find_client(args.slug)
    if not c:
        print(f"No client matching '{args.slug}'. Known: " + ", ".join(x["slug"] for x in iter_clients()), file=sys.stderr)
        return 1
    path = c.pop("_path")
    problems = validate_client(c)
    progs = known_programs()
    if args.json:
        print(json.dumps({"path": path, "client": c, "problems": problems}, indent=2))
        return 0
    print(f"# {c.get('name', c['slug'])}  (`{c['slug']}`)")
    print(f"File: {path}")
    print(f"Home airports: {', '.join(c.get('home_airports') or []) or 'none'}")
    trav = c.get("travelers") or []
    if trav:
        print("Travelers: " + ", ".join(f"{t.get('name','?')} ({t.get('type','adult')})" for t in trav))
    print(f"Default cabin: {c.get('default_cabin') or 'not set'}")
    if c.get("cards"):
        print("Cards: " + ", ".join(c["cards"]))
    bal = c.get("balances") or {}
    if bal:
        print(f"\nBalances (as of {c.get('balances_as_of') or 'unknown'}):")
        print("| Program | Balance | Kind |")
        print("|---|---:|---|")
        for k, v in sorted(bal.items(), key=lambda kv: -(kv[1] if isinstance(kv[1], (int, float)) else 0)):
            meta = progs.get(k, {})
            shown = f"{int(v):,}" if isinstance(v, (int, float)) else f"{v!r} (not a number)"
            print(f"| {meta.get('display', k)} (`{k}`) | {shown} | {meta.get('kind', '?')} |")
    prefs = c.get("preferences") or {}
    if prefs:
        print("\nPreferences: " + json.dumps(prefs, ensure_ascii=False))
    notes = c.get("notes") or []
    if notes:
        print("\nNotes:")
        for n in notes:
            print(f"- {n}")
    # related files
    cons = [x for x in iter_consults() if x.get("client") == c["slug"]]
    bks = iter_bookings(c["slug"])
    if cons:
        print("\nConsults:")
        for x in cons:
            print(f"- {x.get('searched_on','')} {x.get('route','')} [{x.get('status','?')}] {rel(Path(x['_path']))}")
    if bks:
        print("\nBookings:")
        for b in bks:
            d, _ = booking_dates(b)
            print(f"- {d or '?'} {route_of(b)} conf {b.get('confirmation','?')} [{b.get('status','booked')}] {rel(Path(b['_path']))}")
    if problems:
        print("\nProblems:")
        for p in problems:
            print(f"- {p}")
        return 2
    return 0


def cmd_reservations(args) -> int:
    now = today()
    out = []
    for b in iter_bookings(args.client):
        st = audit_state(b, now)
        if args.upcoming and (st["departs"] is None or (st["ends"] or st["departs"]) < now):
            continue
        if args.days is not None and st.get("days_out") is not None and st["days_out"] > args.days:
            continue
        if args.due_only and not st["due"]:
            continue
        b = dict(b)
        b["_file"] = rel(Path(b.pop("_path")))
        out.append(b)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_due(args) -> int:
    now = today()
    rows = []
    for b in iter_bookings(args.client):
        st = audit_state(b, now)
        if st["due"]:
            rows.append((st, b))
    if args.json:
        print(json.dumps([{**{k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in st.items()},
                            "client": b.get("client"), "trip_name": b.get("trip_name"), "route": route_of(b),
                            "confirmation": b.get("confirmation"), "file": rel(Path(b["_path"]))} for st, b in rows], indent=2))
        return 0
    if not rows:
        print("Nothing is due for an audit.")
        return 0
    rows.sort(key=lambda r: (r[0]["departs"] or dt.date.max))
    print("| Client | Trip | Route | Departs | Days out | Why | File |")
    print("|---|---|---|---|---:|---|---|")
    for st, b in rows:
        print(f"| {b.get('client','')} | {b.get('trip_name','')} | {route_of(b)} | {st['departs'] or '?'} | "
              f"{st.get('days_out','')} | {st['reason']} | `{rel(Path(b['_path']))}` |")
    return 0


def cmd_mark_audited(args) -> int:
    stamp = args.date or today().isoformat()
    if not parse_date(stamp):
        print("--date must be YYYY-MM-DD", file=sys.stderr)
        return 1
    count = 0
    for f in args.files:
        p = Path(f).expanduser()
        if not p.is_absolute():
            p = home() / p
        if not p.exists():
            warn(f"{f}: not found")
            continue
        data = load_json(p)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                item["last_audited"] = stamp
                count += 1
        save_json(p, data)
    print(f"Marked {count} reservation(s) audited on {stamp}.")
    return 0


def cmd_status(args) -> int:
    now = today()
    clients = iter_clients()
    consults = iter_consults()
    bookings = iter_bookings()
    states = [(audit_state(b, now), b) for b in bookings]

    upcoming = sorted(
        [(st, b) for st, b in states if st["departs"] and 0 <= (st["departs"] - now).days <= args.days and st["status"] == "booked"],
        key=lambda r: r[0]["departs"],
    )
    due = sorted([(st, b) for st, b in states if st["due"]], key=lambda r: (r[0]["departs"] or dt.date.max))
    past = [(st, b) for st, b in states if st["status"] == "booked" and st["ends"] and st["ends"] < now]
    holds = []
    for st, b in states:
        hd = parse_date(b.get("hold_expires"))
        if hd and st["status"] == "booked" and hd >= now - dt.timedelta(days=1):
            holds.append((hd, b))
    holds.sort(key=lambda r: r[0])
    open_consults = [c for c in consults if c.get("status", "researched") in ("researched", "proposed")]

    if args.json:
        def ser(st):
            return {k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in st.items()}
        print(json.dumps({
            "today": now.isoformat(),
            "home": str(home()),
            "agency": {k: agency().get(k) for k in ("name", "agent_name")},
            "clients": [{"slug": c["slug"], "name": c.get("name"), "home_airports": c.get("home_airports"), "updated": c.get("updated")} for c in clients],
            "upcoming": [{"client": b.get("client"), "trip_name": b.get("trip_name"), "route": route_of(b), "departs": st["departs"].isoformat(), "confirmation": b.get("confirmation"), "file": rel(Path(b["_path"]))} for st, b in upcoming],
            "due": [{"client": b.get("client"), "trip_name": b.get("trip_name"), "route": route_of(b), "file": rel(Path(b["_path"])), **ser(st)} for st, b in due],
            "past_still_booked": [{"client": b.get("client"), "route": route_of(b), "file": rel(Path(b["_path"]))} for st, b in past],
            "holds": [{"client": b.get("client"), "route": route_of(b), "hold_expires": hd.isoformat(), "file": rel(Path(b["_path"]))} for hd, b in holds],
            "open_consults": [{k: v for k, v in c.items() if not k.startswith("_")} | {"file": rel(Path(c["_path"]))} for c in open_consults],
        }, indent=2))
        return 0

    ag = agency()
    print(f"# Travel Desk · {human_date(now)}")
    print(f"{ag.get('name')} · {ag.get('agent_name')} · desk at {home()}\n")

    print(f"## Clients ({len(clients)})")
    if clients:
        print("| Client | Slug | Home | Points on file | Updated |")
        print("|---|---|---|---|---|")
        for c in clients:
            print(f"| {c.get('name','')} | `{c['slug']}` | {', '.join(c.get('home_airports') or [])} | {points_summary(c)} | {c.get('updated') or c.get('created') or ''} |")
    else:
        print("None yet. `/travel-desk:new-client` adds one.")

    print(f"\n## Departing in the next {args.days} days ({len(upcoming)})")
    if upcoming:
        print("| Departs | Client | Trip | Route | Conf | Audit |")
        print("|---|---|---|---|---|---|")
        for st, b in upcoming:
            flag = "due" if st["due"] else "ok"
            print(f"| {st['departs']} | {b.get('client','')} | {b.get('trip_name','')} | {route_of(b)} | {b.get('confirmation','')} | {flag} |")
    else:
        print("No departures in this window.")

    print(f"\n## Bookings due for an audit ({len(due)})")
    if due:
        print("| Client | Trip | Route | Departs | Days out | Why | File |")
        print("|---|---|---|---|---:|---|---|")
        for st, b in due:
            print(f"| {b.get('client','')} | {b.get('trip_name','')} | {route_of(b)} | {st['departs'] or '?'} | {st.get('days_out','')} | {st['reason']} | `{rel(Path(b['_path']))}` |")
        print("\nRun `/travel-desk:audit` to work through these.")
    else:
        print("Nothing due. Cadence: daily inside 7 days, weekly inside 30, monthly beyond.")

    if holds:
        print(f"\n## Holds expiring ({len(holds)})")
        print("| Expires | Client | Route | File |")
        print("|---|---|---|---|")
        for hd, b in holds:
            print(f"| {hd} | {b.get('client','')} | {route_of(b)} | `{rel(Path(b['_path']))}` |")

    print(f"\n## Open consults ({len(open_consults)})")
    if open_consults:
        print("| Searched | Client | Route | Dates | Status | File |")
        print("|---|---|---|---|---|---|")
        for c in open_consults:
            print(f"| {c.get('searched_on','')} | {c.get('client','')} | {c.get('route','')} | {c.get('travel_dates','')} | {c.get('status','researched')} | `{rel(Path(c['_path']))}` |")
        print("\n`researched` means no proposal yet. `proposed` means the client has it and you are waiting on a yes.")
    else:
        print("None open.")

    if past:
        print(f"\n## Trips that already happened but are still marked booked ({len(past)})")
        for st, b in past:
            print(f"- {b.get('client','')} {route_of(b)} ended {st['ends']} · `{rel(Path(b['_path']))}` (set \"status\": \"completed\")")

    if ag.get("name") == STARTER_AGENCY["name"]:
        print("\nagency.json still has the starter values. Run `/travel-desk:setup` to fill in your agency details.")
    return 0


# ----------------------------------------------------------------------------
# proposal rendering
# ----------------------------------------------------------------------------

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def paragraphs(text) -> str:
    if not text:
        return ""
    if isinstance(text, list):
        return "".join(f"<p>{esc(t)}</p>" for t in text if t)
    parts = [p.strip() for p in re.split(r"\n\s*\n", str(text)) if p.strip()]
    return "".join(f"<p>{esc(p)}</p>" for p in parts)


def ul(items, cls="") -> str:
    items = [i for i in (items or []) if i]
    if not items:
        return ""
    c = f' class="{cls}"' if cls else ""
    return f"<ul{c}>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def ol(items, cls="") -> str:
    items = [i for i in (items or []) if i]
    if not items:
        return ""
    c = f' class="{cls}"' if cls else ""
    return f"<ol{c}>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ol>"


def mix(hex_color: str, other: str, t: float) -> str:
    """Blend hex_color toward other by t (0..1)."""
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    c = [round(x + (y - x) * t) for x, y in zip(a, b)]
    return "#" + "".join(f"{v:02x}" for v in c)


def fmt_points(v) -> str:
    if isinstance(v, (int, float)):
        return f"{int(v):,}"
    return esc(v)


def render_proposal(spec: dict, ag: dict) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    ag = {**ag, **(spec.get("agency") or {})}
    brand = ag.get("brand_color") or "#0f4c5c"
    if not HEX.match(brand):
        warn(f"brand_color '{brand}' is not a 6-digit hex; using default")
        brand = "#0f4c5c"

    client = spec.get("client") or {}
    client_name = client.get("name") if isinstance(client, dict) else str(client)
    prepared = parse_date(spec.get("prepared_on")) or today()
    trip = spec.get("trip") or {}

    facts = []
    for label, key in (("Route", "route"), ("Dates", "dates"), ("Travelers", "travelers"), ("Cabin", "cabin"), ("Flexibility", "flexibility")):
        if trip.get(key):
            facts.append(f'<div class="fact"><dt>{esc(label)}</dt><dd>{esc(trip[key])}</dd></div>')
    trip_facts = f'<dl class="facts">{"".join(facts)}</dl>' if facts else ""

    options_html = []
    for i, o in enumerate(spec.get("options") or [], 1):
        rec = bool(o.get("recommended"))
        label = o.get("label") or ("Recommended" if rec else f"Option {i}")
        rows = []
        for lab, key in (("How you'd book", "how"), ("Routing", "routing"), ("Points used", "points"), ("Cash due", "cash"), ("Value", "value"), ("Notes", "notes")):
            if o.get(key):
                rows.append(f"<div class=\"row\"><dt>{esc(lab)}</dt><dd>{esc(o[key])}</dd></div>")
        options_html.append(
            f'<article class="option{" recommended" if rec else ""}">'
            f'<div class="option-head"><span class="eyebrow">{esc(label)}</span><h3>{esc(o.get("name", f"Option {i}"))}</h3></div>'
            f'<dl class="option-rows">{"".join(rows)}</dl>'
            f"</article>"
        )
    options_block = ""
    if options_html:
        options_block = f'<section class="section"><h2>Your options</h2><div class="options">{"".join(options_html)}</div></section>'

    bench = spec.get("cash_benchmark")
    bench_block = f'<aside class="benchmark"><span class="eyebrow">For comparison</span><p>{esc(bench)}</p></aside>' if bench else ""

    why_block = ""
    if spec.get("why"):
        why_block = f'<section class="section"><h2>Why this works for you</h2>{ul(spec["why"], "why")}</section>'

    steps_block = ""
    if spec.get("next_steps"):
        steps_block = f'<section class="section"><h2>What happens next</h2>{ol(spec["next_steps"], "steps")}</section>'

    points_block = ""
    snap = spec.get("points_snapshot") or []
    after = spec.get("balances_after") or []
    if after:
        rows = "".join(
            f"<tr><td>{esc(r.get('program'))}</td><td class=\"num\">{fmt_points(r.get('before'))}</td><td class=\"num\">{fmt_points(r.get('after'))}</td></tr>"
            for r in after
        )
        points_block = (
            '<section class="section"><h2>Your points, before and after</h2>'
            '<div class="table-wrap"><table class="points"><thead><tr><th>Program</th><th class="num">Today</th><th class="num">After booking</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></section>"
        )
    elif snap:
        rows = "".join(f"<tr><td>{esc(r.get('program'))}</td><td class=\"num\">{fmt_points(r.get('balance'))}</td></tr>" for r in snap)
        points_block = (
            '<section class="section"><h2>Your points today</h2>'
            '<div class="table-wrap"><table class="points"><thead><tr><th>Program</th><th class="num">Balance</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></section>"
        )

    # A "fee" key in the spec wins even when empty (empty means: no fee line). Without the key, agency.json decides.
    fee = spec["fee"] if "fee" in spec else ag.get("award_booking_fee")
    fee = (fee or "").strip()
    fee_block = f'<p class="fee">{esc(fee)}</p>' if fee else ""

    fine = spec.get("fine_print") or []
    fine_block = f'<section class="section fine"><h2>Good to know</h2>{ul(fine)}</section>' if fine else ""

    contact_bits = [esc(x) for x in (ag.get("phone"), ag.get("email"), ag.get("website")) if x]
    contact = " · ".join(contact_bits)

    title = spec.get("title") or f"{trip.get('route', 'Your trip')}"
    page_title = f"{title} · {ag.get('name')}"

    filled = {
        "PAGE_TITLE": esc(page_title),
        "BRAND": brand,
        "BRAND_TINT": mix(brand, "#ffffff", 0.88),
        "BRAND_TINT_DARK": mix(brand, "#0f1418", 0.72),
        "BRAND_SOFT": mix(brand, "#ffffff", 0.35),
        "AGENCY_NAME": esc(ag.get("name")),
        "AGENT_NAME": esc(ag.get("agent_name")),
        "TAGLINE": esc(ag.get("tagline") or ""),
        "CONTACT": contact,
        "CLIENT_NAME": esc(client_name or "you"),
        "PREPARED_ON": esc(human_date(prepared)),
        "TRIP_TITLE": esc(title),
        "TRIP_FACTS": trip_facts,
        "SUMMARY": paragraphs(spec.get("summary")),
        "OPTIONS": options_block,
        "BENCHMARK": bench_block,
        "WHY": why_block,
        "NEXT_STEPS": steps_block,
        "POINTS": points_block,
        "FEE": fee_block,
        "FINE_PRINT": fine_block,
        "YEAR": str(prepared.year),
    }
    out = tpl
    for k, v in filled.items():
        out = out.replace("{{" + k + "}}", v)
    leftover = re.findall(r"{{[A-Z_]+}}", out)
    if leftover:
        warn("template placeholders not filled: " + ", ".join(sorted(set(leftover))))
    return out


def cmd_render_proposal(args) -> int:
    src = Path(args.spec).expanduser()
    if not src.is_absolute() and not src.exists():
        src = home() / "proposals" / src
    if not src.exists():
        print(f"not found: {args.spec}", file=sys.stderr)
        return 1
    spec = load_json(src)
    required = ["client", "options"]
    missing = [k for k in required if not spec.get(k)]
    if missing:
        print("proposal spec is missing: " + ", ".join(missing), file=sys.stderr)
        return 1
    out = Path(args.out).expanduser() if args.out else src.with_suffix(".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_proposal(spec, agency()), encoding="utf-8")
    print(str(out))
    return 0


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="desk.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the desk folder structure").set_defaults(fn=cmd_init)
    sub.add_parser("paths", help="print resolved paths").set_defaults(fn=cmd_paths)

    p = sub.add_parser("status", help="the morning view")
    p.add_argument("--days", type=int, default=14, help="departure window in days (default 14)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("clients", help="list clients")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_clients)

    p = sub.add_parser("client", help="show one client")
    p.add_argument("slug")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_client)

    p = sub.add_parser("reservations", help="merge bookings into one JSON array")
    p.add_argument("--client")
    p.add_argument("--upcoming", action="store_true", help="only trips that have not ended")
    p.add_argument("--days", type=int, help="only trips departing within N days")
    p.add_argument("--due-only", action="store_true", help="only bookings due for an audit")
    p.set_defaults(fn=cmd_reservations)

    p = sub.add_parser("due", help="bookings due for an audit")
    p.add_argument("--client")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_due)

    p = sub.add_parser("mark-audited", help="stamp bookings as audited")
    p.add_argument("files", nargs="+")
    p.add_argument("--date", help="YYYY-MM-DD (default today)")
    p.set_defaults(fn=cmd_mark_audited)

    p = sub.add_parser("render-proposal", help="render a proposal JSON spec to HTML")
    p.add_argument("spec", help="path to the .json spec (absolute, or relative to proposals/)")
    p.add_argument("-o", "--out", help="output .html path (default: next to the spec)")
    p.set_defaults(fn=cmd_render_proposal)

    p = sub.add_parser("slug", help="slug for a client name")
    p.add_argument("name", nargs="+")
    p.set_defaults(fn=cmd_slug)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
