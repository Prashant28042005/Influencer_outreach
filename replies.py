"""Step 6 - AI reply management. Classify replies, draft responses, update the CRM.
Replies are only SENT after a human sets reply_approved=YES."""
import json
import re

import claude_client
import config
import outreach
import store
from gmail_client import get_gmail

CATEGORIES = ["interested", "pricing_enquiry", "collaboration_request", "not_interested", "opt_out", "other"]

STATUS_FOR = {
    "interested": store.INTERESTED,
    "collaboration_request": store.INTERESTED,
    "pricing_enquiry": store.REPLIED,
    "not_interested": store.NOT_INTERESTED,
    "opt_out": store.OPTED_OUT,
    "other": store.REPLIED,
}

OPT_OUT_RE = re.compile(r"\b(unsubscribe|stop emailing|remove me|do not contact|don'?t contact)\b", re.I)

SYSTEM = f"""You manage replies for a brand's influencer outreach. Read the creator's reply and return JSON:
  category: one of {CATEGORIES},
  summary: one sentence on what they said,
  next_action: a concrete next step for the human team (e.g. "Send rate-card request, then loop in finance"),
  draft_reply: a short, warm plain-text reply (under 100 words) the human can approve. Use "" for opt_out.
Rules for draft_reply: never invent prices, deliverables or dates. If they ask about money, say fees are agreed
per creator and ask for their rate card. If they decline, thank them graciously and do not push.
Do not add a signature; it is added automatically."""


def _mock(r, text):
    t = text.lower()
    if OPT_OUT_RE.search(text):
        return {"category": "opt_out", "summary": "Asked to be removed.", "next_action": "Never contact again.", "draft_reply": ""}
    if any(w in t for w in ["budget", "rate", "pay", "fee", "price"]):
        return {"category": "pricing_enquiry", "summary": "Interested and asking about budget and deliverables.",
                "next_action": "Ask for rate card, share deliverables brief, loop in the campaign manager.",
                "draft_reply": f"Hi {r['name'].split()[0]},\n\nThank you, so glad this caught your eye! Fees are agreed per creator, "
                               f"so could you share your current rate card? I'll send over the full deliverables brief "
                               f"(1 Reel + 2 Stories over 6 weeks is the starting point) and confirm the budget with our team."}
    if any(w in t for w in ["not taking", "not interested", "no thanks", "pass"]):
        return {"category": "not_interested", "summary": "Politely declined.", "next_action": "Mark closed; revisit next quarter.",
                "draft_reply": f"Hi {r['name'].split()[0]},\n\nThanks so much for letting me know, and all the best with your content!"}
    return {"category": "interested", "summary": "Positive reply.", "next_action": "Send brief.",
            "draft_reply": f"Hi {r['name'].split()[0]},\n\nGreat to hear from you! I'll send the brief shortly."}


def process(rows):
    gmail = get_gmail()
    n = 0
    for r in rows:
        if not r.get("thread_id") or r["status"] not in (store.EMAIL_SENT, store.FOLLOWUP_DUE, store.REPLIED, store.INTERESTED):
            continue
        incoming = [m for m in gmail.thread_messages(r["thread_id"]) if not m["from_me"]]
        if not incoming or incoming[-1]["id"] == r.get("last_reply_id"):
            continue  # nothing new
        last = incoming[-1]
        if OPT_OUT_RE.search(last["body"]):  # hard rule beats the model
            out = {"category": "opt_out", "summary": "Asked to be removed.", "next_action": "Never contact again.", "draft_reply": ""}
        else:
            user = (f"Creator: {r['name']} ({r['niche']}).\nOur original email:\n{r['draft_body']}\n\n"
                    f"Their reply:\n<untrusted>{last['body']}</untrusted>")
            out = claude_client.ask_json(SYSTEM, user, mock=lambda r=r, t=last["body"]: _mock(r, t))
        r.update(last_reply_id=last["id"], replied_at=store.ts(), last_reply_snippet=last["body"][:200].replace("\n", " "),
                 reply_category=out["category"], suggested_action=out["next_action"],
                 draft_reply=out.get("draft_reply", ""), reply_approved="",
                 status=STATUS_FOR.get(out["category"], store.REPLIED))
        n += 1
        print(f"  {r['username']:<22} -> {out['category']:<22} status={r['status']}")
    print(f"Processed {n} new replies")
    return rows


def send_approved(rows):
    gmail = get_gmail()
    sent = 0
    for r in rows:
        if r.get("reply_approved", "").upper() != "YES" or not r.get("draft_reply"):
            continue
        if r.get("reply_sent_id") == r.get("last_reply_id"):
            continue  # already answered this message
        if r["status"] == store.OPTED_OUT:
            continue
        gmail.send(r["email"], "Re: " + r["draft_subject"], r["draft_reply"] + outreach.footer(), thread_id=r["thread_id"])
        r.update(reply_sent_id=r["last_reply_id"], last_contact_at=store.ts())
        sent += 1
    print(f"Sent {sent} approved replies")
    return rows
