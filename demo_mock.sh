#!/usr/bin/env bash
# Runs the complete workflow offline with fake data. Safe: nothing is sent anywhere.
set -e
rm -f influencer_crm.csv data/outbox.jsonl
python main.py discover
python main.py score
python main.py draft
python main.py approve --kind email --all     # <- in real use you do this by reviewing each draft
python main.py send
python main.py replies                         # detects + classifies replies, drafts responses
python main.py followups --days-offset 5       # simulates 5 days passing -> follow-up #1
python main.py followups --days-offset 12      # simulates 12 days -> follow-up #2
python main.py approve --kind reply --all
python main.py send-replies
python main.py status
