from django.urls import path

from . import views, views_lifecycle, views_recon

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
    # Milestone 2 · Increment 6 — vehicle investment ledger admin API.
    path(
        "admin/vehicles/<str:stock_number>/ledger/",
        views.admin_vehicle_ledger,
        name="admin-vehicle-ledger",
    ),
    path(
        "admin/vehicles/<str:stock_number>/acquisition/",
        views.admin_vehicle_acquisition_upsert,
        name="admin-vehicle-acquisition",
    ),
    path(
        "admin/vehicles/<str:stock_number>/costs/",
        views.admin_vehicle_cost_create,
        name="admin-vehicle-cost-create",
    ),
    # Milestone 3 · Increment 6A — condition-report admin API (core).
    # Photo endpoints ship in Increment 6B.
    path(
        "admin/vehicles/<str:stock_number>/condition-report/latest/",
        views.admin_condition_report_latest,
        name="admin-condition-report-latest",
    ),
    path(
        "admin/vehicles/<str:stock_number>/condition-reports/",
        views.admin_condition_report_create,
        name="admin-condition-report-create",
    ),
    path(
        "admin/vehicles/<str:stock_number>/condition-reports/"
        "<int:report_id>/complete/",
        views.admin_condition_report_complete,
        name="admin-condition-report-complete",
    ),
    path(
        "admin/vehicles/<str:stock_number>/condition-reports/"
        "<int:report_id>/findings/",
        views.admin_condition_finding_create,
        name="admin-condition-finding-create",
    ),
    # PATCH + DELETE share the same URL path — Django URL dispatch is
    # method-agnostic, so a single view function handles both HTTP
    # verbs. The URL name intentionally omits an "update"/"delete"
    # suffix; test code refers to the shared name.
    path(
        "admin/vehicles/<str:stock_number>/findings/<int:finding_id>/",
        views.admin_condition_finding_detail,
        name="admin-condition-finding-detail",
    ),
    # Milestone 3 · Increment 6B — photo API + local-mode receiver.
    path(
        "admin/vehicles/<str:stock_number>/findings/"
        "<int:finding_id>/photos/request-upload/",
        views.admin_condition_photo_request_upload,
        name="admin-condition-photo-request-upload",
    ),
    path(
        "admin/vehicles/<str:stock_number>/findings/"
        "<int:finding_id>/photos/",
        views.admin_condition_photo_attach,
        name="admin-condition-photo-attach",
    ),
    path(
        "admin/vehicles/<str:stock_number>/photos/"
        "<uuid:public_id>/",
        views.admin_condition_photo_delete,
        name="admin-condition-photo-delete",
    ),
    path(
        "admin/vehicles/<str:stock_number>/findings/"
        "<int:finding_id>/photos/local-upload/",
        views.admin_condition_photo_local_upload_receiver,
        name="admin-condition-photo-local-upload",
    ),
    # ---- Milestone 4 · Increment 6 — recon admin API -----------------
    # Vendor CRUD.
    path(
        "admin/vendors/",
        views_recon.admin_vendor_list,
        name="admin-vendor-list",
    ),
    path(
        "admin/vendors/<slug:slug>/",
        views_recon.admin_vendor_detail,
        name="admin-vendor-detail",
    ),
    # Recon dashboard.
    path(
        "admin/vehicles/<str:stock_number>/recon/",
        views_recon.admin_recon_dashboard,
        name="admin-recon-dashboard",
    ),
    # Recon decision.
    path(
        "admin/vehicles/<str:stock_number>/"
        "findings/<int:finding_id>/recon-decision/",
        views_recon.admin_recon_decision_create,
        name="admin-recon-decision-create",
    ),
    # WorkOrder lifecycle.
    path(
        "admin/vehicles/<str:stock_number>/work-orders/",
        views_recon.admin_work_order_create,
        name="admin-work-order-create",
    ),
    path(
        "admin/work-orders/<int:wo_id>/approve/",
        views_recon.admin_work_order_approve,
        name="admin-work-order-approve",
    ),
    path(
        "admin/work-orders/<int:wo_id>/start/",
        views_recon.admin_work_order_start,
        name="admin-work-order-start",
    ),
    path(
        "admin/work-orders/<int:wo_id>/complete/",
        views_recon.admin_work_order_complete,
        name="admin-work-order-complete",
    ),
    path(
        "admin/work-orders/<int:wo_id>/cancel/",
        views_recon.admin_work_order_cancel,
        name="admin-work-order-cancel",
    ),
    path(
        "admin/work-orders/<int:wo_id>/",
        views_recon.admin_work_order_patch,
        name="admin-work-order-patch",
    ),
    path(
        "admin/work-orders/<int:wo_id>/findings/",
        views_recon.admin_work_order_attach_findings,
        name="admin-work-order-attach-findings",
    ),
    path(
        "admin/work-orders/<int:wo_id>/findings/<int:finding_id>/",
        views_recon.admin_work_order_detach_finding,
        name="admin-work-order-detach-finding",
    ),
    # Parts.
    path(
        "admin/work-orders/<int:wo_id>/parts/",
        views_recon.admin_work_order_part_create,
        name="admin-work-order-part-create",
    ),
    path(
        "admin/parts/<int:part_id>/",
        views_recon.admin_part_detail,
        name="admin-part-detail",
    ),
    # Vendor communications.
    path(
        "admin/work-orders/<int:wo_id>/comms/draft/",
        views_recon.admin_work_order_comm_draft,
        name="admin-work-order-comm-draft",
    ),
    path(
        "admin/comms/<int:comm_id>/approve/",
        views_recon.admin_comm_approve,
        name="admin-comm-approve",
    ),
    path(
        "admin/comms/<int:comm_id>/mark-sent/",
        views_recon.admin_comm_mark_sent,
        name="admin-comm-mark-sent",
    ),
    path(
        "admin/comms/log/",
        views_recon.admin_comm_log,
        name="admin-comm-log",
    ),
    # ---- Milestone 5 · Increment 4 — lifecycle admin API -------------
    #
    # Three endpoints wrapping the M5.2 + M5.3 service surface for the
    # M5.6 operator UI. All three share
    # ``IsReconManagerSalesManagerOrOwnerAtActiveDealership`` (M4.6);
    # per-transition role authority happens at the service layer.
    #
    # Domain-error → HTTP mapping (per SESSION_075 §0.a item 5):
    # CrossTenantLifecycleError → 404; InvalidStageTransitionError → 409;
    # UnauthorizedStageTransitionError → 403; StageAlreadyCurrentError
    # → 409; ValueError → 400.
    path(
        "admin/vehicles/<str:stock_number>/lifecycle/",
        views_lifecycle.admin_lifecycle_dashboard,
        name="admin-lifecycle-dashboard",
    ),
    path(
        "admin/vehicles/<str:stock_number>/lifecycle/transition/",
        views_lifecycle.admin_lifecycle_manual_transition,
        name="admin-lifecycle-manual-transition",
    ),
    path(
        "admin/vehicles/<str:stock_number>/lifecycle/transition/rule/",
        views_lifecycle.admin_lifecycle_rule_transition,
        name="admin-lifecycle-rule-transition",
    ),
]
