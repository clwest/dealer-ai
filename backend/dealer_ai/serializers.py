from rest_framework import serializers

from .models import (
    ChatMessage,
    ChatSession,
    CustomerLead,
    DealerOnboardingProfile,
    Salesperson,
    Vehicle,
)
from .services.chat_engine import customer_drivetrain_label


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
        ]
        read_only_fields = [
            "id",
            "created_at",
            "handed_off",
            "conversation_summary",
            "recommended_next_action",
        ]


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
