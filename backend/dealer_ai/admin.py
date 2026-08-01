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
    Salesperson,
    UserDealershipRole,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
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
