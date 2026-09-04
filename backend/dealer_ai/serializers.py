from decimal import Decimal

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
from .services.payment_engine import (
    render_estimated_payment_line,
    resolve_store_payment_defaults,
)
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
    # SESSION_234 (finding 31) — per-card estimated-payment line. Uses
    # the store's payment defaults (APR / term / down %) resolved once
    # per response and threaded through serializer context so N cards
    # do not trigger N profile lookups. When the session has captured
    # the customer's stated down_payment or term_months, the caller
    # can pre-populate ``_estimated_payment_line`` on the instance to
    # short-circuit this compute path.
    estimated_payment_line = serializers.SerializerMethodField()

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
            "estimated_payment_line",
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

    def get_estimated_payment_line(self, obj):
        # Prefer an instance-attached value when the caller already
        # composed one (e.g. chat_engine layered the customer's stated
        # down payment on top).
        cached = getattr(obj, "_estimated_payment_line", None)
        if cached is not None:
            return cached
        defaults = _payment_defaults_from_context(self.context)
        # SESSION_235 (finding 50) — when a chat session has stated a
        # down payment or term, thread those onto the payment line so
        # the assistant-card label matches the numbers the LLM is
        # quoting. Store defaults still supply anything the session
        # left blank; the showroom (which has no session) is unaffected.
        session_down = self.context.get("session_down_payment")
        session_term = self.context.get("session_term_months")
        return render_estimated_payment_line(
            obj.price,
            defaults=defaults,
            down_payment=session_down,
            term_months=session_term,
        )


def _payment_defaults_from_context(context: dict) -> dict:
    """Resolve or memoize the store payment defaults for one response.

    Views that emit many vehicles per response set ``payment_defaults``
    on the serializer context to avoid re-fetching the profile per
    card. When absent we look up the profile once and cache it on the
    context dict so nested serializations still benefit.
    """
    cached = context.get("payment_defaults")
    if cached is not None:
        return cached
    profile = _resolve_profile_for_context(context)
    defaults = resolve_store_payment_defaults(profile)
    context["payment_defaults"] = defaults
    return defaults


def _resolve_profile_for_context(context: dict):
    profile = context.get("onboarding_profile")
    if profile is not None:
        return profile
    request = context.get("request")
    if request is None:
        return None
    # Local import — models module already imported at file top, but
    # keep DealerOnboardingProfile lookup lazy to avoid ordering
    # concerns during Django app loading.
    from .services.tenancy import get_current_dealership

    dealership = get_current_dealership(request)
    return (
        DealerOnboardingProfile.objects.filter(dealership=dealership)
        .order_by("-updated_at")
        .first()
    )


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
    "street_address": "",
    "city": "",
    "state": "",
    "postal_code": "",
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
    # SESSION_238 — per-store payment defaults for the est-payment
    # line. Null = "unset; fall back to payment_engine constants
    # (7.49 / 72 / 10)". The dealer sets real numbers on the
    # onboarding page.
    "default_apr": None,
    "default_term_months": None,
    "default_down_payment_pct": None,
    # SESSION_239 — per-store sales tax rate (combined state + city +
    # county) and doc/admin fee dollar amount. Null falls through to
    # the payment_engine constants (4.5% / $599).
    "sales_tax_rate_pct": None,
    "doc_fees": None,
    # SESSION_240 — the store's IANA time zone lives on the Dealership
    # row; SESSION_241.1 changes the no-profile default from Chicago
    # to blank so a store that has never picked a zone is honest about
    # not having one. The onboarding page renders the picker with no
    # default when this is ``""``.
    "dealership_timezone": "",
}


# SESSION_238 — validation bounds for the three payment-default
# fields. Kept out of the serializer body so the preview endpoint
# can reuse them without pulling in the serializer.
PAYMENT_DEFAULT_APR_MIN = 0
PAYMENT_DEFAULT_APR_MAX = 40
PAYMENT_DEFAULT_TERM_MIN = 12
PAYMENT_DEFAULT_TERM_MAX = 96
PAYMENT_DEFAULT_DOWN_PCT_MIN = 0
PAYMENT_DEFAULT_DOWN_PCT_MAX = 50
# SESSION_239 — sales tax 0-15% is wider than any real jurisdiction
# but leaves headroom for future combined-rate outliers; doc fees
# capped at $2,000 because that already exceeds every state's
# statutory cap and the highest observed lot practice. Bounds match
# the frontend gate so the dealer sees the same message twice.
PAYMENT_DEFAULT_TAX_RATE_MIN = 0
PAYMENT_DEFAULT_TAX_RATE_MAX = 15
PAYMENT_DEFAULT_DOC_FEES_MIN = 0
PAYMENT_DEFAULT_DOC_FEES_MAX = 2000


class DealerOnboardingProfileSerializer(serializers.ModelSerializer):
    """Flat snake_case payload mirroring all 35 onboarding fields (27 pre-SESSION_032 + 8 indie shape-of-business).

    SESSION_232 addendum — exposes ``dealership_slug`` (read-only) so
    the public/embed frontend can send it back as the
    ``X-Dealership-Slug`` header on chat and showroom calls. The
    header is how the multi-store backend routes anonymous callers
    to the right store; without it every public session bound to the
    default tenant.

    SESSION_235 addendum — exposes ``readiness`` (read-only) with
    computed values the store can prove for itself (are there any
    active salespeople? any vehicles? which source?). The overview
    page reads these instead of the stored booleans so it can never
    tell a dealer "Sales team not added yet" when three people are
    on the team. Stored booleans remain for backwards compatibility
    but must not be read by anything the store can compute.
    """

    dealership_slug = serializers.CharField(
        source="dealership.slug", read_only=True
    )
    # SESSION_240 (walk finding 28) — the store's IANA time zone lives
    # on the Dealership row (one clock per store; every business-day
    # decision consumes it). Exposed on the profile serializer so the
    # onboarding page can edit it alongside the store address.
    #
    # Deliberately NOT ``source="dealership.timezone"``: the view calls
    # ``serializer.save(dealership=<instance>)`` for new-profile
    # creation, and DRF's ``save()`` merges kwargs into
    # ``validated_data`` — a nested-source field would produce
    # ``validated_data["dealership"] = {"timezone": "..."}`` and then
    # get clobbered by the kwarg to ``<Dealership instance>``, losing
    # the timezone. Plain field + explicit persist in ``create()`` /
    # ``update()`` sidesteps that.
    dealership_timezone = serializers.CharField(
        required=False, allow_blank=True
    )
    dealership_local_now = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()

    def to_representation(self, instance):
        # SESSION_240 — echo the related Dealership's zone on GET even
        # though the field is not source-nested. Kept as a
        # ``to_representation`` override rather than a
        # ``SerializerMethodField`` so the field name stays writable
        # on PATCH / PUT.
        # SESSION_241.1 — a blank column reads back as ``""``, not as
        # "America/Chicago". A silent Chicago default on the wire is
        # what SESSION_240 removed on the database side; do not
        # reintroduce it here. The onboarding page treats ``""`` as
        # "operator has not picked yet" and shows the picker.
        data = super().to_representation(instance)
        data["dealership_timezone"] = instance.dealership.timezone or ""
        return data

    class Meta:
        model = DealerOnboardingProfile
        fields = [
            "dealership_slug",
            "dealership_timezone",
            "dealership_local_now",
            "readiness",
            "dealership_name",
            "store_location",
            # SESSION_239 — structured address parts. ``store_location``
            # stays as the free-text line the header renders; the four
            # parts below are what tax rate + (next session's) time
            # zone can be read from.
            "street_address",
            "city",
            "state",
            "postal_code",
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
            # SESSION_238 — per-store payment defaults for the est-payment
            # line. Nullable; when null the payment_engine module constants
            # (7.49 / 72 / 10) supply the fallback.
            "default_apr",
            "default_term_months",
            "default_down_payment_pct",
            # SESSION_239 — per-store tax rate and doc fees. Nullable;
            # when null the payment_engine constants (4.5 / 599) supply
            # the fallback so a fresh install still renders a payment
            # line.
            "sales_tax_rate_pct",
            "doc_fees",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_default_apr(self, value):
        if value is None:
            return value
        if not (PAYMENT_DEFAULT_APR_MIN <= float(value) <= PAYMENT_DEFAULT_APR_MAX):
            raise serializers.ValidationError(
                f"APR must be between {PAYMENT_DEFAULT_APR_MIN}% "
                f"and {PAYMENT_DEFAULT_APR_MAX}%."
            )
        return value

    def validate_default_term_months(self, value):
        if value is None:
            return value
        if not (PAYMENT_DEFAULT_TERM_MIN <= int(value) <= PAYMENT_DEFAULT_TERM_MAX):
            raise serializers.ValidationError(
                f"Term must be between {PAYMENT_DEFAULT_TERM_MIN} "
                f"and {PAYMENT_DEFAULT_TERM_MAX} months."
            )
        return value

    def validate_default_down_payment_pct(self, value):
        if value is None:
            return value
        if not (
            PAYMENT_DEFAULT_DOWN_PCT_MIN <= float(value) <= PAYMENT_DEFAULT_DOWN_PCT_MAX
        ):
            raise serializers.ValidationError(
                f"Down payment must be between {PAYMENT_DEFAULT_DOWN_PCT_MIN}% "
                f"and {PAYMENT_DEFAULT_DOWN_PCT_MAX}%."
            )
        return value

    def validate_sales_tax_rate_pct(self, value):
        # SESSION_239 — bounds named in the message so the field-scoped
        # 400 reads plainly on the frontend (mirrors SESSION_238).
        if value is None:
            return value
        if not (
            PAYMENT_DEFAULT_TAX_RATE_MIN
            <= float(value)
            <= PAYMENT_DEFAULT_TAX_RATE_MAX
        ):
            raise serializers.ValidationError(
                f"Sales tax rate must be between "
                f"{PAYMENT_DEFAULT_TAX_RATE_MIN}% and "
                f"{PAYMENT_DEFAULT_TAX_RATE_MAX}%."
            )
        return value

    def validate_doc_fees(self, value):
        if value is None:
            return value
        if not (
            PAYMENT_DEFAULT_DOC_FEES_MIN
            <= float(value)
            <= PAYMENT_DEFAULT_DOC_FEES_MAX
        ):
            raise serializers.ValidationError(
                f"Doc / admin fee must be between "
                f"${PAYMENT_DEFAULT_DOC_FEES_MIN} and "
                f"${PAYMENT_DEFAULT_DOC_FEES_MAX}."
            )
        return value

    def validate_state(self, value):
        # SESSION_239 — the state field is a two-letter code from
        # US_STATE_CODES (or blank). A full-name string (``"Arizona"``)
        # or an unknown two-letter code (``"ZZ"``) is rejected so
        # anything that later derives a tax jurisdiction or a time
        # zone from this field can trust it.
        from .models import US_STATE_CODES

        if not value:
            return value
        upper = value.strip().upper()
        if upper not in US_STATE_CODES:
            raise serializers.ValidationError(
                f"State must be a two-letter US code (e.g., AZ). "
                f"Got: {value!r}."
            )
        return upper

    def validate_dealership_timezone(self, value):
        # SESSION_240 — reject anything that isn't a real IANA zone
        # name. The frontend's picker only offers a curated shortlist,
        # but the API accepts any zoneinfo name so an operator on a
        # coast we haven't listed can still set the right one.
        from zoneinfo import available_timezones

        if value in (None, ""):
            return ""
        candidate = value.strip()
        if candidate not in available_timezones():
            raise serializers.ValidationError(
                f"Time zone must be a known IANA name "
                f"(e.g., America/Phoenix). Got: {value!r}."
            )
        return candidate

    def get_dealership_local_now(self, obj) -> str:
        # SESSION_240 — the onboarding page renders this as
        # "It is 3:12 PM at the store right now" beside the timezone
        # picker, so an operator sees proof the zone they picked is
        # the one the platform will use.
        from .services.store_time import store_now

        return store_now(obj.dealership).isoformat()

    def update(self, instance, validated_data):
        # SESSION_240 — persist ``dealership_timezone`` back to the
        # related Dealership before ModelSerializer touches the
        # profile's own fields. Pop first so ModelSerializer never
        # sees an attribute that doesn't exist on the profile model.
        # SESSION_241.1 — when the field is blank and the store's zone
        # is also blank, try to auto-seed from the state. Only writes
        # when the state resolves to a single zone; a multi-zone state
        # (TX, FL, ...) still leaves the column blank so the operator
        # picks explicitly on the onboarding page.
        new_tz = validated_data.pop("dealership_timezone", None)
        state = validated_data.get("state") or getattr(instance, "state", "")
        resolved_tz = _resolve_timezone_or_seed(
            new_tz, instance.dealership.timezone, state
        )
        if resolved_tz != instance.dealership.timezone:
            instance.dealership.timezone = resolved_tz
            instance.dealership.save(update_fields=["timezone"])
        return super().update(instance, validated_data)

    def create(self, validated_data):
        # SESSION_240 — same as ``update`` for new-profile creation.
        # The view passes ``dealership=<Dealership instance>`` as a
        # kwarg to ``save()``; DRF merges it into validated_data
        # ahead of this call, so ``validated_data["dealership"]`` is
        # already the instance we want. We just need to pop the
        # standalone timezone field and apply it after.
        new_tz = validated_data.pop("dealership_timezone", None)
        instance = super().create(validated_data)
        state = validated_data.get("state") or getattr(instance, "state", "")
        resolved_tz = _resolve_timezone_or_seed(
            new_tz, instance.dealership.timezone, state
        )
        if resolved_tz != instance.dealership.timezone:
            instance.dealership.timezone = resolved_tz
            instance.dealership.save(update_fields=["timezone"])
        return instance

    def get_readiness(self, obj) -> dict:
        return compute_readiness(obj.dealership, profile=obj)


def _resolve_timezone_or_seed(
    explicit: str | None, current: str, state: str
) -> str:
    """Return the zone the Dealership row should end up with.

    SESSION_241.1 (walk finding 28 — part 3) — three cases in order:

    1. The operator sent an explicit ``dealership_timezone`` — use it.
       An empty string is treated as "clear" so the operator can
       unset a wrong zone.
    2. No explicit value AND the Dealership is already blank AND the
       store's state resolves to a single IANA zone — seed from state
       via ``suggest_timezone_for_state``.
    3. Otherwise — leave the field alone. A multi-zone state (TX, FL,
       ...) that has never been picked stays blank; the readiness card
       shows the attention item and the operator picks on onboarding.
    """
    if explicit is not None:
        return explicit.strip()
    if (current or "").strip():
        return current
    from .services.store_time import suggest_timezone_for_state

    suggested = suggest_timezone_for_state(state or "")
    return suggested or ""


def compute_readiness(dealership, *, profile=None) -> dict:
    """Compute the readiness signals the store can prove for itself.

    SESSION_235 (overview honesty). The dealership either has
    active salespeople or it doesn't; it either has vehicles or
    it doesn't. Asking a human to also flip a checkbox to say so
    is how the overview ended up telling a dealer "Sales team not
    added yet" while three people were on the team and 130 cars
    were on the lot. Compute; don't flag.

    SESSION_238 (payment defaults). ``payment_defaults_set`` is
    true when the profile has all three of default_apr,
    default_term_months, default_down_payment_pct populated —
    i.e. the store's own numbers are driving the est-payment
    line and cards are not silently on the 7.49 / 72 / 10 fallback.

    SESSION_241.1 (walk finding 28 — part 3). ``timezone_set`` is true
    when the dealership's ``timezone`` column carries a real IANA name.
    When it is blank the store has no clock; every business-day
    decision then falls back to the process zone with a visible
    warning (see ``services.store_time._zone_for``) — and the profile
    section is not "done" until the operator picks one on onboarding.

    Returns the shape:
        {
          "salespeople_added":   bool,   # ≥1 active salesperson
          "salespeople_count":   int,
          "inventory_connected": bool,   # ≥1 vehicle
          "inventory_count":     int,
          "inventory_source":    str,    # human label, e.g.
                                         #   "130 vehicles · demo seed"
                                         #   "24 vehicles · CSV import"
                                         #   ""  when count == 0
          "payment_defaults_set": bool,  # all three of APR/term/down set
          "timezone_set":        bool,   # dealership.timezone non-blank
        }
    """
    salespeople_count = Salesperson.objects.filter(
        dealership=dealership, is_active=True
    ).count()
    vehicles_qs = Vehicle.objects.filter(dealership=dealership)
    inventory_count = vehicles_qs.count()
    payment_defaults_set = bool(
        profile is not None
        and profile.default_apr is not None
        and profile.default_term_months
        and profile.default_down_payment_pct is not None
    )
    return {
        "salespeople_added": salespeople_count > 0,
        "salespeople_count": salespeople_count,
        "inventory_connected": inventory_count > 0,
        "inventory_count": inventory_count,
        "inventory_source": _summarize_inventory_source(
            vehicles_qs, inventory_count
        ),
        "payment_defaults_set": payment_defaults_set,
        "timezone_set": bool((dealership.timezone or "").strip()),
    }


def _summarize_inventory_source(vehicles_qs, count: int) -> str:
    """Compose the "130 vehicles · demo seed" label.

    Groups the raw ``source`` values into three human labels so the
    attention list can name where the cars came from: demo seed,
    CSV import, or live feed. Empty when there are no vehicles.
    """
    if count == 0:
        return ""
    raw_sources = list(
        vehicles_qs.exclude(source="")
        .values_list("source", flat=True)
        .distinct()
    )
    demo = any("seed" in s.lower() or "demo" in s.lower() for s in raw_sources)
    csv = any(s.lower().startswith("csv") for s in raw_sources)
    feed = any(
        not ("seed" in s.lower() or "demo" in s.lower() or s.lower().startswith("csv"))
        for s in raw_sources
    )
    labels = []
    if demo:
        labels.append("demo seed")
    if csv:
        labels.append("CSV import")
    if feed:
        labels.append("live feed")
    if not labels:
        labels.append("legacy")
    noun = "vehicle" if count == 1 else "vehicles"
    return f"{count} {noun} · {' + '.join(labels)}"


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
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    purchase_date = serializers.DateField()
    buyer_fees = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )
    arbitration_fees = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )
    transportation_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )
    title_acquisition_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
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
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    # SESSION_227 — the "tech lifted the car and found a seal" path.
    # When True, ``add_finding`` allows the append even though the
    # parent report is already ``complete``.
    discovered_during_work = serializers.BooleanField(
        required=False, default=False
    )
    discovered_on_work_order_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
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
        min_value=Decimal("0"),
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
