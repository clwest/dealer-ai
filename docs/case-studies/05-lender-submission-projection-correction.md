# Lender Submission Projection Correction

Not every mid-implementation surprise is scope creep. Sometimes
the prior increment made a deliberate omission that turns out to
be load-bearing when the next increment tries to build on it.

## Context

M35.1 shipped the backend annotation for lender-submission
discovery: each credit application gained a computed
`latest_lender_submission_status` field via Subquery. The
projection was deliberately narrow: no full submission record was
returned, because M35.0 §5.h had made "no GET single-record
endpoint" an explicit non-goal for M35.

That decision was correct at planning time. The M35.1 UI only
needed the status chip; a full record fetch was out of scope.

## Diagnosis

M35.2 began the frontend work. The
`LenderSubmissionResponseForm` component needed to `PATCH` the
lender submission after the user recorded a response. To
`PATCH`, the frontend needs the submission's primary key. The
list endpoint returned the status but not the id. If the user
refreshed the page, the id was gone from any local cache and
there was no way to reconstruct it: no GET single-record endpoint
existed by design.

The gap was visible only when the response-form implementation
started. The M35.1 projection was internally consistent (no
consumer needed the id at the time), and the M35.0 non-goal was
still correct in spirit (avoid a full REST resource). But a
concrete FK-discoverability requirement had surfaced.

## Correction

M35.2 amended the projection with a second Subquery annotation
using the same `tenant_latest_submissions` subquery but with
`.values("pk")[:1]` instead of `.values("status")[:1]`. The new
field `latest_lender_submission_id` extends the projection without
adding a new endpoint. The `PATCH` remains against the pre-existing
lender-submission endpoint (which already existed at M35.1); only
the discovery surface widens.

This was documented as a §0.a scope amendment in the SESSION_218
handoff — not scope creep, and not a deferred non-goal violation.
The rule for distinguishing the two was invoked directly:

> FK discoverability requirements can surface during
> implementation and require small backend amendments — these
> are legitimate §0.a corrections, not scope creep.

## Verification

The M35.1 backend tests were extended to assert both `status` and
`id` in the projection (three test cases updated: cases 1 + 3 +
the projection-shape case). The M35.2 frontend tests exercise the
response-form submit path against the widened response. The
Playwright submission-response journey verifies the end-to-end
loop through the real UI.

## Lasting Effect

The discipline point here is honesty about what "scope creep"
means. If M35.2 had added a new GET single-record endpoint, that
would have been a non-goal violation and required opening the M35
scope. Instead it widened an existing annotation on an existing
endpoint by two lines. The mechanism was already there; the
projection just needed to expose the id the same way it already
exposed the status.

The lasting rule: **when a prior increment omits a field on the
assumption no consumer needs it, and the next increment discovers a
consumer that does, extending the projection is cheap and honest.
Adding a new endpoint on the same discovery is scope creep.**
