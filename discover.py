"""Step 1 - Instagram research.

Instagram has no public keyword-search API and scraping breaks its terms, so this
uses a compliant approach:
  1. You curate a seed list of public accounts (data/seed_accounts.csv), found
     manually via hashtags / Explore / competitor tags.
  2. We enrich each one with the official Instagram Graph API "Business Discovery"
     endpoint, which returns only public data for Business/Creator accounts.
  3. A public business email is pulled from the bio text if the creator listed one.
"""
import csv
import re
import time
import json

import config
import store

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_email(text: str) -> str:
    m = EMAIL_RE.search(text or "")
    return m.group(0).lower() if m else ""


def load_seeds():
    with open(config.DATA / "seed_accounts.csv", newline="", encoding="utf-8") as f:
        return [r["username"].strip().lstrip("@") for r in csv.DictReader(f) if r["username"].strip()]


def fetch_profile_live(username: str):
    import requests
    fields = f"business_discovery.username({username}){{username,name,biography,followers_count,media_count,website}}"
    r = requests.get(
        f"https://graph.facebook.com/v21.0/{config.IG_USER_ID}",
        params={"fields": fields, "access_token": config.IG_ACCESS_TOKEN},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  ! {username}: not available via Business Discovery ({r.json().get('error', {}).get('message', r.status_code)})")
        return None
    time.sleep(1)  # be polite to the API
    return r.json()["business_discovery"]


def fetch_profile_mock(username: str):
    profiles = json.loads((config.DATA / "mock_profiles.json").read_text(encoding="utf-8"))
    return profiles.get(username)


def to_row(p: dict) -> dict:
    bio = p.get("biography", "")
    email = extract_email(bio)
    return {
        "username": p["username"],
        "name": p.get("name", ""),
        "profile_url": f"https://www.instagram.com/{p['username']}/",
        "followers": p.get("followers_count", ""),
        "email": email,
        "bio": bio,
        "location": "",
        "status": store.EMAIL_AVAILABLE if email else store.NO_EMAIL,
        "followup_count": 0,
        "added_at": store.ts(),
    }


def run(rows):
    live = bool(config.IG_ACCESS_TOKEN and config.IG_USER_ID)
    print(f"Discovery mode: {'Instagram Graph API' if live else 'MOCK (data/mock_profiles.json)'}")
    added = skipped = 0
    for username in load_seeds():
        p = fetch_profile_live(username) if live else fetch_profile_mock(username)
        if not p:
            print(f"  - {username}: no public profile data, skipped")
            continue
        fol = p.get("followers_count", 0)
        if not (config.BRAND["min_followers"] <= fol <= config.BRAND["max_followers"]):
            print(f"  - {username}: {fol} followers outside target range, skipped")
            continue
        row = to_row(p)
        if store.find_duplicate(rows, row):
            skipped += 1
            print(f"  - {username}: duplicate, skipped")
            continue
        rows.append(row)
        added += 1
        print(f"  + {username}: {fol} followers, email={'yes' if row['email'] else 'no'}")
    print(f"Discovery finished: {added} added, {skipped} duplicates")
    return rows
