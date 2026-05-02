import uuid

from django.db import models


class Vehicle(models.Model):
    CONDITION_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
        ("certified", "Certified Pre-Owned"),
    ]

    BODY_STYLE_CHOICES = [
        ("truck", "Truck"),
        ("suv", "SUV"),
        ("car", "Car"),
        ("ev", "EV"),
        ("van", "Van"),
    ]

    stock_number = models.CharField(max_length=32, unique=True)
    vin = models.CharField(max_length=32, blank=True)
    year = models.PositiveIntegerField()
    make = models.CharField(max_length=64, default="Ford")
    model = models.CharField(max_length=64)
    trim = models.CharField(max_length=128, blank=True)
    body_style = models.CharField(max_length=16, choices=BODY_STYLE_CHOICES, default="suv")
    condition = models.CharField(max_length=16, choices=CONDITION_CHOICES, default="new")
    mileage = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exterior_color = models.CharField(max_length=64, blank=True)
    interior_color = models.CharField(max_length=64, blank=True)
    drivetrain = models.CharField(max_length=32, blank=True)
    transmission = models.CharField(max_length=32, blank=True)
    fuel_type = models.CharField(max_length=32, blank=True, default="Gasoline")
    engine = models.CharField(max_length=128, blank=True)
    features = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    url = models.URLField(blank=True)
    is_available = models.BooleanField(default=True)
    # Import provenance — set by management/commands/import_inventory.py
    # (or seed_demo_vehicles for the bundled demo set).
    source = models.CharField(max_length=64, blank=True, default="")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "model"]

    def __str__(self) -> str:
        return f"{self.year} {self.make} {self.model} {self.trim} (#{self.stock_number})"

    @property
    def display_name(self) -> str:
        parts = [str(self.year), self.make, self.model, self.trim]
        return " ".join(p for p in parts if p)


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_name = models.CharField(max_length=128, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    # Free-form session metadata (e.g. UTM, page, channel).
    metadata = models.JSONField(default=dict, blank=True)
    # Structured intent profile, merged across turns by intent_parser.
    extracted_profile = models.JSONField(default=dict, blank=True)
    lead_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ChatSession {self.id}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
        ("tool", "Tool"),
    ]

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    matched_vehicles = models.ManyToManyField(
        Vehicle, blank=True, related_name="chat_mentions"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        snippet = self.content[:60].replace("\n", " ")
        return f"[{self.role}] {snippet}"


class Salesperson(models.Model):
    """Manager Phase 4: dealership advisor profile.

    Used by:
      - the manager-side assignment dropdown (LeadDetailModal),
      - the public-facing "Meet the team" page,
      - the per-advisor workspace at ``/dealer-ai-advisor/<slug>``.

    Inactive salespeople (``is_active=False``) are kept around so leads
    they previously owned still resolve their advisor — historical
    accuracy beats list cleanliness. Inactive advisors are filtered out
    of the assignment dropdown, the public team page, and workspace
    lookups.
    """

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=128, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    photo_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    # JSON list, e.g. ["F-150", "Trucks", "First-time buyers"]. Manager edits
    # via Django admin. No enum — the demo seeder ships representative values.
    specialties = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]

    def __str__(self) -> str:
        suffix = "" if self.is_active else " (inactive)"
        return f"{self.name}{suffix}"


class CustomerLead(models.Model):
    URGENCY_CHOICES = [
        ("immediate", "Buying now"),
        ("this_week", "This week"),
        ("this_month", "This month"),
        ("researching", "Just researching"),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    name = models.CharField(max_length=128)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    target_monthly_payment = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    down_payment = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    trade_in = models.CharField(max_length=255, blank=True)
    urgency = models.CharField(
        max_length=32, choices=URGENCY_CHOICES, blank=True, default=""
    )
    interested_vehicles = models.ManyToManyField(
        Vehicle, blank=True, related_name="leads"
    )
    credit_range = models.CharField(max_length=64, blank=True)
    conversation_summary = models.TextField(blank=True)
    recommended_next_action = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    handed_off = models.BooleanField(default=False)
    # Manager Phase 4: salesperson assignment. SET_NULL on advisor
    # delete/deactivate keeps the lead intact — but per the locked Phase 4
    # decision, we never auto-unassign on deactivation. The dropdown filters
    # inactive advisors; existing assignments stay.
    assigned_to = models.ForeignKey(
        Salesperson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.urgency or 'no urgency'})"


class DealerOnboardingProfile(models.Model):
    """SESSION_008: persistence for the /dealer-ai-onboarding manager flow.

    v0 is **one-store**: the view layer treats this as a singleton (loads
    .first(), upserts on save). Multi-tenant boundaries land with the
    Dealership entity in the assistant / agent roadmap; for now the
    constraint is enforced in code, not schema, so the migration stays
    cheap to revisit.

    Field shapes mirror the frontend onboarding page sections (dealership
    profile, manager preferences, salesperson seed, assistant behavior,
    pilot checklist). Names follow the future schema sketched in
    docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md so a future
    migration can split this into DealerAssistant / SalespersonAgent /
    StorePolicyProfile without renaming columns.
    """

    # Dealership profile.
    dealership_name = models.CharField(max_length=255, blank=True, default="")
    store_location = models.CharField(max_length=255, blank=True, default="")
    main_brands = models.CharField(max_length=255, blank=True, default="")
    sales_phone = models.CharField(max_length=64, blank=True, default="")
    website = models.CharField(max_length=255, blank=True, default="")
    # SESSION_021 — hosted logo URL. Falls back to the kit's static
    # asset (DEFAULT_DEALER.logoPath on the frontend) when blank.
    # CharField, not URLField, so the form can save partial drafts
    # without strict URL validation; the frontend type=url input gives
    # browser-side validation, and the consumer (`useBrand()`) just
    # passes the string through to `<img src>` which already handles
    # bad URLs via its own `onError` fallback.
    logo_url = models.CharField(max_length=512, blank=True, default="")

    # Manager preferences.
    sales_tone = models.CharField(max_length=128, blank=True, default="")
    pricing_comfort = models.CharField(max_length=128, blank=True, default="")
    appointment_preference = models.CharField(max_length=128, blank=True, default="")
    lead_handoff_style = models.CharField(max_length=128, blank=True, default="")

    # Salesperson seed profile (one salesperson captured during onboarding;
    # the full team lives in Salesperson via /dealer-ai-admin/team).
    salesperson_name = models.CharField(max_length=128, blank=True, default="")
    salesperson_role = models.CharField(max_length=128, blank=True, default="")
    salesperson_phone = models.CharField(max_length=64, blank=True, default="")
    salesperson_email = models.CharField(max_length=255, blank=True, default="")
    salesperson_specialties = models.CharField(max_length=512, blank=True, default="")
    salesperson_preferred_tone = models.CharField(max_length=128, blank=True, default="")
    salesperson_intro = models.TextField(blank=True, default="")

    # Assistant behavior.
    dealership_greeting = models.TextField(blank=True, default="")
    approved_phrases = models.TextField(blank=True, default="")
    banned_phrases = models.TextField(blank=True, default="")
    escalation_rule = models.TextField(blank=True, default="")
    payment_disclaimer = models.TextField(blank=True, default="")

    # Pilot checklist booleans.
    inventory_connected = models.BooleanField(default=False)
    finance_rules_reviewed = models.BooleanField(default=False)
    salespeople_added = models.BooleanField(default=False)
    demo_prompts_tested = models.BooleanField(default=False)
    pilot_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.dealership_name or "Dealer onboarding profile"
