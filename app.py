"""Streamlit dashboard for the influencer outreach pipeline."""
import streamlit as st

import config
import store


st.set_page_config(
    page_title="Influencer Outreach",
    page_icon="✨",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] {
        background: #f7f8fc;
        border: 1px solid #e8eaf2;
        border-radius: 12px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"] p {
        color: #4b5563 !important;
    }
    [data-testid="stMetricValue"] {
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_db():
    return store.get_store()


def load_rows():
    return get_db().read()


def save_rows(rows):
    get_db().write(rows)
    st.cache_data.clear()


def run_pipeline(label, function, rows):
    with st.spinner(label):
        updated = function(rows)
        save_rows(updated)
    st.success(label + " complete.")
    st.rerun()


st.title("✨ Influencer Outreach")
st.caption("Research, score, draft, review, and manage creator outreach from one place.")

rows = load_rows()
counts = {}
for row in rows:
    counts[row.get("status", "Unknown")] = counts.get(row.get("status", "Unknown"), 0) + 1

metric_columns = st.columns(5)
for column, (label, value) in zip(
    metric_columns,
    [
        ("Total leads", len(rows)),
        ("Email available", counts.get(store.EMAIL_AVAILABLE, 0)),
        ("Emails sent", counts.get(store.EMAIL_SENT, 0)),
        ("Replies", counts.get(store.REPLIED, 0) + counts.get(store.INTERESTED, 0)),
        ("Opted out", counts.get(store.OPTED_OUT, 0)),
    ],
):
    column.metric(label, value)

st.divider()
left, right = st.columns([1, 2])

with left:
    st.subheader("Pipeline actions")
    st.caption(
        "Current mode: "
        + ("Live Gmail / Instagram" if config.GMAIL_MODE == "live" else "Mock / offline")
    )
    if config.GMAIL_MODE == "live":
        st.warning("Live mode is enabled. Review every draft before sending.")

    if st.button("1. Discover leads", use_container_width=True):
        import discover
        run_pipeline("Discovery", discover.run, rows)
    if st.button("2. Score leads", use_container_width=True):
        import score
        run_pipeline("Scoring", score.run, rows)
    if st.button("3. Draft emails", use_container_width=True):
        import outreach
        run_pipeline("Email drafting", outreach.draft_emails, rows)
    if st.button("Check replies", use_container_width=True):
        import replies
        run_pipeline("Reply processing", replies.process, rows)
    if st.button("Run follow-ups", use_container_width=True):
        import followups
        run_pipeline("Follow-up processing", followups.run, rows)

    st.divider()
    st.subheader("Send approved messages")
    st.caption("Only messages explicitly approved below can be sent.")
    if st.button("Send approved emails", type="primary", use_container_width=True):
        import outreach
        run_pipeline("Sending approved emails", outreach.send_approved, rows)
    if st.button("Send approved replies", use_container_width=True):
        import replies
        run_pipeline("Sending approved replies", replies.send_approved, rows)

with right:
    st.subheader("Lead review")
    statuses = ["All"] + sorted({r.get("status", "Unknown") for r in rows})
    selected_status = st.selectbox("Filter by status", statuses)
    search = st.text_input("Search username, name, or email")
    filtered = [
        r for r in rows
        if (selected_status == "All" or r.get("status") == selected_status)
        and search.lower() in (
            r.get("username", "") + " " + r.get("name", "") + " " + r.get("email", "")
        ).lower()
    ]

    if not filtered:
        st.info("No leads match this filter. Start with “Discover leads”.")
    else:
        for row in filtered:
            title = f"{row.get('name') or row.get('username')} · {row.get('status', 'Unknown')}"
            with st.expander(title):
                detail_left, detail_right = st.columns(2)
                detail_left.write(f"**Username:** @{row.get('username', '')}")
                detail_left.write(f"**Email:** {row.get('email') or 'Not available'}")
                detail_left.write(f"**Niche:** {row.get('niche') or 'Not scored'}")
                detail_left.write(f"**Followers:** {row.get('followers') or '—'}")
                detail_right.write(f"**Score:** {row.get('score') or 'Not scored'}")
                detail_right.write(f"**Location:** {row.get('location') or '—'}")
                detail_right.write(f"**Reason:** {row.get('reason') or '—'}")

                if row.get("draft_subject"):
                    st.markdown("**Email draft**")
                    st.text_area(
                        "Subject",
                        row["draft_subject"],
                        key=f"subject-{row['username']}",
                        disabled=True,
                    )
                    st.text_area(
                        "Body",
                        row.get("draft_body", ""),
                        key=f"body-{row['username']}",
                        height=180,
                        disabled=True,
                    )
                    if row.get("approved", "").upper() == "YES":
                        st.success("Email approved")
                    elif row.get("status") == store.EMAIL_AVAILABLE:
                        if st.button("Approve email", key=f"approve-email-{row['username']}"):
                            row["approved"] = "YES"
                            save_rows(rows)
                            st.rerun()

                if row.get("last_reply_snippet"):
                    st.markdown("**Latest reply**")
                    st.info(row["last_reply_snippet"])
                    st.write(f"**Category:** {row.get('reply_category') or '—'}")
                    st.write(f"**Suggested action:** {row.get('suggested_action') or '—'}")
                    if row.get("draft_reply"):
                        st.text_area(
                            "Reply draft",
                            row["draft_reply"],
                            key=f"reply-{row['username']}",
                            height=140,
                            disabled=True,
                        )
                        if row.get("reply_approved", "").upper() == "YES":
                            st.success("Reply approved")
                        elif row.get("status") != store.OPTED_OUT:
                            if st.button("Approve reply", key=f"approve-reply-{row['username']}"):
                                row["reply_approved"] = "YES"
                                save_rows(rows)
                                st.rerun()

st.divider()
st.caption("Data is stored in influencer_crm.csv. In mock mode, no real messages are sent.")
