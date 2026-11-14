"""Gmail access. `live` uses the Gmail API (OAuth); `mock` simulates a mailbox on disk
so the full workflow can be tested without sending anything."""
import base64
import json
import re
from email.mime.text import MIMEText

import config

SCOPES = ["https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/gmail.readonly"]


def strip_quoted(text: str) -> str:
    """Keep only the new part of a reply (drop quoted history)."""
    out = []
    for line in text.splitlines():
        if line.startswith(">") or re.match(r"^On .+ wrote:$", line.strip()):
            break
        out.append(line)
    return "\n".join(out).strip()


class MockGmail:
    outbox = config.DATA / "outbox.jsonl"

    def _sent(self):
        if not self.outbox.exists():
            return []
        return [json.loads(l) for l in self.outbox.read_text(encoding="utf-8").splitlines() if l]

    def send(self, to, subject, body, thread_id=None):
        thread_id = thread_id or f"mock-{to}"
        msg_id = f"mock-sent-{len(self._sent()) + 1}"
        with open(self.outbox, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": msg_id, "thread_id": thread_id, "to": to,
                                "subject": subject, "body": body}) + "\n")
        print(f"    [MOCK GMAIL] sent to {to}: {subject}")
        return msg_id, thread_id

    def thread_messages(self, thread_id):
        msgs = [{"id": m["id"], "from_me": True, "body": m["body"]}
                for m in self._sent() if m["thread_id"] == thread_id]
        if not msgs:
            return []
        email = thread_id.replace("mock-", "", 1)
        inbox = json.loads((config.DATA / "mock_inbox.json").read_text(encoding="utf-8"))
        msgs += [{"id": m["id"], "from_me": False, "body": m["body"]} for m in inbox if m["from"] == email]
        return msgs


class LiveGmail:
    def __init__(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        import os
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES).run_local_server(port=0)
            open("token.json", "w").write(creds.to_json())
        self.svc = build("gmail", "v1", credentials=creds)

    def send(self, to, subject, body, thread_id=None):
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        payload = {}
        if thread_id:
            thread = self.svc.users().threads().get(userId="me", id=thread_id, format="metadata",
                                                    metadataHeaders=["Message-ID", "Subject"]).execute()
            last = thread["messages"][-1]["payload"]["headers"]
            mid = next((h["value"] for h in last if h["name"].lower() == "message-id"), None)
            if mid:
                msg["In-Reply-To"] = mid
                msg["References"] = mid
            payload["threadId"] = thread_id
        payload["raw"] = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = self.svc.users().messages().send(userId="me", body=payload).execute()
        return sent["id"], sent["threadId"]

    @staticmethod
    def _body(payload):
        if payload.get("mimeType") == "text/plain" and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "ignore")
        for part in payload.get("parts", []) or []:
            text = LiveGmail._body(part)
            if text:
                return text
        return ""

    def thread_messages(self, thread_id):
        thread = self.svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
        return [{"id": m["id"], "from_me": "SENT" in m.get("labelIds", []),
                 "body": strip_quoted(self._body(m["payload"]))} for m in thread["messages"]]


def get_gmail():
    return LiveGmail() if config.GMAIL_MODE == "live" else MockGmail()
