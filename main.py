"""CLI entry point.  python main.py --help"""
import argparse
import os

import config
import store


def main():
    p = argparse.ArgumentParser(description="AI influencer research & email outreach automation")
    p.add_argument("command", choices=["discover", "score", "draft", "approve", "send", "replies",
                                       "followups", "send-replies", "prepare", "daily", "status"])
    p.add_argument("--kind", choices=["email", "reply"], default="email", help="for 'approve'")
    p.add_argument("--usernames", help="comma-separated usernames for 'approve'")
    p.add_argument("--all", action="store_true", help="approve everything pending")
    p.add_argument("--days-offset", type=int, default=0, help="demo only: pretend N days have passed")
    a = p.parse_args()

    if a.days_offset:
        config.TIME_OFFSET_DAYS = a.days_offset

    import discover, score, outreach, followups, replies  # imported late so config changes apply
    db = store.get_store()
    rows = db.read()
    cmds = {
        "discover": [discover.run], "score": [score.run], "draft": [outreach.draft_emails],
        "send": [outreach.send_approved], "replies": [replies.process],
        "followups": [followups.run], "send-replies": [replies.send_approved],
        "prepare": [discover.run, score.run, outreach.draft_emails],            # then human approves
        "daily": [replies.process, followups.run, outreach.send_approved, replies.send_approved],
    }

    if a.command == "approve":
        names = {n.strip().lower() for n in (a.usernames or "").split(",") if n.strip()}
        field, need = ("approved", "draft_body") if a.kind == "email" else ("reply_approved", "draft_reply")
        for r in rows:
            if r.get(need) and (a.all or r["username"].lower() in names):
                r[field] = "YES"
                print(f"  approved {a.kind} for {r['username']}")
    elif a.command == "status":
        from collections import Counter
        for s, c in Counter(r["status"] for r in rows).most_common():
            print(f"  {s:<24}{c}")
    else:
        for fn in cmds[a.command]:
            rows = fn(rows)
    db.write(rows)


if __name__ == "__main__":
    main()
