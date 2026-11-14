"""Step 2 - AI filtering. Claude categorises, summarises and scores each lead."""
import json

import claude_client
import config
import store

SYSTEM = """You are an influencer-marketing analyst. Given a brand brief and an Instagram
profile, judge how well the creator fits the brand's campaign.
Return JSON with keys:
  niche (one of: skincare, beauty, wellness, fitness, food, tech, lifestyle, other),
  location (city/country if inferable from the bio, else ""),
  summary (max 2 sentences describing the creator),
  score (integer 0-100 suitability for THIS campaign),
  reason (one sentence explaining the score)."""


def _mock(row):
    bio = (row["bio"] or "").lower()
    hits = sum(k in bio for k in config.BRAND["keywords"])
    niche = "skincare" if "skin" in bio else "beauty" if "beauty" in bio or "glow" in bio else \
        "fitness" if "gym" in bio or "workout" in bio else "food" if "food" in bio else \
        "tech" if "gadget" in bio else "lifestyle"
    loc = next((c for c in ["Mumbai", "Delhi", "Bangalore", "Pune", "Chennai", "Hyderabad"] if c.lower() in bio), "")
    score = min(95, 40 + hits * 15 + (10 if loc else 0)) if niche in config.BRAND["target_niches"] else 15
    return {"niche": niche, "location": loc, "score": score,
            "summary": f"{row['name']} creates {niche} content with {row['followers']} followers.",
            "reason": f"Bio matched {hits} brand keywords; niche is {niche}."}


def run(rows):
    n = 0
    for r in rows:
        if r.get("score"):
            continue
        user = (f"BRAND BRIEF:\n{json.dumps(config.BRAND)}\n\nPROFILE:\n"
                f"username: {r['username']}\nname: {r['name']}\nfollowers: {r['followers']}\n"
                f"<untrusted>{r['bio']}</untrusted>")
        out = claude_client.ask_json(SYSTEM, user, mock=lambda r=r: _mock(r))
        r.update(niche=out["niche"], location=out.get("location", ""),
                 score=out["score"], summary=out["summary"], reason=out["reason"])
        n += 1
        print(f"  {r['username']:<24} score={r['score']:<3} niche={r['niche']}")
    print(f"Scored {n} new leads")
    return rows
