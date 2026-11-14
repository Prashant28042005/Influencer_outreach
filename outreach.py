"""Step 4 - personalised cold email. Claude drafts, a human approves, then we send."""
import json
import random
import time

import claude_client
import config
import store
from gmail_client import get_gmail

SYSTEM = """You write short, warm, specific cold emails from a brand to an Instagram creator.
Rules: under 140 words, plain text, no hype, no fake claims, no pretending a prior relationship.
Must: introduce the brand, explain the collaboration, say specifically why THIS creator was chosen
(reference their content), and end with ONE clear call to action (a short reply or a call).
Do not write a signature or opt-out line; those are added automatically.
Return JSON: {"subject": "...", "body": "..."} where body starts with 'Hi <first name>,'."""


def footer() -> str:
    return (f"\n\nBest,\n{config.SENDER_NAME}\n{config.SENDER_TITLE}, {config.SENDER_COMPANY}\n"
            f"{config.BRAND['website']}\n\n---\n"
            f"You're receiving this because your public Instagram profile lists a business email. "
            f"If you'd rather not hear from me, just reply \"unsubscribe\" and I won't contact you again.\n"
            f"{config.SENDER_COMPANY}, {config.SENDER_ADDRESS}")


def _mock(r):
    first = r["name"].split()[0]
    return {
        "subject": f"{config.BRAND['name']} x {r['name']} - Monsoon Glow collab?",
        "body": (f"Hi {first},\n\nI'm {config.SENDER_NAME} from {config.BRAND['name']}, an Indian skincare brand "
                 f"making vegan, dermatologist-tested serums. I came across your {r['niche']} content "
                 f"({r['summary']}) and your honest, ingredient-first style is exactly what we look for.\n\n"
                 f"We're launching a Vitamin C + Niacinamide serum and are working with a small group of creators "
                 f"on a 6-week partnership: a free product kit, a paid content fee and a 10% affiliate code "
                 f"for your audience.\n\nWould you be open to a quick reply if this sounds interesting? "
                 f"I can then share the full brief."),
    }


def draft_emails(rows):
    n = 0
    for r in rows:
        if r["status"] != store.EMAIL_AVAILABLE or r.get("draft_body"):
            continue
        if float(r.get("score") or 0) < config.MIN_SCORE:
            continue
        user = (f"BRAND BRIEF:\n{json.dumps(config.BRAND)}\n\nCREATOR:\nname: {r['name']}\n"
                f"niche: {r['niche']}\nfollowers: {r['followers']}\nlocation: {r['location']}\n"
                f"analyst summary: {r['summary']}\n<untrusted>{r['bio']}</untrusted>")
        out = claude_client.ask_json(SYSTEM, user, mock=lambda r=r: _mock(r))
        r["draft_subject"], r["draft_body"] = out["subject"], out["body"]
        n += 1
        print(f"  drafted email for {r['username']}")
    print(f"{n} drafts written. Review them, then set approved=YES (or run: python main.py approve --kind email --all)")
    return rows


def sent_today(rows) -> int:
    today = store.ts()[:10]
    return sum(1 for r in rows if (r.get("last_contact_at") or "").startswith(today))


def send_approved(rows):
    gmail = get_gmail()
    sent = 0
    for r in rows:
        if r.get("approved", "").upper() != "YES" or r["status"] != store.EMAIL_AVAILABLE:
            continue
        if sent_today(rows) >= config.DAILY_SEND_LIMIT:
            print(f"Daily limit of {config.DAILY_SEND_LIMIT} reached, stopping.")
            break
        _, thread_id = gmail.send(r["email"], r["draft_subject"], r["draft_body"] + footer())
        r.update(status=store.EMAIL_SENT, thread_id=thread_id, email_sent_at=store.ts(),
                 last_contact_at=store.ts(), followup_count=0)
        sent += 1
        if config.GMAIL_MODE == "live":
            time.sleep(random.randint(30, 90))  # spread sends out
    print(f"Sent {sent} initial emails")
    return rows
