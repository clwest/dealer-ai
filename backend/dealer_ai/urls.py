from django.urls import path

from . import views

app_name = "dealer_ai"

urlpatterns = [
    path("chat/start/", views.start_chat, name="chat-start"),
    path("chat/message/", views.send_message, name="chat-message"),
    path(
        "chat/session/<uuid:session_id>/",
        views.session_detail,
        name="chat-session-detail",
    ),
    path("leads/", views.create_lead, name="leads-create"),
    path("vehicles/<int:vehicle_id>/", views.vehicle_detail, name="vehicle-detail"),
    path(
        "vehicles/<int:vehicle_id>/ask/",
        views.vehicle_ask,
        name="vehicle-ask",
    ),
    path("admin/leads/", views.admin_lead_list, name="admin-lead-list"),
    path(
        "admin/lead/<int:lead_id>/",
        views.admin_lead_detail,
        name="admin-lead-detail",
    ),
    path(
        "admin/lead/<int:lead_id>/handoff/",
        views.admin_lead_handoff,
        name="admin-lead-handoff",
    ),
    path(
        "admin/chat-sessions/",
        views.admin_chat_session_list,
        name="admin-chat-session-list",
    ),
    path("admin/trends/", views.admin_trends, name="admin-trends"),
    path("admin/pipeline/", views.admin_pipeline, name="admin-pipeline"),
    path("admin/ad-copy/", views.admin_ad_copy, name="admin-ad-copy"),
    path(
        "admin/salespeople/",
        views.admin_salespeople,
        name="admin-salespeople",
    ),
    path(
        "admin/lead/<int:lead_id>/assign/",
        views.admin_lead_assign,
        name="admin-lead-assign",
    ),
    path(
        "admin/audit-events/",
        views.admin_audit_events,
        name="admin-audit-events",
    ),
    # Manager Phase 4: public team page + advisor workspace.
    path("salespeople/", views.public_salespeople, name="salespeople-list"),
    path(
        "salespeople/<slug:slug>/",
        views.public_salesperson_detail,
        name="salespeople-detail",
    ),
    path(
        "advisor/<slug:slug>/",
        views.advisor_workspace,
        name="advisor-workspace",
    ),
    path(
        "advisor/<slug:slug>/lead/<int:lead_id>/follow-up/",
        views.advisor_follow_up,
        name="advisor-follow-up",
    ),
    path("demo/reset/", views.demo_reset, name="demo-reset"),
    path(
        "demo/scenarios/",
        views.demo_load_scenarios,
        name="demo-load-scenarios",
    ),
    # SESSION_008: onboarding singleton profile.
    path(
        "onboarding/profile/",
        views.onboarding_profile,
        name="onboarding-profile",
    ),
    path(
        "onboarding/profile/logo/",
        views.onboarding_logo_upload,
        name="onboarding-logo-upload",
    ),
    # SESSION_010: stateless manager-side chat tester.
    path(
        "manager-chat/",
        views.manager_chat,
        name="manager-chat",
    ),
    # Milestone 1 · Increment 4E — browser auth flow.
    path("auth/login/", views.auth_login, name="auth-login"),
    path("auth/logout/", views.auth_logout, name="auth-logout"),
    path("auth/me/", views.auth_me, name="auth-me"),
]
