"""Live smoke for the customer chat — exercises the post-Drift-1.a /
2.a behavior with the local llama3.2:latest provider against the
real seed inventory.

Run via:
    cd backend && source .venv/bin/activate
    python smoke_drift_audit.py

Reports per scenario:
  - matched_vehicles count + display names
  - whether assistant prose repeats card data (specs/Stock #/extra
    payments)
  - whether payment-drift was detected and scrubbed
  - metadata.flag
  - follow-up question text (so a human can judge naturalness)
"""

from __future__ import annotations

import os
import re
import sys

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "dealer_kit.settings"
)
django.setup()

from dealer_ai.models import ChatMessage, ChatSession, Vehicle  # noqa: E402
from dealer_ai.services.chat_engine import ChatEngine  # noqa: E402

# Match $X/mo, $X/month, $X per month, $X a month, $X monthly.
PAYMENT_RE = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?"
    r"(?:/\s*mo(?:nth)?|\s+(?:per|a)\s+month|\s+monthly)",
    re.IGNORECASE,
)
STOCK_RE = re.compile(r"\bFF[-\w]+\b|\bStock\s*#?\s*\S+", re.IGNORECASE)
PRICE_RE = re.compile(r"\$\s*\d{2,3},\d{3}\b")
MILEAGE_RE = re.compile(
    r"\b\d{1,3}(?:,\d{3})?\s*(?:mi|miles)\b", re.IGNORECASE
)
QUESTION_RE = re.compile(r"[^.!?]*\?")


def report(label, *, session, profile=None, history_user_msgs=None):
    """Run a single user turn against a fresh session, print a report."""
    sess = ChatSession.objects.create(
        extracted_profile=profile or {},
    )
    if history_user_msgs:
        # Seed prior turns so the engine has the right context.
        # Each entry is (user_text, expected_lead_vehicle_or_None).
        for prior_text in history_user_msgs:
            engine = ChatEngine(session=sess)
            engine.handle_user_message(prior_text)
        sess.refresh_from_db()

    engine = ChatEngine(session=sess)
    result = engine.handle_user_message(session)

    msg = result.assistant_message
    matched = list(result.matched_vehicles)
    content = msg.content
    meta = msg.metadata or {}
    bq = meta.get("budget_query") or {}

    # Allowed payments (matched + closest_above) — used to compute
    # whether prose contains a payment number that ISN'T the lead's.
    allowed = []
    for v in matched:
        p = getattr(v, "_estimated_payment", None)
        if p is not None:
            allowed.append(float(p))

    payment_quotes = [
        float(m.replace("$", "").replace(",", "").split("/")[0]
                .split(" ")[0])
        for m in PAYMENT_RE.findall(content)
    ]
    stocks_in_prose = STOCK_RE.findall(content)
    prices_in_prose = PRICE_RE.findall(content)
    mileage_in_prose = MILEAGE_RE.findall(content)
    questions = [q.strip() for q in QUESTION_RE.findall(content) if q.strip()]

    print(f"\n{'=' * 68}\n{label}\n{'=' * 68}")
    print(f"USER: {session}")
    if history_user_msgs:
        print(f"PRIOR TURNS (seeded): {history_user_msgs}")
    print(f"\nASSISTANT REPLY:\n{content}\n")
    print(f"matched_vehicles ({len(matched)}):")
    for v in matched:
        p = getattr(v, "_estimated_payment", None)
        fit = getattr(v, "_budget_fit", None)
        flex = getattr(v, "_lever_flex_kind", None)
        flex_note = f" lever={flex}" if flex else ""
        print(
            f"  - {v.display_name} | Stock {v.stock_number} | "
            f"est ${p:.0f}/mo | fit={fit}{flex_note}"
            if p is not None else
            f"  - {v.display_name} | Stock {v.stock_number} | "
            f"fit={fit}{flex_note}"
        )

    # Card-repeat heuristic: prose mentions specs the cards already
    # render. Payments other than the lead vehicle's count as repeats;
    # any Stock # in prose, any extra price quote, any mileage, count
    # as repeats.
    repeats = []
    if len(payment_quotes) > 1:
        repeats.append(
            f"multiple payment quotes in prose ({payment_quotes})"
        )
    if stocks_in_prose:
        repeats.append(f"Stock # cited in prose ({stocks_in_prose})")
    if prices_in_prose:
        repeats.append(f"raw price quoted ({prices_in_prose})")
    if mileage_in_prose:
        repeats.append(f"mileage quoted ({mileage_in_prose})")
    print(f"\nrepeats card data? {'YES — ' + '; '.join(repeats) if repeats else 'no'}")

    # Drift detection / scrub status.
    drift = bq.get("payment_drift")
    flag = meta.get("flag")
    scrubs = meta.get("scrubs", [])
    print(f"payment_drift (audit): {drift}")
    print(f"payment_drift_scrubbed in prose? "
          f"{'yes' if 'payment_drift' in scrubs else 'no'}")
    print(f"metadata.flag: {flag}")
    print(f"metadata.scrubs: {scrubs}")

    # Follow-up question(s).
    print(f"\nfollow-up question(s) found ({len(questions)}):")
    for q in questions:
        print(f"  · {q}")
    print(f"lever_offer set? {meta.get('lever_offer', False)}")

    return sess, msg


def main():
    print("LIVE SMOKE — Drift 1.a + 2.a behavior audit")
    print(f"Provider: ollama / model: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
    print(f"Seed inventory: {Vehicle.objects.count()} vehicles")

    # Scenario 1 — 4WD truck, $500/mo, $3k down (cold start)
    report(
        "1. 4WD truck, $500/mo, $3k down",
        session="I'm looking for a 4WD truck around $500/mo with $3,000 down",
    )

    # Scenario 2 — trucks, $500/mo, $0 down (cold start, no drivetrain)
    report(
        "2. trucks, $500/mo, $0 down",
        session="show me trucks for $500/mo, $0 down",
    )

    # Scenario 3 — "tell me more about the Ranger" follow-up. Needs a
    # prior turn that put the Ranger on a card. Seed with scenario 1.
    report(
        "3. tell me more about the Ranger (follow-up after 4WD truck $500/$3k)",
        session="tell me more about the Ranger",
        history_user_msgs=[
            "I'm looking for a 4WD truck around $500/mo with $3,000 down",
        ],
    )

    # Scenario 4 — "yes try 84 months" lever-accept after a turn that
    # set lever_offer=True. Easiest setup: scenario 1's near-fit
    # (Ranger is the canonical near-fit). If that turn doesn't set
    # lever_offer it'll fall through to the normal pipeline; we report
    # whichever path fired.
    report(
        "4. yes try 84 months (lever-accept)",
        session="yes try 84 months",
        history_user_msgs=[
            "I'm looking for a 4WD truck around $500/mo with $3,000 down",
        ],
    )

    # Scenario 5 — "any drivetrain" release after $500/$3k 4WD context.
    # merge_profile should overwrite drivetrain="4WD" with "any" and
    # rerun the pipeline against the wider pool.
    report(
        "5. any drivetrain (release)",
        session="any drivetrain",
        history_user_msgs=[
            "I'm looking for a 4WD truck around $500/mo with $3,000 down",
        ],
    )


if __name__ == "__main__":
    main()
