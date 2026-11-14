"""Central configuration. Everything is driven by environment variables (.env)."""
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional in mock mode
    pass

ROOT = Path(__file__).parent
DATA = ROOT / "data"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")

GMAIL_MODE = os.getenv("GMAIL_MODE", "mock").lower()
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")
SENDER_TITLE = os.getenv("SENDER_TITLE", "Partnerships Associate")
SENDER_COMPANY = os.getenv("SENDER_COMPANY", "GlowLeaf Naturals")
SENDER_ADDRESS = os.getenv("SENDER_ADDRESS", "Your postal address here")

STORE_BACKEND = os.getenv("STORE_BACKEND", "csv").lower()
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Influencer CRM")

DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "20"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "60"))
FOLLOWUP1_DAYS = int(os.getenv("FOLLOWUP1_DAYS", "4"))
FOLLOWUP2_DAYS = int(os.getenv("FOLLOWUP2_DAYS", "6"))

# Demo helper: pretend N days have passed so follow-ups can be shown without waiting.
TIME_OFFSET_DAYS = int(os.getenv("TIME_OFFSET_DAYS", "0"))

BRAND = json.loads((DATA / "brand.json").read_text(encoding="utf-8"))
