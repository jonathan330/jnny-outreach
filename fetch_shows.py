"""Fetch upcoming Austin music events from Ticketmaster and write shows.json."""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

KEY = os.environ.get("TICKETMASTER_KEY")
if not KEY:
    sys.exit("Missing TICKETMASTER_KEY")

DAYS_AHEAD = 90
SKIP = ("parking", "vip upgrade", "vip package", "meet & greet", "meet and greet", "hospitality")
now = datetime.now(timezone.utc)
start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
end = (now + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%dT%H:%M:%SZ")

def get(page):
    q = {
        "apikey": KEY, "classificationName": "music", "city": "Austin",
        "stateCode": "TX", "countryCode": "US", "startDateTime": start,
        "endDateTime": end, "size": 100, "page": page, "sort": "date,asc",
    }
    url = "https://app.ticketmaster.com/discovery/v2/events.json?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

shows, seen, page = [], set(), 0
while True:
    data = get(page)
    for ev in data.get("_embedded", {}).get("events", []):
        name = ev.get("name", "")
        if any(s in name.lower() for s in SKIP):
            continue
        atts = ev.get("_embedded", {}).get("attractions", [])
        artist = atts[0]["name"] if atts else name
        date = ev.get("dates", {}).get("start", {}).get("localDate")
        if not date:
            continue
        key = (artist.lower(), date)
        if key in seen:
            continue
        seen.add(key)
        cls = (atts[0].get("classifications") if atts else None) or ev.get("classifications") or [{}]
        genre = (cls[0].get("genre") or {}).get("name") or "Other"
        if genre == "Undefined":
            genre = "Other"
        venues = ev.get("_embedded", {}).get("venues", [{}])
        shows.append({
            "artist": artist,
            "event": name,
            "date": date,
            "time": ev.get("dates", {}).get("start", {}).get("localTime", ""),
            "venue": venues[0].get("name", "TBA"),
            "genre": genre,
            "subgenre": (cls[0].get("subGenre") or {}).get("name", ""),
            "url": ev.get("url", ""),
        })
    info = data.get("page", {})
    page += 1
    # Ticketmaster limits deep paging (size * page < 1000)
    if page >= info.get("totalPages", 0) or page * 100 >= 1000:
        break
    time.sleep(0.3)

shows.sort(key=lambda s: (s["date"], s["artist"]))
out = {"updated": now.strftime("%Y-%m-%d %H:%M UTC"), "shows": shows}
with open("shows.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Wrote {len(shows)} shows")