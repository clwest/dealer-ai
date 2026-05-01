# dealer_ai/models.py

from django.db import models


class Vehicle(models.Model):
    stock_number = models.CharField(max_length=100, unique=True)
    vin = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField()
    make = models.CharField(max_length=100, default="Ford")
    model = models.CharField(max_length=100)
    trim = models.CharField(max_length=150, blank=True, null=True)
    condition = models.CharField(max_length=50, choices=[("new", "New"), ("used", "Used")])
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mileage = models.IntegerField(blank=True, null=True)
    body_style = models.CharField(max_length=100, blank=True, null=True)
    drivetrain = models.CharField(max_length=100, blank=True, null=True)
    fuel_type = models.CharField(max_length=100, blank=True, null=True)
    exterior_color = models.CharField(max_length=100, blank=True, null=True)
    interior_color = models.CharField(max_length=100, blank=True, null=True)
    features = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatSession(models.Model):
    session_key = models.CharField(max_length=255, unique=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    extracted_profile = models.JSONField(default=dict, blank=True)
    lead_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=[("user", "User"), ("assistant", "Assistant"), ("system", "System")])
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CustomerLead(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    vehicle_interest = models.CharField(max_length=255, blank=True)
    target_monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    down_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    trade_in = models.BooleanField(default=False)
    credit_range = models.CharField(max_length=100, blank=True)
    urgency = models.CharField(max_length=100, blank=True)
    conversation_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)