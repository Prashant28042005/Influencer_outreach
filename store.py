"""CRM storage. Two interchangeable backends: a local CSV and a Google Sheet."""
import csv
from datetime import datetime, timedelta, timezone

import config

# --- Pipeline statuses (from the assignment brief, plus two practical extras) ---
NEW_LEAD = "New Lead"
NO_EMAIL = "No Email"
EMAIL_AVAILABLE = "Email Available"
EMAIL_SENT = "Email Sent"
FOLLOWUP_DUE = "Follow-up Due"
REPLIED = "Replied"
INTERESTED = "Interested"
NOT_INTERESTED = "Not Interested"
OPTED_OUT = "Opted Out"
CONFIRMED = "Collaboration Confirmed"

FIELDS = [
    "username", "name", "profile_url", "niche", "followers", "email", "location", "bio",
    "score", "summary", "reason", "status",
    "draft_subject", "draft_body", "approved",
    "email_sent_at", "last_contact_at", "followup_count", "thread_id",
    "last_reply_id", "replied_at", "last_reply_snippet", "reply_category",
    "suggested_action", "draft_reply", "reply_approved", "reply_sent_id",
    "added_at", "notes",
]


def now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=config.TIME_OFFSET_DAYS)


def ts(dt: datetime = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M")


def parse_ts(s: str):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


class CsvStore:
    def __init__(self, path=None):
        self.path = path or (config.ROOT / "influencer_crm.csv")

    def read(self):
        if not self.path.exists():
            return []
        with open(self.path, newline="", encoding="utf-8") as f:
            return [dict(r) for r in csv.DictReader(f)]

    def write(self, rows):
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in FIELDS})


class SheetsStore:
    """Google Sheet backend. First run opens a browser for OAuth (credentials.json)."""

    def __init__(self):
        import gspread
        gc = gspread.oauth(credentials_filename="credentials.json",
                           authorized_user_filename="sheets_token.json")
        try:
            sh = gc.open(config.GOOGLE_SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(config.GOOGLE_SHEET_NAME)
        self.ws = sh.sheet1
        print(f"Using Google Sheet: {sh.url}")

    def read(self):
        values = self.ws.get_all_values()
        if len(values) < 2:
            return []
        header = values[0]
        return [dict(zip(header, row)) for row in values[1:]]

    def write(self, rows):
        values = [FIELDS] + [[str(r.get(k, "")) for k in FIELDS] for r in rows]
        self.ws.clear()
        self.ws.update(values=values, range_name="A1")


def get_store():
    return SheetsStore() if config.STORE_BACKEND == "sheets" else CsvStore()


def find_duplicate(rows, profile):
    """Dedupe on Instagram username OR email (case-insensitive)."""
    u = profile["username"].lower()
    e = (profile.get("email") or "").lower()
    for r in rows:
        if r["username"].lower() == u:
            return r
        if e and (r.get("email") or "").lower() == e:
            return r
    return None
