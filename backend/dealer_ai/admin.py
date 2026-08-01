from django.contrib import admin

from .models import (
    ChatMessage,
    ChatSession,
    ConditionFinding,
    ConditionFindingPhoto,
    ConditionReport,
    CustomerLead,
    DealerOnboardingProfile,
    Dealership,
    ReconDecision,
    Salesperson,
    UserDealershipRole,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
    VehicleStage,
    VehicleStageEvent,
    Vendor,
    VendorCommunication,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)


@admin.register(Dealership)
class DealershipAdmin(admin.ModelAdmin):
    """Milestone 1 · Increment 4A — enables autocomplete targeting
    from `UserDealershipRoleAdmin` and `SalespersonAdmin`. Read-mostly
    surface; the seeded `slug=default` row is created by migration 0009.
    """

    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "title",
        "phone",
        "email",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "title", "email", "phone", "bio")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "stock_number",
        "year",
        "make",
        "model",
        "trim",
        "condition",
        "price",
        "mileage",
        "is_available",
        "source",
        "last_seen_at",
    )
    list_filter = (
        "condition",
        "body_style",
        "make",
        "is_available",
        "source",
        "year",
    )
    search_fields = ("stock_number", "vin", "model", "trim", "description")
    readonly_fields = ("imported_at", "last_seen_at")


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")
    fields = ("role", "content", "created_at")
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "customer_email",
        "lead_created",
        "created_at",
        "updated_at",
    )
    list_filter = ("lead_created",)
    search_fields = ("id", "customer_name", "customer_email", "customer_phone")
    readonly_fields = ("id", "extracted_profile", "created_at", "updated_at")
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "short_content", "created_at")
    list_filter = ("role",)
    search_fields = ("content",)

    def short_content(self, obj: ChatMessage) -> str:
        return obj.content[:80]


@admin.register(CustomerLead)
class CustomerLeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone",
        "email",
        "urgency",
        "target_monthly_payment",
        "assigned_to",
        "handed_off",
        "created_at",
    )
    list_filter = ("urgency", "handed_off", "assigned_to", "credit_range")
    search_fields = (
        "name",
        "phone",
        "email",
        "notes",
        "conversation_summary",
        "recommended_next_action",
    )
    filter_horizontal = ("interested_vehicles",)
    readonly_fields = (
        "conversation_summary",
        "recommended_next_action",
        "assigned_at",
    )
    autocomplete_fields = ("assigned_to",)


@admin.register(DealerOnboardingProfile)
class DealerOnboardingProfileAdmin(admin.ModelAdmin):
    """SESSION_008: singleton onboarding profile. Only one row is expected
    in v0; the manager flow reads/writes via the API, but the admin allows
    inspection and emergency edits."""

    list_display = ("dealership_name", "store_location", "pilot_approved", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleAcquisition)
class VehicleAcquisitionAdmin(admin.ModelAdmin):
    """Milestone 2 · Increment 1 — read-mostly admin for the buying-event
    record. Primary operator surface is the M2.3 ledger UI; this admin
    is here for internal debugging + emergency corrections."""

    list_display = (
        "vehicle",
        "source",
        "purchase_price",
        "purchase_date",
        "dealership",
        "updated_at",
    )
    list_filter = ("source", "dealership", "purchase_date")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "source_detail",
        "notes",
    )
    autocomplete_fields = ("vehicle", "dealership")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleCost)
class VehicleCostAdmin(admin.ModelAdmin):
    """Milestone 2 · Increment 1 — read-mostly admin for post-acquisition
    cost rows. Same rationale as `VehicleAcquisitionAdmin`. Filters on
    ``category`` + ``is_estimate`` support the common "what's still
    projected vs. committed?" query."""

    list_display = (
        "vehicle",
        "category",
        "amount",
        "incurred_at",
        "vendor",
        "is_estimate",
        "dealership",
        "updated_at",
    )
    list_filter = ("category", "is_estimate", "dealership")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "vendor",
        "reference",
        "notes",
    )
    autocomplete_fields = ("vehicle", "dealership", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConditionReport)
class ConditionReportAdmin(admin.ModelAdmin):
    """Milestone 3 · Increment 1 — read-mostly admin for the condition
    report row. Primary operator surface is the M3.7 condition-report
    UI; this admin is here for internal debugging + emergency
    corrections. Mirrors ``VehicleAcquisitionAdmin`` shape."""

    list_display = (
        "vehicle",
        "inspector_name",
        "inspected_at",
        "mileage_at_inspection",
        "status",
        "completed_at",
        "dealership",
        "updated_at",
    )
    list_filter = ("status", "dealership", "inspected_at")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "inspector_name",
        "notes",
    )
    autocomplete_fields = ("vehicle", "dealership", "authored_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConditionFinding)
class ConditionFindingAdmin(admin.ModelAdmin):
    """Milestone 3 · Increment 1 — read-mostly admin for a finding row.
    Filters on ``severity`` + ``category`` support the common "what's
    still safety-critical vs. advisory?" query."""

    list_display = (
        "report",
        "category",
        "severity",
        "estimated_cost",
        "dealership",
        "updated_at",
    )
    list_filter = ("severity", "category", "dealership")
    search_fields = (
        "report__vehicle__stock_number",
        "report__vehicle__vin",
        "description",
        "notes",
    )
    autocomplete_fields = ("report", "dealership")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConditionFindingPhoto)
class ConditionFindingPhotoAdmin(admin.ModelAdmin):
    """Milestone 3 · Increment 1 — read-mostly admin for photo metadata.
    Storage bytes live in the M3.4 storage backend; this admin surfaces
    the metadata row only. ``public_id`` is the durable external
    identity (see ``ConditionFindingPhoto`` docstring)."""

    list_display = (
        "public_id",
        "finding",
        "content_type",
        "size_bytes",
        "uploaded_by",
        "dealership",
        "created_at",
    )
    list_filter = ("content_type", "dealership")
    search_fields = (
        "public_id",
        "storage_key",
        "caption",
        "finding__report__vehicle__stock_number",
    )
    autocomplete_fields = ("finding", "dealership", "uploaded_by")
    readonly_fields = ("public_id", "created_at")


# ----------------------------------------------------------------------------
# Milestone 4 · Increment 1 (SESSION_066) — recon admin surfaces.
#
# Six read-mostly diagnostic admins mirroring the M2/M3 house pattern
# (list_display / list_filter / search_fields / autocomplete_fields /
# readonly_fields). The primary operator surface lives in M4.7's
# VehicleReconPage; these admins exist for debugging + emergency
# corrections only. No workflow buttons, no transition actions, no
# AI generation, no ledger posting. See ``MILESTONE_4_PLANNING.md``
# §2 row 10.
#
# Delete affordances on Vendor and VendorCommunication are NOT
# offered — the PROTECT contract from planning §5.b (refined
# SESSION_066) makes hard-deleting a referenced Vendor raise
# ``ProtectedError``. The admin defaults would surface a delete
# button that would fail confusingly at DB layer; we drop
# ``has_delete_permission`` on Vendor to align the UI with the
# schema contract.
# ----------------------------------------------------------------------------


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — vendor directory admin.

    Delete disabled at the admin surface to match the PROTECT
    schema contract: normal removal is ``is_active=False``. A
    superuser who genuinely needs to hard-delete an unreferenced
    vendor can do so via the Django shell.
    """

    list_display = (
        "name",
        "slug",
        "is_active",
        "phone",
        "email",
        "dealership",
        "updated_at",
    )
    list_filter = ("is_active", "dealership")
    search_fields = ("name", "slug", "email", "phone", "notes")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("dealership",)
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False


@admin.register(ReconDecision)
class ReconDecisionAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — recon decision (three-tier) admin.

    Filters on ``tier`` support the common "what did we agree to
    skip?" query, which is the warranty-defense entry point per
    RECON §13.1."""

    list_display = (
        "finding",
        "tier",
        "decided_by",
        "decided_at",
        "dealership",
        "updated_at",
    )
    list_filter = ("tier", "dealership", "decided_at")
    search_fields = (
        "finding__report__vehicle__stock_number",
        "finding__report__vehicle__vin",
        "notes",
    )
    autocomplete_fields = ("finding", "dealership", "decided_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — work order admin.

    Filters on ``status`` + ``venue`` + ``category`` support the
    common "what's in progress at which vendor?" / "what's still in
    draft?" queries."""

    list_display = (
        "vehicle",
        "category",
        "venue",
        "vendor",
        "status",
        "estimated_cost",
        "actual_cost",
        "dealership",
        "updated_at",
    )
    list_filter = ("status", "venue", "category", "dealership")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "vendor__name",
        "notes",
        "cancellation_reason",
    )
    autocomplete_fields = (
        "vehicle",
        "dealership",
        "vendor",
        "assignee",
        "approved_by",
        "started_by",
        "completed_by",
        "cancelled_by",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkOrderFinding)
class WorkOrderFindingAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — through-table admin. Minimal
    diagnostic surface for debugging finding→WO wiring."""

    list_display = ("work_order", "finding", "dealership", "created_at")
    list_filter = ("dealership",)
    search_fields = (
        "work_order__vehicle__stock_number",
        "finding__description",
    )
    autocomplete_fields = ("work_order", "finding", "dealership")
    readonly_fields = ("created_at",)


@admin.register(WorkOrderPart)
class WorkOrderPartAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — work order parts admin.

    Filters on ``status`` + ``source_type`` support the common
    "what's still on backorder?" / "which customer-supplied parts
    are we tracking?" queries."""

    list_display = (
        "name",
        "work_order",
        "quantity",
        "status",
        "source_type",
        "source_name",
        "unit_cost",
        "dealership",
        "updated_at",
    )
    list_filter = ("status", "source_type", "dealership")
    search_fields = (
        "name",
        "part_number",
        "source_name",
        "notes",
        "work_order__vehicle__stock_number",
    )
    autocomplete_fields = ("work_order", "dealership")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VendorCommunication)
class VendorCommunicationAdmin(admin.ModelAdmin):
    """Milestone 4 · Increment 1 — vendor communication log admin.

    Filters on ``status`` + ``kind`` + ``channel`` + ``direction``
    support the common "which sent emails are still awaiting reply?"
    and "which inbound comms did we log?" queries. Delete is
    permitted for genuinely orphan drafts, but the M4.5 service will
    typically soft-close by transitioning to a terminal status."""

    list_display = (
        "vendor",
        "work_order",
        "kind",
        "channel",
        "direction",
        "status",
        "sent_at",
        "dealership",
        "updated_at",
    )
    list_filter = (
        "status",
        "kind",
        "channel",
        "direction",
        "dealership",
    )
    search_fields = (
        "vendor__name",
        "work_order__vehicle__stock_number",
        "draft_content",
        "sent_content",
        "notes",
    )
    autocomplete_fields = (
        "dealership",
        "vendor",
        "work_order",
        "drafted_by",
        "approved_by",
        "sent_by",
    )
    readonly_fields = ("created_at", "updated_at")


# ----------------------------------------------------------------------------
# Milestone 5 · Increment 1 (SESSION_075) — vehicle lifecycle admins.
#
# Diagnostic surfaces only. Transition workflow lives in M5.4
# endpoints, not here. Both classes present event-facts and stage state
# as read-only where possible so admin doesn't inadvertently become the
# transition-authoring path (which would bypass the M5.2 service and
# lose the audit-trail invariants).
#
# ``VehicleStageEventAdmin`` disables add + delete: events are
# append-only through the M5.2 service, and hand-editing a historical
# transition would silently break the timeline.
# ----------------------------------------------------------------------------


@admin.register(VehicleStage)
class VehicleStageAdmin(admin.ModelAdmin):
    """Milestone 5 · Increment 1 — current-stage admin.

    Diagnostic; not the transition-authoring surface (that lives in the
    M5.4 admin API). Every mutable-looking field displays but writes to
    it here still bypass the M5.2 service state machine — the write
    path is intentionally the endpoint, not the admin form.
    """

    list_display = (
        "vehicle",
        "current_stage",
        "entered_at",
        "trigger",
        "entered_by",
        "dealership",
        "updated_at",
    )
    list_filter = ("current_stage", "trigger", "dealership")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "last_transition_note",
    )
    autocomplete_fields = ("vehicle", "dealership", "entered_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleStageEvent)
class VehicleStageEventAdmin(admin.ModelAdmin):
    """Milestone 5 · Increment 1 — append-only event log admin.

    Read-only shape: add + delete disabled. Every field is displayed
    read-only in the change form. The event log is the durable audit
    trail M8 aggregates; hand-editing a historical event would silently
    corrupt aging analytics. Historical rows survive user deletion
    (``by`` is SET_NULL).
    """

    list_display = (
        "vehicle",
        "from_stage",
        "to_stage",
        "entered_at",
        "trigger",
        "rule_name",
        "by",
        "dealership",
        "created_at",
    )
    list_filter = ("to_stage", "from_stage", "trigger", "dealership")
    search_fields = (
        "vehicle__stock_number",
        "vehicle__vin",
        "rule_name",
        "notes",
    )
    autocomplete_fields = ("vehicle", "dealership", "by")
    readonly_fields = (
        "vehicle",
        "dealership",
        "from_stage",
        "to_stage",
        "entered_at",
        "by",
        "trigger",
        "rule_name",
        "notes",
        "created_at",
    )

    def has_add_permission(self, request):  # noqa: ARG002
        # Events are appended by the M5.2 service, not the admin form.
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        # Append-only history — refusing delete keeps the timeline honest.
        return False


@admin.register(UserDealershipRole)
class UserDealershipRoleAdmin(admin.ModelAdmin):
    """Milestone 1 · Increment 4A — bootstrap path for the first
    dealer_owner. A superuser creates the initial membership row here
    before Increment 4C ships endpoint auth. No custom forms; the
    default ModelAdmin surface is sufficient for the bootstrap window.
    """

    list_display = ("user", "dealership", "role", "created_at", "updated_at")
    list_filter = ("role", "dealership")
    search_fields = ("user__username", "user__email", "dealership__name", "dealership__slug")
    autocomplete_fields = ("user", "dealership")
    readonly_fields = ("created_at", "updated_at")
