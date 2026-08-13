# Dealer AI — What It Is

## In one paragraph

Dealer AI is a dealership operating system for independent used-car
dealers. It models the workflows a small-to-mid dealership actually
runs — inventory acquisition and reconditioning, lead capture and
follow-up, sales-to-F&I handoff and deal structuring, lender
submission and response tracking, BHPH (buy-here-pay-here) payment
collection and delinquency, and double-entry accounting with a
trial-balance substrate — and puts an LLM-powered chat surface on
top of that engine. The chat runs deterministic math (standard-APR
amortization and BHPH weekly/biweekly cadence) and enforces
compliance rules that are gated on dealer type (an independent
dealer cannot legally advertise "Ford Credit approved" or "0% APR";
the code strips that language before it reaches a customer). The
shipped demo persona is a fictional independent lot (Copper Canyon
Auto, Yuma, AZ) with 45 mixed-make used vehicles.

## Who it's for

- **Primary:** independent used-car dealership operators
  (owner / GM / sales manager) at 1–3 rooftop lots, especially
  those serving credit-challenged or BHPH-heavy segments
  (~$3k–$25k price band, mixed-make used inventory).
- **Secondary:** franchise dealers who want a compliant AI sales
  layer their OEM does not provide, via env-override configuration
  (`DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<make>`).

## What it is not

- Not an AI-first platform. The LLM is a natural-language interface
  over rule-based dealership logic. The value lives in the guardrails,
  the payment math, the compliance scrubs, and the operational data
  model — not the model.
- Not deployed to real dealerships. The shipped persona is a
  fictional lot; the pilot playbook exists but no live customer has
  operated on this software.
- Not integrated with real DMS, credit bureaus, lender APIs, or
  payment processors. Those are documented gaps, not stubs pretending
  to work.

## Stack

- **Backend:** Django 5, Django REST Framework, Celery + Redis,
  PostgreSQL (SQLite fallback for dev), Django Channels not used.
- **Frontend:** React 18 + Vite + TypeScript strict, shadcn/ui on
  Tailwind 3 with dealer-agnostic `brand.*` tokens,
  react-router 6.
- **LLM:** switchable provider — Ollama (default, free, local) or
  OpenAI. Chat degrades gracefully to a clear "trouble reaching AI"
  message if the provider is unreachable; the rest of the app keeps
  working.
- **Tests:** 5,045 Django tests, 431 Vitest tests, 20 Playwright
  journey specs across six operator personas.
