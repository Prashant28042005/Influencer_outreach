# AI-Powered Instagram Influencer Research & Email Outreach

Python pipeline: Instagram research -> Claude scoring -> CRM (CSV / Google Sheets) -> Claude-written Gmail outreach
-> automatic follow-ups -> reply classification -> Claude reply drafts -> CRM status updates.
Humans approve the first send and every AI reply.

## How it works
| Step | Command | What happens |
|---|---|---|
| 1 Research | `python main.py discover` | Reads `data/seed_accounts.csv`, enriches each public account through the Instagram Graph API *Business Discovery* endpoint (followers, bio), pulls a public email from the bio, filters by follower range, skips duplicates (username or email). |
| 2 AI filtering | `python main.py score` | Claude returns niche, location, 2-line summary, 0-100 suitability score and reason. |
| 3 CRM | automatic | Every command reads/writes the CRM. Statuses: New Lead, Email Available, Email Sent, Follow-up Due, Replied, Interested, Not Interested, Collaboration Confirmed (+ No Email, Opted Out). |
| 4 Cold email | `python main.py draft` then review, set `approved=YES`, then `python main.py send` | Claude drafts a personalised email for leads with score >= `MIN_SCORE`. Sender identity, postal address and opt-out line are appended in code, so Claude can't omit them. Daily cap + random delay when live. |
| 5 Follow-ups | `python main.py followups` | Follow-up 1 after `FOLLOWUP1_DAYS` (default 4), follow-up 2 after `FOLLOWUP2_DAYS` (default 6). Only leads still in Email Sent / Follow-up Due are touched, and the live Gmail thread is re-checked for a reply before each send. |
| 6 Replies | `python main.py replies`, review, set `reply_approved=YES`, `python main.py send-replies` | Claude classifies (interested / pricing_enquiry / collaboration_request / not_interested / opt_out / other), suggests the next action, drafts a reply and updates status. Opt-out keywords ("unsubscribe", "stop emailing"...) are caught by a hard rule that overrides the model. |

Daily routine once approved: `python main.py daily`  (replies -> follow-ups -> approved sends -> approved replies).

## Try it in 2 minutes (no accounts needed)
```
pip install -r requirements.txt     # mock mode needs none of these
./demo_mock.sh
```
Mock mode uses fake profiles (`data/mock_profiles.json`), a fake inbox (`data/mock_inbox.json`) and rule-based stand-ins for Claude.
`--days-offset N` pretends N days have passed so follow-ups can be demonstrated; it is a demo flag only.

## Web dashboard

Run the simple Streamlit interface locally from this folder:

```
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. The dashboard uses
the same `influencer_crm.csv` and pipeline functions as the CLI. It starts in mock mode
unless `GMAIL_MODE=live` and the required credentials are configured. Review drafts
carefully before approving or sending anything.

To publish the dashboard, upload this project to a GitHub repository and deploy that
repository on Streamlit Community Cloud using `app.py` as the entry point. A public
deployment URL is created by Streamlit after deployment; it cannot be generated from
this local project without access to your GitHub and Streamlit accounts.

## Going live
1. `cp .env.example .env` and set `ANTHROPIC_API_KEY` (Claude is then used instead of the mock).
2. Google Cloud: enable Gmail API + Sheets/Drive API, create an OAuth *Desktop* client, save it as `credentials.json`. Add your own Gmail as a test user.
3. Set `GMAIL_MODE=live`, `STORE_BACKEND=sheets`, and your real `SENDER_*` details (including postal address).
4. Instagram: create a Meta app, link an Instagram Business/Creator account to a Facebook Page, generate a token with `instagram_basic` and `pages_show_list`, and set `IG_ACCESS_TOKEN` + `IG_USER_ID` (Business Discovery needs App Review for production; dev mode works for your test accounts).
5. Edit `data/brand.json` (brand, campaign, niches, follower range) and `data/seed_accounts.csv`.
6. Test with accounts you own first, e.g. a second Gmail address playing the influencer.

## Design decisions / limits (mention these in your demo)
- Instagram has no keyword-search API and scraping violates its terms, so discovery = curated seed list + official API enrichment.
- Business Discovery returns no location, so Claude infers it from the bio when possible.
- Bios and email replies are treated as untrusted data in prompts (prompt-injection guard).
- Compliance: sender identity, opt-out line, postal address, sending cap, human approval before first send and before any AI reply.
- Storage is read-all / write-all: fine for hundreds of leads; use a real DB or the Sheets API with row updates at scale.

## Files
`main.py` CLI - `discover.py` - `score.py` - `outreach.py` - `followups.py` - `replies.py` - `gmail_client.py` - `store.py` - `claude_client.py` - `config.py` -
`sample_influencer_crm.xlsx` - `sample_outputs/` (initial email, 2 follow-ups, AI reply; regenerate these from your own live run before submitting).
