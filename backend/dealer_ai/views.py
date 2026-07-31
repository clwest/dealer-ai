from pathlib import Path
from typing import Optional
from uuid import uuid4

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import (
    ChatMessage,
    ChatSession,
    CustomerLead,
    DealerOnboardingProfile,
    Salesperson,
    Vehicle,
)
from .serializers import (
    AdminChatSessionListSerializer,
    AdminLeadListSerializer,
    AssignLeadSerializer,
    ChatMessageInputSerializer,
    ChatMessageSerializer,
    ChatSessionSerializer,
    CustomerLeadSerializer,
    DealerOnboardingProfileSerializer,
    ManagerChatInputSerializer,
    ONBOARDING_DEFAULTS,
    SalespersonAdminSerializer,
    SalespersonPublicSerializer,
    StartChatSerializer,
    VehicleAskSerializer,
    VehicleSerializer,
)
from datetime import timedelta

from django.utils import timezone

from .services.ad_copy import generate_ad_copy
from .services.audit import audit_events_snapshot
from .services.chat_engine import ChatEngine
from .permissions import (
    IsAdvisorForSlug,
    IsDealerOwnerAtActiveDealership,
    IsDealerOwnerForAdvisorSlug,
    IsSalesManagerOrOwnerAtActiveDealership,
    ReadOnly,
)
from .services.follow_up import (
    SUPPORTED_CHANNELS as FOLLOW_UP_CHANNELS,
    SUPPORTED_TONES as FOLLOW_UP_TONES,
    generate_follow_up_drafts,
)
from .services.handoff_service import build_handoff_packet, packet_to_text
from .services.lead_service import create_lead_from_session
from .services.manager_chat_response import enforce_coaching_shape
from .services.pipeline import pipeline_snapshot
from .services.tenancy import get_current_dealership, get_default_dealership
from .services.trends import trends_snapshot
from .services.vehicle_assistant import analyze_vehicle, answer_vehicle_question


DEMO_SOURCE = "demo_seed"


DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200
MAX_LOGO_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _parse_limit(request, default: int = DEFAULT_LIST_LIMIT) -> int:
    raw = request.query_params.get("limit")
    if not raw:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, MAX_LIST_LIMIT))


@api_view(["POST"])
def start_chat(request):
    serializer = StartChatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session = ChatSession.objects.create(
        dealership=get_default_dealership(),
        customer_name=data.get("customer_name", ""),
        customer_email=data.get("customer_email", ""),
        customer_phone=data.get("customer_phone", ""),
    )

    initial_message = (data.get("initial_message") or "").strip()
    response_payload = {
        "session": ChatSessionSerializer(session).data,
        "assistant_message": None,
        "matched_vehicles": [],
    }

    if initial_message:
        engine = ChatEngine(session=session)
        result = engine.handle_user_message(initial_message)
        response_payload["assistant_message"] = ChatMessageSerializer(
            result.assistant_message
        ).data
        response_payload["matched_vehicles"] = VehicleSerializer(
            result.matched_vehicles, many=True
        ).data

    return Response(response_payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def send_message(request):
    serializer = ChatMessageInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        session = ChatSession.objects.get(id=data["session_id"])
    except ChatSession.DoesNotExist:
        return Response(
            {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
        )

    engine = ChatEngine(session=session)
    result = engine.handle_user_message(data["message"])

    return Response(
        {
            "assistant_message": ChatMessageSerializer(result.assistant_message).data,
            "matched_vehicles": VehicleSerializer(
                result.matched_vehicles, many=True
            ).data,
        }
    )


@api_view(["POST"])
def create_lead(request):
    # Validate and normalize the inbound payload (does not persist).
    serializer = CustomerLeadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = dict(serializer.validated_data)

    session_obj = payload.pop("session", None)
    # PrimaryKeyRelatedField returns the model instance for `session`; coerce
    # interested_vehicles back to id list for the service.
    interested = payload.pop("interested_vehicles", []) or []
    payload["interested_vehicles"] = [
        v.id if hasattr(v, "id") else v for v in interested
    ]

    lead = create_lead_from_session(
        session=session_obj,
        payload=payload,
    )

    return Response(
        CustomerLeadSerializer(lead).data, status=status.HTTP_201_CREATED
    )


# ---- Admin / read endpoints ------------------------------------------------


@api_view(["GET"])
def session_detail(request, session_id):
    try:
        session = ChatSession.objects.prefetch_related("messages").get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response(
            {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
        )
    return Response(ChatSessionSerializer(session).data)


_LEAD_SINCE_WINDOWS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

_LEAD_VALID_URGENCIES = {"immediate", "this_week", "this_month", "researching"}

# Severity ranking for ordering=urgency. Higher number = more urgent;
# unset urgency falls to 0. Tie-break on -created_at handled in caller.
_URGENCY_RANK = {
    "immediate": 4,
    "this_week": 3,
    "this_month": 2,
    "researching": 1,
}


def _apply_lead_filters(qs, request):
    """Manager Phase 1: optional filters for the handoff queue.

    Query params (all optional, garbage values silently ignored):

    - ``handed_off``: ``true`` / ``false``
    - ``urgency``: comma-separated subset of immediate / this_week /
      this_month / researching
    - ``since``: ``24h`` / ``7d`` / ``30d``
    - ``ordering``: ``urgency`` / ``created_at`` (default)
    """
    raw_handed = request.query_params.get("handed_off")
    if raw_handed is not None:
        normalized = raw_handed.strip().lower()
        if normalized in ("true", "1", "yes"):
            qs = qs.filter(handed_off=True)
        elif normalized in ("false", "0", "no"):
            qs = qs.filter(handed_off=False)

    raw_urgency = request.query_params.get("urgency")
    if raw_urgency:
        wanted = {
            tok.strip().lower()
            for tok in raw_urgency.split(",")
            if tok.strip()
        }
        wanted = wanted & _LEAD_VALID_URGENCIES
        if wanted:
            qs = qs.filter(urgency__in=list(wanted))

    raw_since = request.query_params.get("since")
    if raw_since in _LEAD_SINCE_WINDOWS:
        cutoff = timezone.now() - _LEAD_SINCE_WINDOWS[raw_since]
        qs = qs.filter(created_at__gte=cutoff)

    return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_list(request):
    dealership = get_current_dealership(request)
    limit = _parse_limit(request)
    base_qs = (
        CustomerLead.objects.filter(dealership=dealership)
        .select_related("session")
        .prefetch_related("interested_vehicles")
    )
    filtered_qs = _apply_lead_filters(base_qs, request)

    ordering = request.query_params.get("ordering", "created_at").strip().lower()
    if ordering == "urgency":
        # Pull the filtered set then sort in Python: severity rank
        # desc, then -created_at. Demo scale; portable across DB
        # backends without case expressions.
        rows = list(filtered_qs)
        rows.sort(
            key=lambda lead: (
                -_URGENCY_RANK.get(lead.urgency, 0),
                -lead.created_at.timestamp(),
            )
        )
        results = rows[:limit]
        total_filtered = len(rows)
    else:
        results = list(filtered_qs.order_by("-created_at")[:limit])
        total_filtered = filtered_qs.count()

    return Response(
        {
            "count": total_filtered,
            "limit": limit,
            "results": AdminLeadListSerializer(results, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_chat_session_list(request):
    dealership = get_current_dealership(request)
    limit = _parse_limit(request)
    scoped = ChatSession.objects.filter(dealership=dealership)
    qs = scoped.order_by("-updated_at")[:limit]
    return Response(
        {
            "count": scoped.count(),
            "limit": limit,
            "results": AdminChatSessionListSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_trends(request):
    return Response(trends_snapshot(dealership=get_current_dealership(request)))


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_pipeline(request):
    """Manager Phase 2: sales pipeline + demand-vs-supply + recommended actions.

    Pure read aggregate over CustomerLead and Vehicle. No schema changes,
    no chat-engine touches. Milestone 1 · Increment 4D — tenant-scoped
    via ``dealership=`` passed into :func:`pipeline_snapshot`.
    """
    return Response(pipeline_snapshot(dealership=get_current_dealership(request)))


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_ad_copy(request):
    """Manager Phase 3: generate 2–3 ad-copy variants for an inventory or
    marketing recommendation. Read-only with respect to system state — no
    persistence, no auto-publish. Variants pass through the same post-LLM
    safety scrub stack the chat path uses.

    Request body::

        {
          "recommendation": {
            "id": "...",          # required
            "category": "...",    # required, must be inventory|marketing
            "title": "...",
            "explanation": "...",
            "action_text": "...",
            "evidence": {...},
            "cta": {...}          # optional, used to derive band edges
          },
          "vehicle_id": 123        # optional
        }
    """
    body = request.data or {}
    recommendation = body.get("recommendation")
    raw_vehicle_id = body.get("vehicle_id")
    vehicle_id: Optional[int]
    if raw_vehicle_id in (None, ""):
        vehicle_id = None
    else:
        try:
            vehicle_id = int(raw_vehicle_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "vehicle_id must be an integer when provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        result = generate_ad_copy(
            recommendation=recommendation,
            vehicle_id=vehicle_id,
            dealership=get_current_dealership(request),
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    payload = {
        "recommendation_id": result.recommendation_id,
        "variants": result.variants,
        "warnings": result.warnings,
        "vehicles_used": VehicleSerializer(
            result.vehicles_used, many=True
        ).data,
    }
    return Response(payload)


# ---- Manager Phase 4: Salespeople + assignment + advisor workspace --------


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_salespeople(request):
    """List all salespeople (active and inactive). Used by the manager
    dashboard and the assignment dropdown. Phase 4 keeps inactive rows
    visible so historical assignments still resolve, but the frontend
    filters them out of the assignment menu via the ``is_active`` flag.

    Milestone 1 · Increment 4D — tenant-scoped. Admin at Dealership A
    only sees Dealership A's salespeople.
    """
    dealership = get_current_dealership(request)
    qs = Salesperson.objects.filter(dealership=dealership).order_by(
        "-is_active", "name"
    )
    only_active = request.query_params.get("active")
    if only_active in ("true", "1", "yes"):
        qs = qs.filter(is_active=True)
    return Response(
        {
            "count": qs.count(),
            "results": SalespersonAdminSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
def public_salespeople(request):
    """Public-facing 'Meet the team' list. Active salespeople only;
    contact details (phone/email/bio) are intentionally omitted."""
    qs = Salesperson.objects.filter(is_active=True).order_by("name")
    return Response(
        {
            "count": qs.count(),
            "results": SalespersonPublicSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
def public_salesperson_detail(request, slug):
    """Public-facing single-salesperson detail (active only)."""
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Salesperson not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(SalespersonPublicSerializer(sp).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_assign(request, lead_id):
    """Assign a lead to a salesperson, or clear assignment when
    ``salesperson_id`` is null.

    Per the locked Phase 4 decisions: cannot assign to an inactive
    salesperson. Already-assigned leads are silently re-assigned.

    Milestone 1 · Increment 4D — both the lead and the target
    salesperson must belong to the caller's active dealership. An admin
    at Dealership A cannot reassign a Dealership B lead, and cannot
    assign any lead to a Dealership B salesperson.
    """
    dealership = get_current_dealership(request)
    try:
        lead = CustomerLead.objects.get(pk=lead_id, dealership=dealership)
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = AssignLeadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    salesperson_id = serializer.validated_data.get("salesperson_id")

    if salesperson_id is None:
        lead.assigned_to = None
        lead.assigned_at = None
    else:
        try:
            sp = Salesperson.objects.get(pk=salesperson_id, dealership=dealership)
        except Salesperson.DoesNotExist:
            return Response(
                {"detail": "Salesperson not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not sp.is_active:
            return Response(
                {"detail": "Cannot assign to an inactive salesperson."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lead.assigned_to = sp
        lead.assigned_at = timezone.now()
    lead.save(update_fields=["assigned_to", "assigned_at", "updated_at"])

    return Response(AdminLeadListSerializer(lead).data)


_WORKSPACE_RECENT_DAYS = 30


@api_view(["GET"])
@permission_classes(
    [IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]
)
def advisor_workspace(request, slug):
    """Salesperson workspace: profile + open leads + contacted leads.

    Open = assigned + handed_off=false.
    Contacted = assigned + handed_off=true within the last 30 days.

    Milestone 1 · Increment 4C — access is real DRF authorization now.
    Authenticated advisor for this slug OR authenticated dealer_owner
    at the same dealership can view. Everyone else gets 401 (unauth)
    or 403 (auth but not authorized). URL shape and response body
    preserved; the slug-obscurity mechanism (previously documented
    here as v1) is replaced. Post-permission 404 still fires when a
    legitimately-authorized caller hits a slug whose Salesperson is
    inactive — that's the same data-lifecycle check as before.
    """
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Advisor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    base = (
        CustomerLead.objects.filter(assigned_to=sp)
        .select_related("session", "assigned_to")
        .prefetch_related("interested_vehicles")
    )
    open_qs = base.filter(handed_off=False).order_by(
        "-assigned_at", "-created_at"
    )
    cutoff = timezone.now() - timedelta(days=_WORKSPACE_RECENT_DAYS)
    contacted_qs = base.filter(
        handed_off=True, updated_at__gte=cutoff
    ).order_by("-updated_at")

    return Response(
        {
            "salesperson": SalespersonPublicSerializer(sp).data,
            "open_leads": AdminLeadListSerializer(
                list(open_qs), many=True
            ).data,
            "contacted_leads": AdminLeadListSerializer(
                list(contacted_qs), many=True
            ).data,
            "counts": {
                "open": open_qs.count(),
                "contacted": contacted_qs.count(),
            },
        }
    )


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]
)
def advisor_follow_up(request, slug, lead_id):
    """Generate AI follow-up drafts for an assigned lead.

    Body::

        {
          "channel": "sms" | "email",     # default sms
          "tone":    "warm" | "direct"    # default warm
        }

    Milestone 1 · Increment 4C — authorization is DRF-based (see
    :func:`advisor_workspace`). The 403 lead-ownership check below
    (``lead.assigned_to_id != sp.pk``) is preserved verbatim — it is
    the data-scoping layer's manifestation on this endpoint and
    remains distinct from the authorization layer. A dealer_owner
    accessing an advisor's URL still fails the lead-ownership check
    for leads not assigned to that advisor, which is the correct
    behavior: owners can *see* an advisor's queue via the workspace
    endpoint, but drafting on behalf of an advisor is scoped to that
    advisor's own leads.
    """
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Advisor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        lead = CustomerLead.objects.prefetch_related(
            "interested_vehicles"
        ).get(pk=lead_id)
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )
    if lead.assigned_to_id != sp.pk:
        return Response(
            {"detail": "Lead is not assigned to this advisor."},
            status=status.HTTP_403_FORBIDDEN,
        )

    body = request.data or {}
    channel = (body.get("channel") or "sms").strip().lower()
    tone = (body.get("tone") or "warm").strip().lower()
    if channel not in FOLLOW_UP_CHANNELS:
        return Response(
            {"detail": f"channel must be one of {sorted(FOLLOW_UP_CHANNELS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if tone not in FOLLOW_UP_TONES:
        return Response(
            {"detail": f"tone must be one of {sorted(FOLLOW_UP_TONES)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = generate_follow_up_drafts(
        lead=lead,
        advisor=sp,
        channel=channel,
        tone=tone,
    )
    return Response(
        {
            "lead_id": result.lead_id,
            "salesperson_slug": result.salesperson_slug,
            "channel": channel,
            "tone": tone,
            "drafts": result.drafts,
            "warnings": result.warnings,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_audit_events(request):
    since = request.query_params.get("since", "24h")
    raw_limit = request.query_params.get("limit")
    try:
        recent_limit = max(1, min(int(raw_limit), 200)) if raw_limit else 50
    except (TypeError, ValueError):
        recent_limit = 50
    return Response(
        audit_events_snapshot(
            since=since,
            recent_limit=recent_limit,
            dealership=get_current_dealership(request),
        )
    )


# ---- Vehicle detail / vehicle ask ------------------------------------------


def _profile_from_request(request) -> dict:
    """Pull customer financial signals from query params or body for the
    vehicle detail/ask endpoints. Falls back to attached session profile."""
    profile: dict = {}
    src = request.query_params if request.method == "GET" else request.data
    target = src.get("target_monthly_payment")
    down = src.get("down_payment")
    if target not in (None, ""):
        profile["target_monthly_payment"] = target
    if down not in (None, ""):
        profile["down_payment"] = down
    return profile


@api_view(["GET"])
def vehicle_detail(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response(
            {"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND
        )

    profile = _profile_from_request(request)
    session_id = request.query_params.get("session_id")
    if session_id and not profile:
        try:
            session = ChatSession.objects.get(id=session_id)
            profile = dict(session.extracted_profile or {})
        except ChatSession.DoesNotExist:
            pass

    analysis = analyze_vehicle(vehicle, profile=profile)
    return Response(
        {
            "vehicle": VehicleSerializer(vehicle).data,
            "payment_estimates": analysis.payment_estimates,
            "affordability_notes": analysis.affordability_notes,
            "similar_vehicles": VehicleSerializer(
                analysis.similar_vehicles, many=True
            ).data,
        }
    )


@api_view(["POST"])
def vehicle_ask(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response(
            {"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = VehicleAskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session = None
    if data.get("session_id"):
        try:
            session = ChatSession.objects.get(id=data["session_id"])
        except ChatSession.DoesNotExist:
            session = None

    profile = {}
    if session is not None:
        profile = dict(session.extracted_profile or {})
    if data.get("target_monthly_payment") is not None:
        profile["target_monthly_payment"] = data["target_monthly_payment"]
    if data.get("down_payment") is not None:
        profile["down_payment"] = data["down_payment"]

    answer = answer_vehicle_question(
        vehicle=vehicle,
        question=data["question"],
        profile=profile,
        session=session,
    )

    analysis = analyze_vehicle(vehicle, profile=profile)
    return Response(
        {
            "vehicle": VehicleSerializer(vehicle).data,
            "answer": answer,
            "payment_estimates": analysis.payment_estimates,
            "affordability_notes": analysis.affordability_notes,
            "similar_vehicles": VehicleSerializer(
                analysis.similar_vehicles, many=True
            ).data,
        }
    )


# ---- Lead detail / handoff -------------------------------------------------


def _serialize_lead_messages(lead: CustomerLead) -> list:
    if lead.session_id is None:
        return []
    qs = ChatMessage.objects.filter(session_id=lead.session_id).order_by("created_at")
    return ChatMessageSerializer(qs, many=True).data


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_detail(request, lead_id):
    dealership = get_current_dealership(request)
    try:
        lead = (
            CustomerLead.objects.filter(dealership=dealership)
            .select_related("session")
            .prefetch_related("interested_vehicles")
            .get(id=lead_id)
        )
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {
            "lead": CustomerLeadSerializer(lead).data,
            "interested_vehicles": VehicleSerializer(
                lead.interested_vehicles.all(), many=True
            ).data,
            "session_profile": (
                lead.session.extracted_profile if lead.session else {}
            ),
            "messages": _serialize_lead_messages(lead),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_handoff(request, lead_id):
    dealership = get_current_dealership(request)
    try:
        lead = (
            CustomerLead.objects.filter(dealership=dealership)
            .prefetch_related("interested_vehicles")
            .get(id=lead_id)
        )
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    packet = build_handoff_packet(lead)

    if request.data.get("mark_handed_off"):
        if not lead.handed_off:
            lead.handed_off = True
            lead.save(update_fields=["handed_off", "updated_at"])

    return Response({**packet, "text": packet_to_text(packet), "handed_off": lead.handed_off})


# ---- Demo reset ------------------------------------------------------------


@api_view(["POST"])
def demo_reset(request):
    """Wipe demo conversational state so a fresh demo can run.

    Default behavior:
        - Delete all chat sessions, chat messages, and customer leads.
        - Reload the bundled demo vehicles.
        - LEAVE imported (non-demo) vehicles alone.

    Explicit opt-ins (request body, JSON):
        - reload_demo_vehicles (bool, default true)
        - delete_imported_vehicles (bool, default false) — drops vehicles whose
          source != 'demo_seed'. Use with care.
    """
    body = request.data or {}
    reload_demo_vehicles = bool(body.get("reload_demo_vehicles", True))
    delete_imported_vehicles = bool(body.get("delete_imported_vehicles", False))

    counts = {
        "chat_messages": ChatMessage.objects.count(),
        "chat_sessions": ChatSession.objects.count(),
        "leads": CustomerLead.objects.count(),
    }
    CustomerLead.objects.all().delete()
    ChatMessage.objects.all().delete()
    ChatSession.objects.all().delete()

    deleted_imported = 0
    if delete_imported_vehicles:
        deleted_imported = (
            Vehicle.objects.exclude(source=DEMO_SOURCE).count()
        )
        Vehicle.objects.exclude(source=DEMO_SOURCE).delete()

    reloaded_count = 0
    if reload_demo_vehicles:
        from io import StringIO

        call_command("seed_demo_vehicles", stdout=StringIO())
        reloaded_count = Vehicle.objects.filter(source=DEMO_SOURCE).count()

    return Response(
        {
            "ok": True,
            "cleared": counts,
            "deleted_imported_vehicles": deleted_imported,
            "demo_vehicles": reloaded_count,
            "imported_vehicles_remaining": (
                Vehicle.objects.exclude(source=DEMO_SOURCE).count()
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def demo_load_scenarios(request):
    """Seed (or re-seed) the bundled demo scenarios. Wraps
    `python manage.py seed_demo_scenarios`."""
    from io import StringIO

    body = request.data or {}
    reset = bool(body.get("reset", False))

    out = StringIO()
    args = ["seed_demo_scenarios"]
    if reset:
        args.append("--reset")
    call_command(*args, stdout=out)

    return Response(
        {
            "ok": True,
            "reset": reset,
            "chat_sessions": ChatSession.objects.count(),
            "leads": CustomerLead.objects.count(),
            "stdout": out.getvalue(),
        },
        status=status.HTTP_200_OK,
    )


# ---- Manager chat tester (SESSION_010) -------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def manager_chat(request):
    """SESSION_010: stateless manager-side chat tester.

    Lets a manager preview how the configured sales assistant responds —
    voice, banned-phrase scrubbing, disclaimer behavior — without
    polluting a real customer session. Each request runs in a fresh
    ephemeral ``ChatSession`` tagged ``channel=manager_test``; the
    existing chat engine handles everything (including SESSION_009
    onboarding overrides), so behavior matches what real customers see.

    Returns ``{"reply": <assistant text>}``. No vehicle cards — the
    tester is voice-and-tone focused, and including matched_vehicles
    here would couple the manager UI to inventory shape changes.
    """
    serializer = ManagerChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    message = (data.get("message") or "").strip()
    if not message:
        return Response(
            {"detail": "message is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = ChatSession.objects.create(
        dealership=get_current_dealership(request),
        metadata={"channel": "manager_test"},
    )
    engine = ChatEngine(session=session)
    result = engine.handle_user_message(message)

    # SESSION_010 hotfix + SESSION_011 structural enforcement.
    # The chat engine already received MANAGER_COACHING_HINT via the
    # manager_test channel and applied SESSION_009 onboarding overrides
    # (banned-phrase scrub + tone overrides + disclaimer). This call
    # adds a final structural pass: it strips known-bad sentences via
    # the existing card-implying scrub AND, if the surviving text
    # impersonates the customer-facing assistant or lacks a coaching
    # frame entirely, replaces it with a context-aware coaching
    # fallback built from the customer's message. Customer-facing chat
    # is unaffected — the enforcer lives in this view only.
    reply_text, _action = enforce_coaching_shape(
        result.assistant_message.content,
        customer_message=message,
    )

    return Response(
        {"reply": reply_text},
        status=status.HTTP_200_OK,
    )


# ---- Onboarding (SESSION_008) ----------------------------------------------


@api_view(["GET", "PUT", "PATCH"])
@permission_classes(
    [ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]
)
def onboarding_profile(request):
    """Singleton dealer onboarding profile.

    GET: returns the current profile, or the default shape if none exists
        yet. Always 200 — the page can render with defaults pre-filled.
        Public (branding must render on unauthenticated pages per
        MILESTONE_1_PLANNING.md §3 compatibility checklist).
    PUT/PATCH: upserts the singleton row. PUT requires the full payload
        (validates every field). PATCH allows partial updates and only
        validates the keys present in the body.

    Milestone 1 · Increment 4D — mutation requires ``dealer_owner`` at
    the caller's active dealership. GET stays public because
    ``useBrand()`` renders on public pages that never authenticate.
    """
    dealership = get_current_dealership(request)
    profile = (
        DealerOnboardingProfile.objects.filter(dealership=dealership).first()
    )

    if request.method == "GET":
        if profile is None:
            return Response(ONBOARDING_DEFAULTS)
        return Response(DealerOnboardingProfileSerializer(profile).data)

    partial = request.method == "PATCH"
    if profile is None:
        # Seed creation with defaults so PATCH (partial) lands cleanly even
        # when only some fields are supplied. PUT will validate every key
        # the serializer requires (none are required by default since all
        # CharField/TextField are blank=True and BooleanField has default).
        serializer = DealerOnboardingProfileSerializer(
            data={**ONBOARDING_DEFAULTS, **request.data}
        )
    else:
        serializer = DealerOnboardingProfileSerializer(
            profile, data=request.data, partial=partial
        )
    serializer.is_valid(raise_exception=True)
    profile = serializer.save(dealership=dealership)
    return Response(
        DealerOnboardingProfileSerializer(profile).data, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated & IsDealerOwnerAtActiveDealership])
def onboarding_logo_upload(request):
    """Upload a dealer logo and store its served URL in ``logo_url``.

    This keeps ``logo_url`` as the single source of truth for every brand
    surface. Hosted URL paste still uses the JSON profile endpoint.

    Milestone 1 · Increment 4D — requires ``dealer_owner`` at the
    caller's active dealership.
    """
    upload = request.FILES.get("logo")
    if upload is None:
        return Response(
            {"detail": "Upload a file field named 'logo'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_LOGO_CONTENT_TYPES.get(content_type)
    if extension is None:
        return Response(
            {
                "detail": (
                    "Unsupported logo type. Use JPG, PNG, WEBP, or SVG."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if upload.size > MAX_LOGO_UPLOAD_BYTES:
        return Response(
            {"detail": "Logo file must be 2 MB or smaller."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    original_suffix = Path(upload.name).suffix.lower()
    if original_suffix in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
        extension = ".jpg" if original_suffix == ".jpeg" else original_suffix
    path = default_storage.save(
        f"dealer-logos/{uuid4().hex}{extension}",
        upload,
    )
    logo_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{path}")

    dealership = get_current_dealership(request)
    profile = (
        DealerOnboardingProfile.objects.filter(dealership=dealership).first()
    )
    if profile is None:
        serializer = DealerOnboardingProfileSerializer(
            data={**ONBOARDING_DEFAULTS, "logo_url": logo_url}
        )
    else:
        serializer = DealerOnboardingProfileSerializer(
            profile, data={"logo_url": logo_url}, partial=True
        )
    serializer.is_valid(raise_exception=True)
    profile = serializer.save(dealership=dealership)
    return Response(
        DealerOnboardingProfileSerializer(profile).data, status=status.HTTP_200_OK
    )


# ---- Milestone 1 · Increment 4E — browser auth flow -----------------------
#
# Three endpoints implementing the minimal browser-side session flow:
#
#   POST /api/dealer-ai/auth/login/   — authenticate + open Django session
#   POST /api/dealer-ai/auth/logout/  — close the Django session (idempotent)
#   GET  /api/dealer-ai/auth/me/      — current session probe + CSRF primer
#
# Design constraints (see docs/roadmap/AUTHENTICATION_MODEL.md §2):
#
# 1. Session cookies (Django session middleware) drive the browser flow.
#    TokenAuthentication remains configured for non-browser clients but
#    the browser never stores a DRF token in localStorage.
# 2. Login errors return a generic message — never confirm username
#    existence.
# 3. Logout is safe to call when already anonymous — the frontend
#    invokes it on ambiguous state without needing to check first.
# 4. `/me/` uses `@ensure_csrf_cookie` so the very first bootstrap
#    call sets the `csrftoken` cookie the frontend needs for the
#    subsequent login POST.
# 5. `/me/` returns identity + active-dealership + roles minimally.
#    It resolves both via the existing `services.tenancy` primitives —
#    no parallel identity resolver.


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login(request):
    """Authenticate a user + open a Django session.

    Body: ``{"username": "...", "password": "..."}``. Returns 200 with
    the same shape as :func:`auth_me` when successful, 400 for a
    missing field, 401 with a generic message otherwise.
    """
    body = request.data or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return Response(
            {"detail": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Generic message — never distinguish "no such user" from
        # "wrong password". This is a login-CSRF and enumeration
        # defense at once.
        return Response(
            {"detail": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    django_login(request, user)
    return Response(_me_payload(request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_logout(request):
    """End the active Django session.

    Idempotent: returns 200 whether or not a session existed. The
    frontend can call this on ambiguous state (e.g. session expired
    server-side) without a pre-flight check.
    """
    django_logout(request)
    return Response({"detail": "Signed out."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_me(request):
    """Return the current session state.

    Also primes the ``csrftoken`` cookie via ``@ensure_csrf_cookie`` —
    the frontend calls this once on boot so subsequent unsafe requests
    (login, logout, admin mutations) have the token to include in
    the ``X-CSRFToken`` header.

    Response shape is intentionally minimal (username +
    active dealership + roles) — enough for the frontend to route,
    not enough to become a general user-profile endpoint.
    """
    return Response(_me_payload(request), status=status.HTTP_200_OK)


def _me_payload(request) -> dict:
    """Compose the ``/auth/me/`` response body.

    Delegates to :func:`services.tenancy.get_current_dealership` for
    the active dealership and to the membership model for roles.
    Never invents parallel resolvers; downstream code changes here
    only when those primitives change.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return {"authenticated": False}

    dealership = get_current_dealership(request)
    # Pull every role the user holds at the active dealership. Multiple
    # concurrent roles at one dealership are supported per the 4A
    # design note.
    from .models import UserDealershipRole  # local import to avoid cycles

    roles = sorted(
        UserDealershipRole.objects.filter(
            user=user, dealership=dealership
        ).values_list("role", flat=True)
    )

    salesperson = getattr(user, "salesperson", None)
    return {
        "authenticated": True,
        "user": {
            "id": user.pk,
            "username": user.get_username(),
            "display_name": (user.get_full_name() or user.get_username()),
            "salesperson_slug": salesperson.slug if salesperson else None,
        },
        "dealership": {
            "id": dealership.pk,
            "slug": dealership.slug,
            "name": dealership.name,
        },
        "roles": roles,
    }
