"""Step 5 - automatic follow-ups (day 3-5, then 5-7 days later). Stops on any reply."""
import json

import claude_client
import config
import outreach
import store
from gmail_client import get_gmail

SYSTEM = """You write a brief, friendly follow-up to an unanswered cold email from a brand to a creator.
Rules: under 70 words, plain text, no guilt-tripping, add one new small piece of value or a lower-effort
ask. Follow-up #2 must be a polite last note that makes it easy to say no. No signature or opt-out line.
Return JSON: {"body": "..."} starting with 'Hi <first name>,'."""


def _mock(r, n):
    first = r["name"].split()[0]
    if n == 1:
        return {"body": f"Hi {first},\n\nJust floating my earlier note back to the top of your inbox. "
                        f"Happy to send a one-page brief on the {config.BRAND['name']} Monsoon Glow collab "
                        f"so you can see the details before deciding. Would that be useful?"}
    return {"body": f"Hi {first},\n\nLast note from me - I don't want to clutter your inbox. "
                    f"If the timing isn't right, no worries at all. If you'd like the brief, "
                    f"just reply 'yes' and I'll send it over."}


def _due(r):
    last = store.parse_ts(r.get("last_contact_at"))
    if not last:
        return 0
    days = (store.now() - last).days
    n = int(r.get("followup_count") or 0)
    if n == 0 and days >= config.FOLLOWUP1_DAYS:
        return 1
    if n == 1 and days >= config.FOLLOWUP2_DAYS:
        return 2
    return 0


def run(rows):
    gmail = get_gmail()
    sent = 0
    for r in rows:
        if r["status"] not in (store.EMAIL_SENT, store.FOLLOWUP_DUE):
            continue  # replied / declined / opted out => sequence stops here
        n = _due(r)
        if not n:
            continue
        # Safety: re-check the live thread so we never follow up on someone who just replied.
        if any(not m["from_me"] for m in gmail.thread_messages(r["thread_id"])):
            print(f"  {r['username']} has replied, skipping follow-up")
            continue
        r["status"] = store.FOLLOWUP_DUE
        if outreach.sent_today(rows) >= config.DAILY_SEND_LIMIT:
            print("Daily send limit reached; remaining follow-ups stay 'Follow-up Due'.")
            break
        user = (f"Creator: {r['name']} ({r['niche']}). Follow-up number: {n}.\n"
                f"Original email:\n{r['draft_body']}")
        out = claude_client.ask_json(SYSTEM, user, mock=lambda r=r, n=n: _mock(r, n))
        subject = "Re: " + r["draft_subject"]
        gmail.send(r["email"], subject, out["body"] + outreach.footer(), thread_id=r["thread_id"])
        r.update(status=store.EMAIL_SENT, followup_count=n, last_contact_at=store.ts())
        sent += 1
        print(f"  follow-up #{n} sent to {r['username']}")
    print(f"Sent {sent} follow-ups")
    return rows
