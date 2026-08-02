from django.urls import path

from . import (
    views,
    views_analytics,
    views_delivery,
    views_f_and_i,
    views_lifecycle,
    views_listings,
    views_photos,
    views_recon,
    views_sale,
    views_showroom,
)

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
    # ---- Milestone 6 · Increment 5 — photo + listing admin API ----------
    #
    # URL shape per SESSION_086 §1 Option A user-confirmed:
    #   - Vehicle-scoped operations (upload / list / reorder) nested
    #     under /admin/vehicles/<stock_number>/photos/.
    #   - Photo mutations by public_id (M6.2 SESSION_083 §2 confirmed)
    #     under /admin/vehicle-photos/<uuid:public_id>/.
    #   - Listing endpoints (OneToOne with Vehicle) nested under
    #     /admin/vehicles/<stock_number>/listing/.
    #   - Public showroom endpoint (M6.5 §5.e publish semantics)
    #     under /showroom/vehicles/<stock_number>/.
    #
    # Domain-error mapping per SESSION_086 handoff; distinct errors →
    # distinct HTTP status codes.
    # Photo endpoints.
    path(
        "admin/vehicles/<str:stock_number>/photos/",
        views_photos.admin_photo_list,
        name="admin-photo-list",
    ),
    path(
        "admin/vehicles/<str:stock_number>/photos/upload/",
        views_photos.admin_photo_upload,
        name="admin-photo-upload",
    ),
    path(
        "admin/vehicles/<str:stock_number>/photos/reorder/",
        views_photos.admin_photo_reorder,
        name="admin-photo-reorder",
    ),
    path(
        "admin/vehicle-photos/<uuid:public_id>/set-primary/",
        views_photos.admin_photo_set_primary,
        name="admin-photo-set-primary",
    ),
    path(
        "admin/vehicle-photos/<uuid:public_id>/",
        views_photos.admin_photo_delete,
        name="admin-photo-delete",
    ),
    path(
        "admin/vehicle-photos/<uuid:public_id>/restore/",
        views_photos.admin_photo_restore,
        name="admin-photo-restore",
    ),
    # Listing endpoints.
    path(
        "admin/vehicles/<str:stock_number>/listing/",
        views_listings.admin_listing_read,
        name="admin-listing-read",
    ),
    path(
        "admin/vehicles/<str:stock_number>/listing/draft/",
        views_listings.admin_listing_draft,
        name="admin-listing-draft",
    ),
    path(
        "admin/vehicles/<str:stock_number>/listing/regenerate/",
        views_listings.admin_listing_regenerate,
        name="admin-listing-regenerate",
    ),
    path(
        "admin/vehicles/<str:stock_number>/listing/approve/",
        views_listings.admin_listing_approve,
        name="admin-listing-approve",
    ),
    path(
        "admin/vehicles/<str:stock_number>/listing/publish/",
        views_listings.admin_listing_publish,
        name="admin-listing-publish",
    ),
    path(
        "admin/vehicles/<str:stock_number>/listing/unpublish/",
        views_listings.admin_listing_unpublish,
        name="admin-listing-unpublish",
    ),
    # Public showroom endpoint (AllowAny — retail gate is the auth).
    path(
        "showroom/vehicles/<str:stock_number>/",
        views_showroom.showroom_vehicle_detail,
        name="showroom-vehicle-detail",
    ),
    # ---- Milestone 8 · Increment 1 — analytics admin API -------------
    # Every endpoint role-gated on
    # ``IsReconManagerSalesManagerOrOwnerAtActiveDealership`` per
    # MILESTONE_8_PLANNING.md §1.9. Additional aggregations land at
    # M8.2 – M8.4; the operator UI at M8.5.
    path(
        "admin/analytics/recon-cost-per-source/",
        views_analytics.admin_analytics_recon_cost_per_source,
        name="admin-analytics-recon-cost-per-source",
    ),
    path(
        "admin/analytics/vendor-performance/",
        views_analytics.admin_analytics_vendor_performance,
        name="admin-analytics-vendor-performance",
    ),
    path(
        "admin/analytics/stage-aging-trend/",
        views_analytics.admin_analytics_stage_aging_trend,
        name="admin-analytics-stage-aging-trend",
    ),
    path(
        "admin/analytics/sla-breach-patterns/",
        views_analytics.admin_analytics_sla_breach_patterns,
        name="admin-analytics-sla-breach-patterns",
    ),
    path(
        "admin/analytics/vehicle-type-recon-cost/",
        views_analytics.admin_analytics_vehicle_type_recon_cost,
        name="admin-analytics-vehicle-type-recon-cost",
    ),
    path(
        "admin/analytics/days-at-frontline-proxy/",
        views_analytics.admin_analytics_days_at_frontline_proxy,
        name="admin-analytics-days-at-frontline-proxy",
    ),
    # ---- Milestone 9 · Increment 3 — analytics extensions unlocking
    # M8 deferrals (Q3 true / Q6 gross-profit trend / Q8 true inventory
    # turn). Same role gate + query-arg conventions as M8.1-M8.4.
    path(
        "admin/analytics/vehicle-type-profitability/",
        views_analytics.admin_analytics_vehicle_type_profitability,
        name="admin-analytics-vehicle-type-profitability",
    ),
    path(
        "admin/analytics/gross-profit-trend/",
        views_analytics.admin_analytics_gross_profit_trend,
        name="admin-analytics-gross-profit-trend",
    ),
    path(
        "admin/analytics/inventory-turn/",
        views_analytics.admin_analytics_inventory_turn,
        name="admin-analytics-inventory-turn",
    ),
    # ---- Milestone 9 · Increment 4 — Q7 buyer estimate accuracy.
    # Q7 was deferred at M8 pending the acquisition-buyer FK; the
    # substrate shipped at M9.1 and the verb now consumes it.
    path(
        "admin/analytics/buyer-estimate-accuracy/",
        views_analytics.admin_analytics_buyer_estimate_accuracy,
        name="admin-analytics-buyer-estimate-accuracy",
    ),
    # ---- Milestone 9 · Increment 1 — Sale admin API -------------------
    # Role-gated on
    # ``IsReconManagerSalesManagerOrOwnerAtActiveDealership`` per
    # MILESTONE_9_PLANNING.md §1.6 (mirrors the M4-M8 pattern).
    # Domain-error mapping in ``views_sale.py``:
    #   CrossTenantSaleError → 404;
    #   SaleAlreadyExistsError → 409;
    #   ValueError → 400.
    # POST creates the Sale; GET reads it (M9.5 additive per
    # SESSION_104 §0.a). Same URL name preserved.
    path(
        "admin/vehicles/<str:stock_number>/sale/",
        views_sale.admin_sale_create,
        name="admin-sale-create",
    ),
    # ---- Milestone 9 · Increment 2 — Delivery admin API ---------------
    # Role-gated per M4-M8 pattern. Domain-error mapping in
    # ``views_delivery.py``:
    #   CrossTenantDeliveryError → 404;
    #   SaleNotFoundForDeliveryError → 409 (workflow ordering);
    #   DeliveryAlreadyExistsError → 409;
    #   UnknownChecklistKeyError → 400;
    #   ValueError → 400.
    path(
        "admin/vehicles/<str:stock_number>/delivery/",
        views_delivery.admin_delivery_create,
        name="admin-delivery-create",
    ),
    path(
        "admin/deliveries/<int:delivery_id>/",
        views_delivery.admin_delivery_update,
        name="admin-delivery-update",
    ),
    # ---- Milestone 10 · Increment 1 — F&I credit-application API ------
    # Role-gated on
    # ``IsFinanceManagerOrOwnerAtActiveDealership`` per
    # MILESTONE_10_PLANNING.md §7 M10.1. ``f_and_i_manager`` +
    # ``dealer_owner`` at the active dealership pass; every other
    # role receives 403 (deliberate — F&I has distinct compliance
    # obligations from sales / recon per FINANCE §6.4).
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantCreditApplicationError → 404;
    #   ValueError → 400.
    path(
        "admin/credit-applications/",
        views_f_and_i.admin_credit_application_create,
        name="admin-credit-application-create",
    ),
    # ---- Milestone 10 · Increment 2 — F&I deal-structure API ----------
    # Role-gated on the same permission class as M10.1 (composed
    # via ``_M101_PERMS`` in views_f_and_i). Flat URL shape per
    # MILESTONE_10_PLANNING.md §1.9.a Option A (user-confirmed at
    # SESSION_107 open, recorded in §0.a) — matches the M10.1
    # credit-application URL and the platform-wide M1-M9 flat
    # resource-naming convention.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantDealStructureError → 404;
    #   ValueError → 400.
    path(
        "admin/deal-structures/",
        views_f_and_i.admin_deal_structure_create,
        name="admin-deal-structure-create",
    ),
    # ---- Milestone 10 · Increment 3 — Lender catalog + submission API --
    # Role-gated on the same permission class as M10.1/M10.2 (composed
    # via ``_M101_PERMS`` in views_f_and_i). Flat URL shape per §1.9.a.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   DuplicateLenderProgramError → 409;
    #   CrossTenantLenderSubmissionError → 404;
    #   ValueError → 400.
    path(
        "admin/lender-programs/",
        views_f_and_i.admin_lender_program_create,
        name="admin-lender-program-create",
    ),
    path(
        "admin/lender-submissions/",
        views_f_and_i.admin_lender_submission_create,
        name="admin-lender-submission-create",
    ),
    path(
        "admin/lender-submissions/<int:pk>/",
        views_f_and_i.admin_lender_submission_update,
        name="admin-lender-submission-update",
    ),
    # ---- Milestone 10 · Increment 4 — Stipulation admin API -----------
    # Role-gated on the same permission class as M10.1-M10.3
    # (``_M101_PERMS``). Flat URL shape per §1.9.a.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantStipulationError → 404;
    #   ValueError → 400.
    path(
        "admin/stipulations/",
        views_f_and_i.admin_stipulation_create,
        name="admin-stipulation-create",
    ),
    path(
        "admin/stipulations/<int:pk>/",
        views_f_and_i.admin_stipulation_update,
        name="admin-stipulation-update",
    ),
    # ---- Milestone 10 · Increment 5 — Contract + BEPA + Funding API ---
    # Role-gated on the same permission class as M10.1-M10.4
    # (``_M101_PERMS``). Flat URL shape per §1.9.a.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantContractError → 404;
    #   CrossTenantFundingError → 404;
    #   ContractAlreadyVoidedError → 409;
    #   FundingAlreadyExistsError → 409;
    #   ValueError → 400.
    path(
        "admin/contracts/",
        views_f_and_i.admin_contract_create,
        name="admin-contract-create",
    ),
    path(
        "admin/contracts/<int:pk>/",
        views_f_and_i.admin_contract_update,
        name="admin-contract-update",
    ),
    path(
        "admin/back-end-products/",
        views_f_and_i.admin_back_end_product_create,
        name="admin-back-end-product-create",
    ),
    path(
        "admin/funding/",
        views_f_and_i.admin_funding_create,
        name="admin-funding-create",
    ),
    path(
        "admin/funding/<int:pk>/",
        views_f_and_i.admin_funding_update,
        name="admin-funding-update",
    ),
    # ---- Milestone 10 · Increment 6 — Chargeback admin API ------------
    # Role-gated on the same permission class as M10.1-M10.5
    # (``_M101_PERMS``). Flat URL shape per §1.9.a.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantChargebackError → 404;
    #   ValueError → 400.
    path(
        "admin/chargebacks/",
        views_f_and_i.admin_chargeback_create,
        name="admin-chargeback-create",
    ),
    # ---- Milestone 10 · Increment 7 — Compliance + deal-jacket API ----
    # Role-gated on the same permission class as M10.1-M10.6
    # (``_M101_PERMS``). Flat URL shape per §1.9.a.
    # Domain-error mapping in ``views_f_and_i.py``:
    #   CrossTenantComplianceError → 404;
    #   ComplianceAlreadyExistsError → 409;
    #   ValueError → 400.
    path(
        "admin/compliance-records/",
        views_f_and_i.admin_compliance_create,
        name="admin-compliance-create",
    ),
    path(
        "admin/compliance-records/<int:pk>/",
        views_f_and_i.admin_compliance_update,
        name="admin-compliance-update",
    ),
    path(
        "admin/deal-jackets/<int:contract_pk>/",
        views_f_and_i.admin_deal_jacket_read,
        name="admin-deal-jacket-read",
    ),
    path(
        "admin/f-and-i/deals/",
        views_f_and_i.admin_f_and_i_deals_list,
        name="admin-f-and-i-deals-list",
    ),
]
