from rest_framework import serializers

from .models import (
    ACQUISITION_SOURCE_CHOICES,
    CONDITION_CATEGORY_CHOICES,
    CONDITION_PHOTO_CONTENT_TYPE_CHOICES,
    CONDITION_SEVERITY_CHOICES,
    VEHICLE_COST_CATEGORY_CHOICES,
    ChatMessage,
    ChatSession,
    CustomerLead,
    DealerOnboardingProfile,
    Salesperson,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from .services.chat_engine import customer_drivetrain_label
from .services.vehicle_ledger import category_group_of


# ---- Salesperson serializers (Manager Phase 4) -----------------------------


class SalespersonPublicSerializer(serializers.ModelSerializer):
    """Public-facing payload for the "Meet the team" page. Omits phone/email
    and bio so the marketing surface doesn't leak contact info to anonymous
    browsers. The admin payload (below) includes everything."""

    class Meta:
        model = Salesperson
        fields = [
            "id",
            "name",
            "slug",
            "title",
            "photo_url",
            "specialties",
            "is_active",
        ]


class SalespersonAdminSerializer(serializers.ModelSerializer):
    """Admin-side payload — includes phone, email, and bio. Used by the
    LeadDetailModal assignment dropdown and the manager team page."""

    class Meta:
        model = Salesperson
        fields = [
            "id",
            "name",
            "slug",
            "title",
            "email",
            "phone",
            "photo_url",
            "bio",
            "specialties",
            "is_active",
            "created_at",
            "updated_at",
        ]


class SalespersonAssignmentSerializer(serializers.ModelSerializer):
    """Compact representation embedded in admin lead lists / pipeline payloads."""

    class Meta:
        model = Salesperson
        fields = ["id", "name", "slug", "title", "photo_url"]


class AssignLeadSerializer(serializers.Serializer):
    """Request body for POST /admin/lead/<id>/assign/."""

    salesperson_id = serializers.IntegerField(allow_null=True, required=False)


class VehicleSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    # Item 4 — customer-facing drivetrain label. Internal seed values
    # are 4x4 / AWD / RWD / FWD; the customer sees 4WD / AWD / 2WD /
    # FWD. Override here so the frontend chip + the post-LLM scrub
    # share the same vocabulary.
    drivetrain = serializers.SerializerMethodField()
    # Transient budget annotations populated by chat_engine.build_budget_context
    # via instance attributes (`_budget_fit`, `_estimated_payment`,
    # `_payment_delta`). Vehicles fetched outside a budget context simply
    # serialize these as null — no model field is required.
    budget_fit = serializers.SerializerMethodField()
    estimated_payment = serializers.SerializerMethodField()
    payment_delta = serializers.SerializerMethodField()
    # Phase 8s/UX (lever-flex) — when a vehicle is surfaced as a
    # presentation flex option (longer term / more down / drivetrain
    # release), the chat-card needs the lever name + the human caption
    # to render its second badge and explainer line. Cards that aren't
    # flex picks serialize these as null.
    lever_flex_kind = serializers.SerializerMethodField()
    lever_flex_explainer = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "stock_number",
            "vin",
            "year",
            "make",
            "model",
            "trim",
            "body_style",
            "condition",
            "mileage",
            "price",
            "msrp",
            "exterior_color",
            "interior_color",
            "drivetrain",
            "transmission",
            "fuel_type",
            "engine",
            "features",
            "description",
            "image_url",
            "url",
            "source",
            "last_seen_at",
            "imported_at",
            "display_name",
            "budget_fit",
            "estimated_payment",
            "payment_delta",
            "lever_flex_kind",
            "lever_flex_explainer",
        ]

    def get_drivetrain(self, obj):
        return customer_drivetrain_label(obj.drivetrain)

    def get_budget_fit(self, obj):
        return getattr(obj, "_budget_fit", None)

    def get_estimated_payment(self, obj):
        return getattr(obj, "_estimated_payment", None)

    def get_payment_delta(self, obj):
        return getattr(obj, "_payment_delta", None)

    def get_lever_flex_kind(self, obj):
        return getattr(obj, "_lever_flex_kind", None)

    def get_lever_flex_explainer(self, obj):
        return getattr(obj, "_lever_flex_explainer", None)


class ChatMessageSerializer(serializers.ModelSerializer):
    matched_vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "matched_vehicles", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "customer_name",
            "customer_email",
            "customer_phone",
            "metadata",
            "extracted_profile",
            "lead_created",
            "messages",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "extracted_profile",
            "lead_created",
            "messages",
            "created_at",
        ]


class StartChatSerializer(serializers.Serializer):
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    initial_message = serializers.CharField(required=False, allow_blank=True)


class ChatMessageInputSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    message = serializers.CharField()


class ManagerChatInputSerializer(serializers.Serializer):
    """SESSION_010: stateless manager-test endpoint input.

    The manager chat is a sandbox for testing how the configured assistant
    responds to customer prompts. No session_id — each request runs in a
    fresh ephemeral ``ChatSession`` tagged with ``channel=manager_test`` so
    audits / dashboards can filter the test traffic out of real customer
    metrics.
    """

    message = serializers.CharField()


class VehicleAskSerializer(serializers.Serializer):
    question = serializers.CharField()
    session_id = serializers.UUIDField(required=False, allow_null=True)
    target_monthly_payment = serializers.FloatField(required=False, allow_null=True)
    down_payment = serializers.FloatField(required=False, allow_null=True)


class CustomerLeadSerializer(serializers.ModelSerializer):
    interested_vehicles = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Vehicle.objects.all(),
        required=False,
    )
    # Milestone 25 · Increment 1 (SESSION_186) — attribution surface for
    # LeadDetailModal per MILESTONE_25_PLANNING.md §5.b + §5.c. Additive
    # only; matches the M11.6 AdminLeadListSerializer precedent (which
    # already exposes ``channel`` + ``referrer``). ``referrer_name`` is
    # derived so the modal renders "Referred by: {name}" without a
    # second fetch. ``source_metadata`` is exposed as-is; the modal
    # reads platform via ``source_metadata.platform`` on the client
    # side (server-side accessor lives on the model).
    referrer_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerLead
        fields = [
            "id",
            "session",
            "name",
            "phone",
            "email",
            "target_monthly_payment",
            "down_payment",
            "trade_in",
            "urgency",
            "credit_range",
            "interested_vehicles",
            "conversation_summary",
            "recommended_next_action",
            "notes",
            "handed_off",
            "created_at",
            # M25.1 attribution fields.
            "channel",
            "referrer",
            "referrer_name",
            "source_metadata",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "handed_off",
            "conversation_summary",
            "recommended_next_action",
            "channel",
            "referrer",
            "referrer_name",
            "source_metadata",
        ]

    def get_referrer_name(self, obj: CustomerLead) -> str:
        return obj.referrer.name if obj.referrer_id else ""


# ---- Admin / dashboard serializers -----------------------------------------


class VehicleSummarySerializer(serializers.ModelSerializer):
    """Compact vehicle representation for admin tables."""

    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "stock_number",
            "year",
            "make",
            "model",
            "trim",
            "condition",
            "price",
            "display_name",
        ]


class AdminLeadListSerializer(serializers.ModelSerializer):
    """Compact lead row for the manager dashboard list."""

    interested_vehicles = VehicleSummarySerializer(many=True, read_only=True)
    session_id = serializers.PrimaryKeyRelatedField(source="session", read_only=True)
    assigned_to = SalespersonAssignmentSerializer(read_only=True)

    class Meta:
        model = CustomerLead
        fields = [
            "id",
            "session_id",
            "name",
            "phone",
            "email",
            "target_monthly_payment",
            "down_payment",
            "trade_in",
            "urgency",
            "credit_range",
            "interested_vehicles",
            "conversation_summary",
            "recommended_next_action",
            "handed_off",
            "assigned_to",
            "assigned_at",
            "created_at",
            # Milestone 11 · Increment 6 (SESSION_119) — expose the M11.1
            # channel field so the sales operator UI can render the
            # channel column + filter by it. Additive-only serializer
            # change; existing consumers ignore unknown fields.
            "channel",
            "referrer",
        ]


class AdminChatSessionListSerializer(serializers.ModelSerializer):
    """Compact session row — last user/assistant message snippet + message count."""

    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "customer_name",
            "customer_email",
            "customer_phone",
            "extracted_profile",
            "lead_created",
            "message_count",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, obj: ChatSession) -> int:
        return obj.messages.count()

    def get_last_message(self, obj: ChatSession):
        msg = (
            obj.messages.exclude(role="system").order_by("-created_at").first()
        )
        if not msg:
            return None
        snippet = msg.content[:160]
        return {
            "role": msg.role,
            "content": snippet + ("…" if len(msg.content) > 160 else ""),
            "created_at": msg.created_at.isoformat(),
        }


# ---- Onboarding (SESSION_008) ----------------------------------------------


# Default values returned by GET when no profile row exists. Mirror the
# defaults the v0 frontend page used to seed its local state so the UI
# behaves identically before the first save.
ONBOARDING_DEFAULTS: dict = {
    "dealership_name": "",
    "store_location": "",
    "main_brands": "",
    "sales_phone": "",
    "website": "",
    "logo_url": "",
    "sales_tone": "",
    "pricing_comfort": "",
    "appointment_preference": "",
    "lead_handoff_style": "",
    "salesperson_name": "",
    "salesperson_role": "",
    "salesperson_phone": "",
    "salesperson_email": "",
    "salesperson_specialties": "",
    "salesperson_preferred_tone": "",
    "salesperson_intro": "",
    "dealership_greeting": "",
    "approved_phrases": "",
    "banned_phrases": "",
    "escalation_rule": "",
    "payment_disclaimer": (
        "Payments shown are estimates. Final terms with approved credit (W.A.C.)."
    ),
    "inventory_connected": False,
    "finance_rules_reviewed": False,
    "salespeople_added": False,
    "demo_prompts_tested": False,
    "pilot_approved": False,
    # Indie shape-of-business (SESSION_032). Blank / False defaults
    # here mean "unset — resolver falls back to env or Copper Canyon
    # default"; see docstring on the model.
    "dealer_type": "",
    "bhph_enabled": True,
    "bhph_configured": False,
    "subprime_lenders": "",
    "floor_plan_lender": "",
    "warranty_offering": "",
    "credit_range_served": "",
    "makes_carried": "",
}


class DealerOnboardingProfileSerializer(serializers.ModelSerializer):
    """Flat snake_case payload mirroring all 35 onboarding fields (27 pre-SESSION_032 + 8 indie shape-of-business)."""

    class Meta:
        model = DealerOnboardingProfile
        fields = [
            "dealership_name",
            "store_location",
            "main_brands",
            "sales_phone",
            "website",
            "logo_url",
            "sales_tone",
            "pricing_comfort",
            "appointment_preference",
            "lead_handoff_style",
            "salesperson_name",
            "salesperson_role",
            "salesperson_phone",
            "salesperson_email",
            "salesperson_specialties",
            "salesperson_preferred_tone",
            "salesperson_intro",
            "dealership_greeting",
            "approved_phrases",
            "banned_phrases",
            "escalation_rule",
            "payment_disclaimer",
            "inventory_connected",
            "finance_rules_reviewed",
            "salespeople_added",
            "demo_prompts_tested",
            "pilot_approved",
            "dealer_type",
            "bhph_enabled",
            "bhph_configured",
            "subprime_lenders",
            "floor_plan_lender",
            "warranty_offering",
            "credit_range_served",
            "makes_carried",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# ---- Vehicle investment ledger serializers (Milestone 2 · Increment 6) ----
#
# Three admin endpoints under
# ``/api/dealer-ai/admin/vehicles/<stock_number>/`` expose the ledger built
# in M2.1-M2.5:
#
# - GET ``.../ledger/``       — full ledger read (uses the three OUTPUT
#                                serializers below + a totals dict).
# - POST ``.../acquisition/`` — upsert (uses ``AcquisitionUpsertRequestSerializer``
#                                for input, ``VehicleAcquisitionOutputSerializer``
#                                for output).
# - POST ``.../costs/``       — post one immutable cost row (uses
#                                ``CostCreateRequestSerializer`` for input,
#                                ``VehicleCostOutputSerializer`` for output).
#
# Decimal handling: DRF ``DecimalField`` never parses through binary float
# (uses ``Decimal(str(value))`` internally) — safe for cent-accurate
# accounting inputs. Outputs are strings on the wire so JavaScript's
# ``Number`` type can't silently truncate precision.


class VehicleLedgerHeaderSerializer(serializers.ModelSerializer):
    """Small vehicle-identity block for the ledger page header.

    Deliberately minimal — the ledger page doesn't need the full
    ``VehicleSerializer`` payload (drivetrain labels, budget-fit
    annotations, presentation-flex metadata all live there for chat
    surfaces). Header just needs enough to render "2024 Ford Ranger
    XLT #F25-014" with the current asking price alongside it.
    """

    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "stock_number",
            "vin",
            "year",
            "make",
            "model",
            "trim",
            "price",
            "display_name",
        ]


class VehicleAcquisitionOutputSerializer(serializers.ModelSerializer):
    """Output projection for a single :class:`VehicleAcquisition`.

    Includes ``source_display`` so the UI can render the friendly
    label without maintaining its own choice map. ``dealership`` is
    intentionally omitted — the caller resolved the tenant to reach
    this endpoint; echoing the dealership back would be noise.
    """

    source_display = serializers.CharField(
        source="get_source_display", read_only=True
    )

    class Meta:
        model = VehicleAcquisition
        fields = [
            "source",
            "source_display",
            "source_detail",
            "purchase_price",
            "purchase_date",
            "buyer_fees",
            "arbitration_fees",
            "transportation_cost",
            "title_acquisition_cost",
            "notes",
            "created_at",
            "updated_at",
        ]


class VehicleCostOutputSerializer(serializers.ModelSerializer):
    """Output projection for a single :class:`VehicleCost`.

    Includes:

    - ``category_display`` — friendly label from the model's
      ``choices=`` (e.g. ``"Floor plan interest"`` for
      ``"floor_plan_interest"``).
    - ``category_group`` — one of ``"flooring"`` / ``"recon"`` /
      ``"administrative"`` / ``"photography"`` (via
      :func:`services.vehicle_ledger.category_group_of`). Keeps the
      partition source-of-truth in the service layer; the UI can
      render group headers without repeating the partition logic.
    - ``created_by`` — the username of the poster, or ``None`` for
      seed / management-command writes. Full user object is
      unnecessary for the ledger view and would leak email etc.
    """

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    category_group = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = VehicleCost
        fields = [
            "id",
            "category",
            "category_display",
            "category_group",
            "amount",
            "incurred_at",
            "vendor",
            "reference",
            "notes",
            "is_estimate",
            "created_by",
            "created_at",
        ]

    def get_category_group(self, obj):
        return category_group_of(obj.category)

    def get_created_by(self, obj):
        if obj.created_by_id is None:
            return None
        return obj.created_by.username


class AcquisitionUpsertRequestSerializer(serializers.Serializer):
    """Request body for POST ``/admin/vehicles/<stock>/acquisition/``.

    Every field validated with the same rules the model + service
    enforce. Fee fields default to ``Decimal("0")`` — trades and
    private-party acquisitions typically have no auction / broker /
    arbitration / transportation charges.

    ``purchase_price`` is required and non-negative
    (``min_value=Decimal("0")``); the service layer's
    ``VehicleAcquisition.clean()`` cross-tenant guard runs on save
    but signed-money invariants live here in the request layer
    where field-level errors surface to the caller cleanly.
    """

    source = serializers.ChoiceField(choices=ACQUISITION_SOURCE_CHOICES)
    source_detail = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=255
    )
    purchase_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0
    )
    purchase_date = serializers.DateField()
    buyer_fees = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0
    )
    arbitration_fees = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0
    )
    transportation_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0
    )
    title_acquisition_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CostCreateRequestSerializer(serializers.Serializer):
    """Request body for POST ``/admin/vehicles/<stock>/costs/``.

    ``amount`` is a signed :class:`Decimal` — negative values are
    permitted because reversing entries are the ledger's correction
    pattern (mirrors accounting §2.11). No update/delete endpoints
    exist in v1; corrections happen by posting a new row with the
    negative amount and a reference pointing at the original.

    ``created_by`` is NOT accepted from the request body — the view
    sets it to ``request.user``. Client-supplied attribution would
    let an authenticated operator forge cost authorship.
    """

    category = serializers.ChoiceField(choices=VEHICLE_COST_CATEGORY_CHOICES)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    incurred_at = serializers.DateTimeField()
    vendor = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=255
    )
    reference = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=128
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    is_estimate = serializers.BooleanField(required=False, default=False)


# ---- Milestone 3 · Increment 6A — condition-report request serializers ----
#
# Request-body validation only. Responses use dict-builder projections
# in ``views.py`` (matches the ``admin_vehicle_ledger`` totals pattern
# where money formatting + signed-URL insertion live in the view).
#
# What is server-owned and NOT accepted from client bodies:
#
# - ``status`` — always ``draft`` on create; only ``complete_report``
#   transitions it. Client cannot pre-set to ``complete`` or spoof.
# - ``completed_at`` — set atomically by the service when
#   ``complete_report`` runs.
# - ``dealership`` — resolved from ``get_current_dealership(request)``;
#   never accepted from body.
# - ``authored_by`` — set from ``request.user``; client cannot forge
#   authorship.
#
# On finding update, ``report`` and ``dealership`` are also NOT in
# the whitelist (re-parenting / re-scoping is not an editing
# operation — service raises ``ValueError`` if attempted).


class ConditionReportCreateRequestSerializer(serializers.Serializer):
    """Request body for POST ``.../condition-reports/``.

    Every research-backed inspection field (RECON §2.4) is required
    at create time. ``status`` / ``completed_at`` / ``dealership`` /
    ``authored_by`` are server-owned and MUST NOT appear in the
    request body.
    """

    inspector_name = serializers.CharField(max_length=255)
    inspected_at = serializers.DateTimeField()
    mileage_at_inspection = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ConditionFindingCreateRequestSerializer(serializers.Serializer):
    """Request body for POST ``.../condition-reports/<report_id>/findings/``.

    ``report`` is URL-scoped, not body-supplied. ``dealership`` is
    resolved server-side.
    """

    category = serializers.ChoiceField(choices=CONDITION_CATEGORY_CHOICES)
    severity = serializers.ChoiceField(choices=CONDITION_SEVERITY_CHOICES)
    description = serializers.CharField()
    estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
        default=None,
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ConditionFindingUpdateRequestSerializer(serializers.Serializer):
    """Request body for PATCH ``.../findings/<finding_id>/``.

    Every field is optional (PATCH semantics). Whatever the caller
    supplies is passed to :func:`services.condition_report.update_finding`
    via ``**kwargs``; the service's whitelist enforcement is the
    source of truth on what fields are actually updatable — this
    serializer just validates individual field shapes when supplied.

    Attempting to include ``report``, ``dealership``, ``id`` etc.
    surfaces as a ``ValueError`` from the service — this serializer
    doesn't need to reject them defensively.
    """

    category = serializers.ChoiceField(
        choices=CONDITION_CATEGORY_CHOICES, required=False
    )
    severity = serializers.ChoiceField(
        choices=CONDITION_SEVERITY_CHOICES, required=False
    )
    description = serializers.CharField(required=False)
    estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    notes = serializers.CharField(
        required=False, allow_blank=True
    )


# ---- Milestone 3 · Increment 6B — photo API request serializers ----


class PhotoRequestUploadSerializer(serializers.Serializer):
    """Request body for POST ``.../findings/<finding_id>/photos/request-upload/``.

    Client supplies only the intended MIME type. Server generates
    the UUID + canonical key + presigned URL and returns them via
    the ``UploadTarget`` projection. ``dealership``, ``finding``,
    ``photo_uuid`` are all server-owned or URL-scoped.
    """

    content_type = serializers.ChoiceField(
        choices=CONDITION_PHOTO_CONTENT_TYPE_CHOICES
    )


class PhotoAttachSerializer(serializers.Serializer):
    """Request body for POST ``.../findings/<finding_id>/photos/``.

    ``storage_key`` is the key the client received from a prior
    ``request-upload`` response (or wrote to via the local-mode
    receiver). ``content_type`` + ``size_bytes`` are the values the
    client claims for HEAD verification against actual object
    metadata. ``caption`` is optional.

    ``photo_uuid`` is NOT accepted — the service extracts it from
    ``storage_key`` via
    :func:`photo_storage.parse_canonical_key`. ``dealership`` is
    resolved server-side. ``uploaded_by`` is set from
    ``request.user``.
    """

    storage_key = serializers.CharField(max_length=512)
    content_type = serializers.ChoiceField(
        choices=CONDITION_PHOTO_CONTENT_TYPE_CHOICES
    )
    size_bytes = serializers.IntegerField(min_value=1)
    caption = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=255
    )
