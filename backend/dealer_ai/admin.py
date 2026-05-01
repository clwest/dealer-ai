from django.contrib import admin

from .models import ChatMessage, ChatSession, CustomerLead, Salesperson, Vehicle


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
