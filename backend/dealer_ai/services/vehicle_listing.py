"""Milestone 6 · Increment 3 (SESSION_084) — vehicle listing drafting service.

The one place all vehicle listing draft/approve/publish workflow
happens. Answers the M6 business questions in the listing subsystem:

- Q5: *"What listing copy has the AI drafted for this vehicle?"* —
  every :class:`VehicleListing` row.
- Q6: *"Has the operator approved and published the listing?"* —
  captured in ``VehicleListing.status`` + the actor / timestamp
  provenance pairs.
- Q7: *"When was the listing published?"* — ``published_at``
  (M8 aging seam).

Five public functions (mirrors M4.5 ``services/vendor_comm.py``
draft/approve/send shape):

- :func:`draft_listing` — AI-drafts a new listing from a structured
  source bundle assembled from Vehicle + latest completed condition
  report + M6.2 photo count. Runs the LLM output through the shared
  safety stack (:mod:`services.llm_safety`) with the M4.5
  ``_scrub_invented_recon_fact`` scrub (via the new
  ``"vehicle_listing"`` dispatch kind per §5.d Option A user-
  confirmed at SESSION_084). Persists a ``VehicleListing`` row at
  ``status='draft'``. Refuses if a listing already exists for the
  vehicle (any status) — use :func:`regenerate_draft` to replace an
  existing draft.
- :func:`approve_listing` — ``draft → approved`` transition.
- :func:`publish_listing` — ``approved → published`` transition.
  Drives the M6.4 ``_rule_listing_to_frontline`` predicate.
- :func:`unpublish_listing` — ``published → unpublished`` transition.
  Captures the operator's reason for withdrawal.
- :func:`regenerate_draft` — replaces the current draft body via a
  fresh LLM invocation. Refused when ``status != 'draft'``.

Layer discipline (per :doc:`AUTHENTICATION_MODEL.md` §1):

- **Data-scoping** — this module. Every public function accepts an
  explicit ``dealership`` kwarg and refuses to touch rows in any
  other tenant (:class:`CrossTenantListingError`).
- **Business semantics** — this module. Draft-approve-publish-
  unpublish ladder locked here.
- **AI safety** — this module + :mod:`services.llm_safety`. The
  M4.5 ``_scrub_invented_recon_fact`` scrub strips any finding ID /
  part number / dollar amount / ISO date the LLM invented that
  isn't in the source bundle. Per §5.d Option A user-confirmed at
  SESSION_084 open — reuse the existing M4.5 scrub, no new scrub
  needed. Extended via the ``_RECON_COMM_KINDS`` frozenset in
  :mod:`services.llm_safety` (dispatch extension, not new scrub
  logic).

Semantic decisions locked here:

- **draft_listing creates only.** If a listing exists for the
  vehicle (any status), :func:`draft_listing` raises
  :class:`ListingImmutableError`. Callers use
  :func:`regenerate_draft` to replace an existing draft or
  :func:`unpublish_listing` before re-drafting a published one.
- **No pricing in the drafted body.** The LLM prompt forbids
  mentioning specific dollar amounts. Price lives on ``Vehicle.price``
  and the M6.5 rendering layer injects it separately — listing
  body focuses on descriptive prose. Any $-amount the LLM emits
  gets scrubbed to "the quoted amount" (safety net).
- **No internal-detail leakage in the body.** The prompt forbids
  referencing internal findings, work orders, or recon-tier
  decisions. Listing copy is customer-facing marketing content,
  not operational disclosure.
- **Publish semantics (planning §5.e).** ``status='published''``
  means "visible to customers on the M6.5 ``/showroom`` endpoint."
  M6 v1 does NOT push to Facebook Marketplace / AutoTrader / etc.
  — that's Milestone 11+.

Concurrency posture:

- State transitions (:func:`approve_listing`, :func:`publish_listing`,
  :func:`unpublish_listing`, :func:`regenerate_draft`) use
  ``transaction.atomic()`` + ``select_for_update()`` on the target
  row so two concurrent transition calls cannot both succeed against
  the same row and produce contradictory provenance. Same shape as
  the M4.5 vendor-comm transitions.
"""

from __future__ import annotations

from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import (
    ConditionFinding,
    CONDITION_REPORT_STATUS_COMPLETE,
    ConditionReport,
    Dealership,
    VEHICLE_LISTING_STATUS_APPROVED,
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    VEHICLE_LISTING_STATUS_UNPUBLISHED,
    Vehicle,
    VehicleListing,
    VehiclePhoto,
)
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .llm_safety import apply_post_llm_scrubs


# ---- Domain errors --------------------------------------------------------


class CrossTenantListingError(ValueError):
    """Raised when a listing-service call references a Vehicle or
    :class:`VehicleListing` that belongs to a different dealership
    than the requesting tenant.

    Maps to HTTP 404 at the M6.5 endpoint layer (correct posture is
    "does not exist for this tenant" rather than "exists but you
    can't touch it"). Mirrors :class:`CrossTenantVendorCommError`
    from :mod:`services.vendor_comm`.
    """


class InvalidListingTransitionError(ValueError):
    """Raised when the caller attempts a structurally illegal status
    transition — e.g. approving a listing whose current status is
    ``published``, publishing a ``draft``, unpublishing an
    ``approved`` listing.

    Distinct from :class:`ListingImmutableError` per SESSION_084 §M6.3
    handoff — this one is "the transition itself is structurally
    invalid"; :class:`ListingImmutableError` is "an operation cannot
    run because the listing is in a state that forbids it (e.g. a
    listing already exists when :func:`draft_listing` was called)."
    Both map to HTTP 409, but the distinct classes let the M6.5
    endpoint surface an accurate remediation message.
    """


class ListingImmutableError(ValueError):
    """Raised when an operation is refused because the listing is in
    a state that forbids the operation — e.g. :func:`draft_listing`
    called when a listing already exists, :func:`regenerate_draft`
    called on a non-draft listing.

    Maps to HTTP 409. See :class:`InvalidListingTransitionError` for
    the distinction (structural transition illegality vs. operation
    forbidden by current state).
    """


class ListingScrubDroppedError(ValueError):
    """Raised by :func:`draft_listing` and :func:`regenerate_draft`
    when the shared safety stack signals a wholesale-rewrite class
    (``dropped_reason`` non-None) on the LLM's raw output.

    The draft is NOT persisted — the M6.5 endpoint should surface
    this to the operator as a retry prompt rather than logging a
    rejected draft that would corrupt the audit trail. Mirrors
    :class:`ReconFactScrubDroppedError` from
    :mod:`services.vendor_comm`.

    Maps to HTTP 422.
    """


class EmptyListingDraftError(ValueError):
    """Raised when the LLM returns empty output (or the safety stack
    scrubbs it to empty).

    Distinct from :class:`ListingScrubDroppedError` so callers can
    distinguish "LLM returned nothing" from "LLM output was unsafe."
    Mirrors :class:`EmptyDraftError` in :mod:`services.vendor_comm`.
    Not persisted; caller retries.
    """


# ---- Cross-tenant guards --------------------------------------------------


def _assert_vehicle_tenant(
    vehicle: Vehicle, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantListingError` when ``vehicle`` does
    not belong to the caller's tenant."""
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantListingError(
            f"Vehicle #{vehicle.pk} (stock {vehicle.stock_number!r}) "
            f"belongs to dealership_id={vehicle.dealership_id}, not "
            f"the requesting tenant #{dealership.pk} "
            f"({dealership.slug!r})."
        )


def _assert_listing_tenant(
    listing: VehicleListing, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantListingError` when ``listing`` does
    not belong to the caller's tenant."""
    if listing.dealership_id != dealership.pk:
        raise CrossTenantListingError(
            f"VehicleListing #{listing.pk} belongs to "
            f"dealership_id={listing.dealership_id}, not the "
            f"requesting tenant #{dealership.pk} "
            f"({dealership.slug!r})."
        )


# ---- Source bundle assembly -----------------------------------------------


def _build_source_bundle(vehicle: Vehicle) -> dict:
    """Assemble the structured source bundle the LLM prompt is
    rendered from and the M4.5 recon-fact scrub validates against.

    Shape (analogous to
    :func:`services.vendor_comm._build_source_bundle` but centered
    on Vehicle rather than WorkOrder):

    .. code-block:: python

        {
            "vehicle": {
                "stock", "year", "make", "model", "trim",
                "condition", "body_style", "mileage", "vin_last_6",
                "description",
            },
            "condition_report": {
                "inspector_name", "inspected_at",
                "mileage_at_inspection",
            } or None,
            "findings": [
                {"id", "category", "severity", "description"}, ...
            ],
            "photos": {
                "total_count": int,
                "listing_ready_count": int,
                "primary_public_id": str or None,
            },
            "authorized_cost": None,
            "parts_needed": [],
            "estimated_completion_date": None,
        }

    The last three keys are stubbed for scrub compatibility — the
    :func:`_scrub_invented_recon_fact` scrub reads them to build its
    valid-facts set. Empty / None values mean "no valid amounts /
    parts / dates present, so the LLM should NOT mention any."

    ``findings`` is populated from the latest completed
    :class:`ConditionReport` for the vehicle (if any). This gives
    the scrub finding IDs to validate against — the LLM prompt
    forbids referencing findings in listing copy, but if it does
    slip a reference through, the scrub strips invented IDs.
    """
    vin = getattr(vehicle, "vin", "") or ""

    latest_completed = (
        ConditionReport.objects.filter(
            vehicle=vehicle, status=CONDITION_REPORT_STATUS_COMPLETE
        )
        .order_by("-completed_at")
        .first()
    )
    if latest_completed is not None:
        report_bundle = {
            "inspector_name": latest_completed.inspector_name,
            "inspected_at": latest_completed.inspected_at.isoformat(),
            "mileage_at_inspection": latest_completed.mileage_at_inspection,
        }
        findings_bundle = [
            {
                "id": f.pk,
                "category": f.category,
                "severity": f.severity,
                "description": f.description,
            }
            for f in ConditionFinding.objects.filter(
                report=latest_completed
            ).order_by("pk")
        ]
    else:
        report_bundle = None
        findings_bundle = []

    total_photos = VehiclePhoto.objects.filter(
        vehicle=vehicle, marked_deleted_at__isnull=True
    ).count()
    # Local import to avoid the module-load cycle: gallery imports
    # photo_storage which imports models which pulls this module.
    from . import photo_gallery
    listing_ready = photo_gallery.listing_ready_count(
        vehicle, dealership=vehicle.dealership
    )
    primary = (
        VehiclePhoto.objects.filter(
            vehicle=vehicle,
            is_primary=True,
            marked_deleted_at__isnull=True,
        )
        .values_list("public_id", flat=True)
        .first()
    )

    return {
        "vehicle": {
            "stock": vehicle.stock_number,
            "year": vehicle.year,
            "make": getattr(vehicle, "make", "") or "",
            "model": vehicle.model,
            "trim": getattr(vehicle, "trim", "") or "",
            "condition": getattr(vehicle, "condition", "") or "",
            "body_style": getattr(vehicle, "body_style", "") or "",
            "mileage": getattr(vehicle, "mileage", None),
            "vin_last_6": vin[-6:] if vin else "",
            "description": getattr(vehicle, "description", "") or "",
        },
        "condition_report": report_bundle,
        "findings": findings_bundle,
        "photos": {
            "total_count": total_photos,
            "listing_ready_count": listing_ready,
            "primary_public_id": (
                str(primary) if primary is not None else None
            ),
        },
        # Scrub-compatibility stubs — the recon-fact scrub reads these
        # keys to build its valid-facts set. None / empty means "no
        # valid facts present; strip any LLM-referenced amounts /
        # parts / dates."
        "authorized_cost": None,
        "parts_needed": [],
        "estimated_completion_date": None,
    }


# ---- LLM prompt construction ---------------------------------------------


def _build_llm_messages(source_bundle: dict) -> list[dict]:
    """Render the source bundle into a structured LLM prompt for
    listing copy.

    The system message pins the boundaries: draft descriptive listing
    copy using ONLY facts from the bundle; do NOT mention internal
    findings / work orders / recon details; do NOT include pricing
    (M6.5 rendering injects price separately); no APR / rate /
    financing language; no promotion / discount claims.
    """
    vehicle = source_bundle["vehicle"]
    system_lines = [
        "You are drafting used-car listing copy for a dealership's "
        "public showroom page. Write in the dealership's voice — "
        "concise, professional, informative.",
        "",
        "STRICT rules:",
        "- Draft using ONLY facts present in the source data below.",
        "- Do NOT include pricing or specific dollar amounts — the "
        "operator adds pricing separately after approval.",
        "- Do NOT reference internal findings, work orders, or "
        "recon-tier decisions (those are operational data, not "
        "customer content).",
        "- Do NOT invent features, specs, or trim details not present "
        "in the source. If a fact is missing, omit it rather than "
        "guessing.",
        "- Do NOT quote APR / rate / financing language.",
        "- Do NOT mention discounts, promotions, or manufacturer programs.",
        "- Do NOT reference photos by URL or file name — the operator's "
        "showroom page renders photos separately.",
        "- Focus on the vehicle's descriptive attributes: year, make, "
        "model, trim, body style, condition, mileage, and any operator-"
        "authored description already present.",
        "- Keep the copy to a single body of text (2-4 short paragraphs). "
        "The operator will add title / headline / photos separately.",
    ]

    user_lines = [
        "Source data:",
        f"  Vehicle: stock #{vehicle['stock']}, "
        f"{vehicle['year']} {vehicle['make']} "
        f"{vehicle['model']}".strip(),
    ]
    if vehicle["trim"]:
        user_lines.append(f"  Trim: {vehicle['trim']}")
    if vehicle["body_style"]:
        user_lines.append(f"  Body style: {vehicle['body_style']}")
    if vehicle["condition"]:
        user_lines.append(f"  Condition: {vehicle['condition']}")
    if vehicle["mileage"] is not None:
        user_lines.append(f"  Mileage: {vehicle['mileage']:,}")
    if vehicle["description"]:
        user_lines.append(f"  Dealer description: {vehicle['description']}")

    photos = source_bundle["photos"]
    if photos["total_count"] > 0:
        user_lines.append(
            f"  Photos available: {photos['total_count']} "
            f"(operator will render separately — do NOT reference in copy)"
        )

    user_lines.append("")
    user_lines.append(
        "Draft the listing body as descriptive prose. Do not include a "
        "subject line, title, price, or photo captions — the operator "
        "adds those separately."
    )

    return [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


# ---- LLM invocation + scrub helper ---------------------------------------


def _draft_via_llm(
    source_bundle: dict, *, provider: Optional[LLMProvider]
) -> tuple[str, list[str], dict]:
    """Call the LLM, run the output through the safety stack, and
    return ``(cleaned_body, scrubs_fired, provenance)``.

    Raises :class:`ListingScrubDroppedError` on wholesale-rewrite
    signals (unsafe / negotiation / handoff phrasing) or
    :class:`EmptyListingDraftError` if the output is empty / scrubbed
    to empty.

    Shared by :func:`draft_listing` and :func:`regenerate_draft` so
    the LLM-invocation + scrub logic lives in exactly one place.
    """
    messages = _build_llm_messages(source_bundle)
    llm = provider or get_llm_provider()
    raw = llm.chat(messages, temperature=0.4, max_tokens=800)

    cleaned, scrubs_fired, dropped_reason = apply_post_llm_scrubs(
        raw, kind="vehicle_listing", recon_source_bundle=source_bundle
    )
    if dropped_reason is not None:
        raise ListingScrubDroppedError(
            f"draft_listing: LLM output rejected by safety stack "
            f"({dropped_reason}). Draft NOT persisted."
        )
    cleaned = (cleaned or "").strip()
    if not cleaned:
        raise EmptyListingDraftError(
            "draft_listing: LLM returned empty output (or the safety "
            "stack scrubbed it to empty). Draft NOT persisted."
        )

    provenance = {
        "source_bundle": source_bundle,
        "scrubs_fired": list(scrubs_fired),
        "llm_provider": getattr(llm, "name", "unknown"),
    }
    return cleaned, list(scrubs_fired), provenance


# ---- Public: draft_listing -----------------------------------------------


def draft_listing(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    drafted_by,
    provider: Optional[LLMProvider] = None,
) -> VehicleListing:
    """AI-draft an initial :class:`VehicleListing` for ``vehicle``.

    Three-step pattern mirroring
    :func:`services.vendor_comm.draft_communication`:

    1. Assemble the source bundle from Vehicle + latest completed
       condition report + M6.2 photo count.
    2. Call the LLM with a prompt that pins the boundaries (no
       pricing, no internal-detail leakage, no invented facts).
    3. Run the LLM output through
       :func:`services.llm_safety.apply_post_llm_scrubs` with
       ``kind='vehicle_listing'``. The M4.5
       ``_scrub_invented_recon_fact`` scrub (invoked via the
       extended ``_RECON_COMM_KINDS`` dispatch per §5.d Option A)
       strips any invented finding IDs / part numbers / dollar
       amounts / ISO dates that slipped past the prompt.

    Persists a :class:`VehicleListing` row at ``status='draft'`` with
    ``drafted_by`` + ``drafted_at`` set + ``source_provenance``
    populated.

    Preconditions:

    - Cross-tenant guard on ``vehicle.dealership``.
    - No existing :class:`VehicleListing` for the vehicle (any
      status) — refused with :class:`ListingImmutableError` if one
      exists. Callers use :func:`regenerate_draft` to replace an
      existing draft; :func:`unpublish_listing` + fresh
      :func:`draft_listing` to replace a published one.

    Raises:

    - :class:`CrossTenantListingError` — cross-tenant.
    - :class:`ListingImmutableError` — listing already exists.
    - :class:`ListingScrubDroppedError` — safety stack fired a
      wholesale rewrite. Draft NOT persisted.
    - :class:`EmptyListingDraftError` — LLM returned empty (or
      scrubbed to empty). Not persisted.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    if VehicleListing.objects.filter(vehicle=vehicle).exists():
        raise ListingImmutableError(
            f"draft_listing: a VehicleListing already exists for "
            f"vehicle #{vehicle.pk} (stock {vehicle.stock_number!r}). "
            "Use regenerate_draft to replace an existing draft, or "
            "unpublish_listing before re-drafting a published one."
        )

    source_bundle = _build_source_bundle(vehicle)
    body, _scrubs, provenance = _draft_via_llm(
        source_bundle, provider=provider
    )

    now = timezone.now()
    listing = VehicleListing(
        vehicle=vehicle,
        dealership=dealership,
        status=VEHICLE_LISTING_STATUS_DRAFT,
        title="",
        body=body,
        source_provenance=provenance,
        drafted_by=drafted_by,
        drafted_at=now,
    )
    listing.full_clean()
    try:
        listing.save()
    except IntegrityError as exc:
        # Race with a concurrent draft_listing call — the OneToOne
        # unique constraint fires. Translate to the same domain
        # error the pre-check would have raised.
        raise ListingImmutableError(
            f"draft_listing: a concurrent call created a VehicleListing "
            f"for vehicle #{vehicle.pk} first. Retry via regenerate_draft."
        ) from exc
    return listing


# ---- Public: regenerate_draft --------------------------------------------


def regenerate_draft(
    listing: VehicleListing,
    *,
    dealership: Dealership,
    drafted_by,
    provider: Optional[LLMProvider] = None,
) -> VehicleListing:
    """Replace the current draft body via a fresh LLM invocation.

    Refused when ``status != 'draft'`` — an approved / published /
    unpublished listing must be moved back through the transition
    chain (via a future ``revert_to_draft`` verb, deferred to M6.5+)
    before it can be redrafted.

    Overwrites ``body`` and ``source_provenance``; updates
    ``drafted_by`` + ``drafted_at``. Keeps ``title`` (operator-
    authored) unchanged.

    Wrapped in ``transaction.atomic()`` + ``select_for_update()`` so
    two concurrent regenerate calls cannot both succeed against the
    same row.

    Raises:

    - :class:`CrossTenantListingError`.
    - :class:`ListingImmutableError` if ``status != 'draft'``.
    - :class:`ListingScrubDroppedError` / :class:`EmptyListingDraftError`
      per :func:`_draft_via_llm`.
    """
    _assert_listing_tenant(listing, dealership)

    with transaction.atomic():
        refreshed = (
            VehicleListing.objects.select_for_update()
            .select_related("vehicle")
            .get(pk=listing.pk)
        )
        if refreshed.status != VEHICLE_LISTING_STATUS_DRAFT:
            raise ListingImmutableError(
                f"regenerate_draft: VehicleListing #{refreshed.pk} is "
                f"in status {refreshed.status!r}. Regeneration is "
                "allowed only from 'draft' — approve → publish → "
                "unpublish must be walked back before redrafting."
            )
        source_bundle = _build_source_bundle(refreshed.vehicle)
        body, _scrubs, provenance = _draft_via_llm(
            source_bundle, provider=provider
        )
        refreshed.body = body
        refreshed.source_provenance = provenance
        refreshed.drafted_by = drafted_by
        refreshed.drafted_at = timezone.now()
        refreshed.full_clean()
        refreshed.save(
            update_fields=[
                "body",
                "source_provenance",
                "drafted_by",
                "drafted_at",
                "updated_at",
            ]
        )
        return refreshed


# ---- Public: approve_listing ---------------------------------------------


def approve_listing(
    listing: VehicleListing,
    *,
    dealership: Dealership,
    approved_by,
) -> VehicleListing:
    """Transition a draft listing to approved.

    Preconditions:

    - Cross-tenant guard.
    - Current status must be ``draft`` (raises
      :class:`InvalidListingTransitionError` otherwise).

    Sets ``approved_by`` + ``approved_at``.
    """
    _assert_listing_tenant(listing, dealership)

    with transaction.atomic():
        refreshed = (
            VehicleListing.objects.select_for_update().get(pk=listing.pk)
        )
        if refreshed.status != VEHICLE_LISTING_STATUS_DRAFT:
            raise InvalidListingTransitionError(
                f"approve_listing: VehicleListing #{refreshed.pk} is "
                f"in status {refreshed.status!r}. Approval is allowed "
                "only from 'draft'."
            )
        refreshed.status = VEHICLE_LISTING_STATUS_APPROVED
        refreshed.approved_by = approved_by
        refreshed.approved_at = timezone.now()
        refreshed.full_clean()
        refreshed.save()
        return refreshed


# ---- Public: publish_listing ---------------------------------------------


def publish_listing(
    listing: VehicleListing,
    *,
    dealership: Dealership,
    published_by,
) -> VehicleListing:
    """Transition an approved listing to published.

    Publish semantics per planning §5.e: ``status='published'`` means
    "visible to customers on the M6.5 ``/showroom`` endpoint." M6 v1
    does NOT push to Facebook Marketplace / AutoTrader / etc.

    Preconditions:

    - Cross-tenant guard.
    - Current status must be ``approved`` (raises
      :class:`InvalidListingTransitionError` otherwise).

    Sets ``published_by`` + ``published_at``. Drives the M6.4
    ``_rule_listing_to_frontline`` predicate.
    """
    _assert_listing_tenant(listing, dealership)

    with transaction.atomic():
        refreshed = (
            VehicleListing.objects.select_for_update().get(pk=listing.pk)
        )
        if refreshed.status != VEHICLE_LISTING_STATUS_APPROVED:
            raise InvalidListingTransitionError(
                f"publish_listing: VehicleListing #{refreshed.pk} is "
                f"in status {refreshed.status!r}. Publish is allowed "
                "only from 'approved'."
            )
        refreshed.status = VEHICLE_LISTING_STATUS_PUBLISHED
        refreshed.published_by = published_by
        refreshed.published_at = timezone.now()
        refreshed.full_clean()
        refreshed.save()
        return refreshed


# ---- Public: unpublish_listing -------------------------------------------


def unpublish_listing(
    listing: VehicleListing,
    *,
    dealership: Dealership,
    unpublished_by,
    reason: str,
) -> VehicleListing:
    """Transition a published listing to unpublished.

    Preconditions:

    - Cross-tenant guard.
    - Current status must be ``published`` (raises
      :class:`InvalidListingTransitionError` otherwise).
    - ``reason`` must be nonblank (raises :class:`ValueError`) —
      operator must explain why the listing was withdrawn (for
      audit + downstream analytics). Truncated at 255 characters
      (the ``unpublished_reason`` CharField's max_length).

    Sets ``unpublished_by`` + ``unpublished_at`` + ``unpublished_reason``.
    """
    _assert_listing_tenant(listing, dealership)

    if not (reason or "").strip():
        raise ValueError(
            "unpublish_listing: reason is required and must be nonblank. "
            "Operator must explain why the listing was withdrawn."
        )

    with transaction.atomic():
        refreshed = (
            VehicleListing.objects.select_for_update().get(pk=listing.pk)
        )
        if refreshed.status != VEHICLE_LISTING_STATUS_PUBLISHED:
            raise InvalidListingTransitionError(
                f"unpublish_listing: VehicleListing #{refreshed.pk} is "
                f"in status {refreshed.status!r}. Unpublish is allowed "
                "only from 'published'."
            )
        refreshed.status = VEHICLE_LISTING_STATUS_UNPUBLISHED
        refreshed.unpublished_by = unpublished_by
        refreshed.unpublished_at = timezone.now()
        # Truncate at 255 chars — CharField enforces this via
        # full_clean, but truncating here gives a clean domain-level
        # experience rather than a Django ValidationError with a
        # field-length message.
        refreshed.unpublished_reason = reason.strip()[:255]
        refreshed.full_clean()
        refreshed.save()
        return refreshed


# ---- Public re-exports ---------------------------------------------------


__all__ = [
    "CrossTenantListingError",
    "EmptyListingDraftError",
    "InvalidListingTransitionError",
    "ListingImmutableError",
    "ListingScrubDroppedError",
    "approve_listing",
    "draft_listing",
    "publish_listing",
    "regenerate_draft",
    "unpublish_listing",
]
