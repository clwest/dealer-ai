from django.urls import path

from . import (
    views,
    views_accounting,
    views_analytics,
    views_be_backs,
    views_bhph_analytics,
    views_bhph_notes,
    views_bhph_payments,
    views_bhph_promises,
    views_collection_contacts,
    views_deal_writeups,
    views_delivery,
    views_demo_store,
    views_f_and_i,
    views_follow_ups,
    views_leads,
    views_lifecycle,
    views_listings,
    views_photos,
    views_pilot_onboarding,
    views_recon,
    views_repossessions,
    views_sale,
    views_showroom,
    views_test_drives,
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
    # Milestone 25 · Increment 2 (SESSION_187) — tenant vehicle list.
    # Additive endpoint added at M25.2 open to unblock the test-drive
    # form's vehicle picker per MILESTONE_25_PLANNING.md §5.e. Every
    # `admin/vehicles/*` route above M25.2 was stock-scoped; the picker
    # needs a full-inventory fallback for walk-in / phone / referral
    # leads that land with empty `interested_vehicles`.
    path(
        "admin/vehicles/",
        views.admin_vehicle_list,
        name="admin-vehicle-list",
    ),
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
    # ---- Milestone 32 · Increment 1 — F&I intake list endpoint --------
    # Per MILESTONE_32_PLANNING.md §5.b D3. F&I-role-gated (first F&I-
    # role-gated list endpoint). Fail-explicit query validation —
    # invalid `intake`, `lead_id`, or `since` values return 400. Uses
    # `list/` suffix rather than method-dispatching at the same URL as
    # the M10.1 create endpoint above, preserving M10.1's shipped
    # POST-only URL config verbatim per §5.h non-goals.
    path(
        "admin/credit-applications/list/",
        views_f_and_i.admin_credit_application_list,
        name="admin-credit-application-list",
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
    # ---- Milestone 11 · Increment 1 — non-chat lead intake ------------
    # Four write endpoints per MILESTONE_11_PLANNING.md §1.1 + §1.6 + §7
    # M11.1. All four gate on ``IsSalesManagerOrOwnerAtActiveDealership``
    # (M4 permission class, reused unchanged per §1.9). Domain-error
    # mapping in ``views_leads.py``:
    #   UnknownWebhookPlatformError → 400;
    #   CrossTenantReferrerError → 404 (fail-closed);
    #   serializer error → 400.
    # ``CustomerLead.channel`` is set by each verb from a fixed 5+1
    # vocabulary; the M1 chat-funnel intake path at
    # ``POST /leads/`` (line 26) is unchanged and lands with the
    # default ``channel="chat"``.
    path(
        "admin/leads/walk-in/",
        views_leads.admin_lead_walk_in_create,
        name="admin-lead-walk-in-create",
    ),
    path(
        "admin/leads/phone/",
        views_leads.admin_lead_phone_create,
        name="admin-lead-phone-create",
    ),
    path(
        "admin/leads/referral/",
        views_leads.admin_lead_referral_create,
        name="admin-lead-referral-create",
    ),
    path(
        "admin/leads/webhook/",
        views_leads.admin_lead_webhook_create,
        name="admin-lead-webhook-create",
    ),
    # ---- Milestone 11 · Increment 2 — TestDrive admin API -------------
    # One endpoint per MILESTONE_11_PLANNING.md §1.2 + §7 M11.2. Gated
    # on ``IsSalesManagerOrOwnerAtActiveDealership`` (M4 permission
    # class reused, matches M11.1 posture per §1.9).
    # Domain-error mapping in ``views_test_drives.py``:
    #   CrossTenantTestDriveError → 404 (fail-closed);
    #   missing lead / vehicle in tenant → 404;
    #   serializer error → 400.
    path(
        "admin/test-drives/",
        views_test_drives.admin_test_drive_create,
        name="admin-test-drive-create",
    ),
    # M11.6 addendum — read-only list surface for the operator UI.
    path(
        "admin/test-drives/list/",
        views_test_drives.admin_test_drive_list,
        name="admin-test-drive-list",
    ),
    # ---- Milestone 11 · Increment 3 — DealWriteup admin API ------------
    # Three endpoints per MILESTONE_11_PLANNING.md §1.3 + §5.e Option A
    # + §7 M11.3. Gated on ``IsSalesManagerOrOwnerAtActiveDealership``
    # (same posture as M11.1 / M11.2 per §1.9).
    # Domain-error mapping in ``views_deal_writeups.py``:
    #   CrossTenantDealWriteupError → 404 (fail-closed);
    #   WriteupNotApprovedError → 409 (state machine);
    #   WriteupAlreadyHandedOffError → 409 (idempotency);
    #   missing writeup / lead / vehicle in tenant → 404;
    #   serializer error → 400.
    # Handoff endpoint server-side auto-creates a matching M10.1
    # CreditApplication via the existing
    # ``services.f_and_i.record_credit_application`` verb per
    # §5.e Option A + SESSION_116 §0.a M11.3 amendment.
    path(
        "admin/deal-writeups/",
        views_deal_writeups.admin_deal_writeup_create,
        name="admin-deal-writeup-create",
    ),
    path(
        "admin/deal-writeups/<int:pk>/approve/",
        views_deal_writeups.admin_deal_writeup_approve,
        name="admin-deal-writeup-approve",
    ),
    path(
        "admin/deal-writeups/<int:pk>/hand-off/",
        views_deal_writeups.admin_deal_writeup_hand_off,
        name="admin-deal-writeup-hand-off",
    ),
    # ---- Milestone 32 · Increment 1 — DealWriteup read endpoints -------
    # Per MILESTONE_32_PLANNING.md §5.b D1 + D2. Same permission class
    # as M11.3 create/approve/hand-off (``_M113_PERMS``). Fail-explicit
    # query validation on the list endpoint per D1 — invalid `state`
    # or `lead_id` values return 400 rather than silently unfiltering.
    # Distinct URL from the M11.3 create URL: dispatch is by HTTP
    # method (POST creates; GET lists). Detail endpoint is a new URL
    # pattern with pk.
    path(
        "admin/deal-writeups/list/",
        views_deal_writeups.admin_deal_writeup_list,
        name="admin-deal-writeup-list",
    ),
    path(
        "admin/deal-writeups/<int:pk>/",
        views_deal_writeups.admin_deal_writeup_detail,
        name="admin-deal-writeup-detail",
    ),
    # ---- Milestone 11 · Increment 4 — Follow-up cadence admin API ------
    # Five endpoints per MILESTONE_11_PLANNING.md §1.4 + §5.d Option A
    # + §7 M11.4. Gated on ``IsSalesManagerOrOwnerAtActiveDealership``
    # (same posture as M11.1 / M11.2 / M11.3 per §1.9).
    # Domain-error mapping in ``views_follow_ups.py``:
    #   CrossTenantCadenceError / CrossTenantTaskError → 404;
    #   DuplicateActiveCadenceError → 409 (idempotency guard);
    #   UnknownTemplateError → 400;
    #   TaskAlreadyTerminalError → 409 (state machine);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    # Beat orchestrator registered in
    # ``dealer_kit/settings.py::CELERY_BEAT_SCHEDULE`` at 06:00
    # project-time daily. State transitions are operator-triggered
    # only (SESSION_117 §0.a M11.4 decision 3).
    path(
        "admin/follow-up-cadences/",
        views_follow_ups.admin_follow_up_cadence_create,
        name="admin-follow-up-cadence-create",
    ),
    path(
        "admin/follow-up-cadences/<int:pk>/pause/",
        views_follow_ups.admin_follow_up_cadence_pause,
        name="admin-follow-up-cadence-pause",
    ),
    path(
        "admin/follow-up-tasks/",
        views_follow_ups.admin_follow_up_task_list,
        name="admin-follow-up-task-list",
    ),
    path(
        "admin/follow-up-tasks/<int:pk>/complete/",
        views_follow_ups.admin_follow_up_task_complete,
        name="admin-follow-up-task-complete",
    ),
    path(
        "admin/follow-up-tasks/<int:pk>/skip/",
        views_follow_ups.admin_follow_up_task_skip,
        name="admin-follow-up-task-skip",
    ),
    # ---- Milestone 11 · Increment 5 — BeBack admin API ----------------
    # Three endpoints per MILESTONE_11_PLANNING.md §1.5 + §5.g Options
    # A / A / B (recorded in §0.a at SESSION_118 open) + §7 M11.5. Gated
    # on ``IsSalesManagerOrOwnerAtActiveDealership`` (same posture as
    # M11.1-M11.4 per §1.9).
    # Domain-error mapping in ``views_be_backs.py``:
    #   CrossTenantBeBackError → 404;
    #   UnknownReasonError → 400;
    #   BeBackAlreadyTerminalError → 409 (state machine);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    # No-show auto-detector registered in
    # ``dealer_kit/settings.py::CELERY_BEAT_SCHEDULE`` at 07:00
    # project-time daily (grace period configurable via
    # ``BE_BACK_NO_SHOW_GRACE_HOURS``, default 4). Manual override
    # available at the ``mark-no-show`` endpoint.
    path(
        "admin/be-backs/",
        views_be_backs.admin_be_back_create,
        name="admin-be-back-create",
    ),
    # M11.6 addendum — read-only list surface for the operator UI.
    path(
        "admin/be-backs/list/",
        views_be_backs.admin_be_back_list,
        name="admin-be-back-list",
    ),
    path(
        "admin/be-backs/<int:pk>/mark-returned/",
        views_be_backs.admin_be_back_mark_returned,
        name="admin-be-back-mark-returned",
    ),
    path(
        "admin/be-backs/<int:pk>/mark-no-show/",
        views_be_backs.admin_be_back_mark_no_show,
        name="admin-be-back-mark-no-show",
    ),
    # Milestone 12 · Increment 1 (SESSION_121) — BhphNote origination.
    # Domain-error mapping in ``views_bhph_notes.py``:
    #   CrossTenantBhphNoteError → 404;
    #   NonBhphSaleError → 400;
    #   DuplicateBhphNoteError → 409;
    #   UnknownBhphFrequencyError → 400;
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    # Retrieve endpoint returns the note + the computed payment schedule
    # (equal-amount installments derived from
    # ``services.payment_engine.bhph_note_schedule``).
    path(
        "admin/bhph-notes/",
        views_bhph_notes.admin_bhph_note_create,
        name="admin-bhph-note-create",
    ),
    # M12.7 addendum — list surface for the portfolio dashboard.
    path(
        "admin/bhph-notes/list/",
        views_bhph_notes.admin_bhph_note_list,
        name="admin-bhph-note-list",
    ),
    path(
        "admin/bhph-notes/<int:pk>/",
        views_bhph_notes.admin_bhph_note_retrieve,
        name="admin-bhph-note-retrieve",
    ),
    # Milestone 12 · Increment 2 (SESSION_122) — BhphPayment intake.
    # Nested under the note per RESTful convention (a payment always
    # belongs to a note; there is no top-level payment surface).
    # Domain-error mapping in ``views_bhph_payments.py``:
    #   CrossTenantBhphPaymentError → 404;
    #   UnknownPaymentMethodError → 400;
    #   OverpaymentError → 400 (refund/reversal deferred beyond M12);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    path(
        "admin/bhph-notes/<int:pk>/payments/",
        views_bhph_payments.admin_bhph_payment_create,
        name="admin-bhph-payment-create",
    ),
    path(
        "admin/bhph-notes/<int:pk>/payments/list/",
        views_bhph_payments.admin_bhph_payment_list,
        name="admin-bhph-payment-list",
    ),
    # Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay
    # tracking. Two nested-under-note routes for creation + listing;
    # two top-level promise routes for state transitions (mark-kept
    # requires a payment reference per §5.d Option A operator-
    # triggered reconciliation).
    #
    # Domain-error mapping in ``views_bhph_promises.py``:
    #   CrossTenantBhphPromiseError → 404;
    #   UnknownReasonError → 400;
    #   CrossPromisePaymentError → 400;
    #   PromiseAlreadyTerminalError → 409 (state machine);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    path(
        "admin/bhph-notes/<int:pk>/promises/",
        views_bhph_promises.admin_bhph_promise_create,
        name="admin-bhph-promise-create",
    ),
    path(
        "admin/bhph-notes/<int:pk>/promises/list/",
        views_bhph_promises.admin_bhph_promise_list,
        name="admin-bhph-promise-list",
    ),
    path(
        "admin/bhph-promises/<int:pk>/mark-kept/",
        views_bhph_promises.admin_bhph_promise_mark_kept,
        name="admin-bhph-promise-mark-kept",
    ),
    path(
        "admin/bhph-promises/<int:pk>/mark-broken/",
        views_bhph_promises.admin_bhph_promise_mark_broken,
        name="admin-bhph-promise-mark-broken",
    ),
    # Milestone 12 · Increment 5 (SESSION_125) — CollectionContact
    # audit log. Nested under the note per RESTful convention; the
    # paired FDCPA-adjacent scrub layer lives in
    # ``services.llm_safety.apply_post_llm_scrubs`` under
    # ``kind="collection_contact"``.
    #
    # Domain-error mapping in ``views_collection_contacts.py``:
    #   CrossTenantContactError → 404;
    #   UnknownChannelError → 400;
    #   UnknownOutcomeError → 400;
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    path(
        "admin/bhph-notes/<int:pk>/contacts/",
        views_collection_contacts.admin_collection_contact_create,
        name="admin-collection-contact-create",
    ),
    path(
        "admin/bhph-notes/<int:pk>/contacts/list/",
        views_collection_contacts.admin_collection_contact_list,
        name="admin-collection-contact-list",
    ),
    # Milestone 12 · Increment 6 (SESSION_126) — Repossession record.
    # Two nested-under-note routes for creation + listing; two top-
    # level repossession routes for state transitions
    # (mark-re-intaked requires a ConditionReport reference).
    #
    # Domain-error mapping in ``views_repossessions.py``:
    #   CrossTenantRepossessionError → 404;
    #   CrossTenantConditionReportError → 400;
    #   RepossessionAlreadyTerminalError → 409 (state machine);
    #   InvalidStateTransitionError → 409 (state machine);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    path(
        "admin/bhph-notes/<int:pk>/repossessions/",
        views_repossessions.admin_repossession_create,
        name="admin-repossession-create",
    ),
    path(
        "admin/bhph-notes/<int:pk>/repossessions/list/",
        views_repossessions.admin_repossession_list,
        name="admin-repossession-list",
    ),
    path(
        "admin/bhph-repossessions/<int:pk>/mark-recovered/",
        views_repossessions.admin_repossession_mark_recovered,
        name="admin-repossession-mark-recovered",
    ),
    path(
        "admin/bhph-repossessions/<int:pk>/mark-re-intaked/",
        views_repossessions.admin_repossession_mark_re_intaked,
        name="admin-repossession-mark-re-intaked",
    ),
    # Milestone 12 · Increment 7 (SESSION_127) — BHPH portfolio
    # analytics. Single summary endpoint at MVP per §0.a M12.7
    # decision 2. Read-only aggregation over M12.1-M12.4 tables.
    path(
        "admin/bhph/analytics/summary/",
        views_bhph_analytics.admin_bhph_analytics_summary,
        name="admin-bhph-analytics-summary",
    ),
    # Milestone 13 · Increment 1 (SESSION_129) — accounting substrate
    # endpoints per MILESTONE_13_PLANNING.md §7 M13.1 + §5.a Option A
    # + §5.c Option A + §5.e Option A + §5.f Option C (backend-only —
    # operator UI defers to M14). Gated on IsSalesManagerOrOwnerAt
    # ActiveDealership per M12 continuity (permission-class count stays
    # at 8, zero drift).
    #
    # Domain-error mapping in ``views_accounting.py``:
    #   EmptyJournalEntryError / InvalidJournalLineError /
    #   UnbalancedJournalEntryError → 400;
    #   CrossTenantGLAccountError / CrossTenantJournalEntryError → 404
    #   (fail-closed);
    #   ImmutableJournalEntryError → 409 (empty-reason reversal);
    #   missing lookups in-tenant → 404;
    #   serializer error → 400.
    path(
        "admin/accounting/journal-entries/",
        views_accounting.admin_journal_entry_create,
        name="admin-journal-entry-create",
    ),
    path(
        "admin/accounting/journal-entries/<int:pk>/reverse/",
        views_accounting.admin_journal_entry_reverse,
        name="admin-journal-entry-reverse",
    ),
    path(
        "admin/accounting/journal-entries/<int:pk>/",
        views_accounting.admin_journal_entry_retrieve,
        name="admin-journal-entry-retrieve",
    ),
    # Milestone 13 · Increment 3 (SESSION_131) — trial-balance snapshot.
    # Pure recompute per §0.a M13.3 decision 2 (no snapshot entity at
    # M13.3; materialization defers to M14+ close workflow). Optional
    # ?as_of=<ISO8601> query parameter per §0.a M13.3 decision 4.
    # Same permission class as the other M13.1 endpoints.
    path(
        "admin/accounting/trial-balance/",
        views_accounting.admin_trial_balance,
        name="admin-trial-balance",
    ),
    # Milestone 14 · Increment 1 (SESSION_134) — list + failures endpoints
    # per MILESTONE_14_PLANNING.md §7 M14.1 + §5.a Option A (four-surface
    # UI scope) + §5.b Option B (filter-less list — filters land at M15+
    # per operator evidence). Read-only. Same permission class as M13
    # accounting endpoints (zero drift extends to a sixth consecutive
    # milestone). Empty-list responses for zero-portfolio / zero-failure
    # tenants (not 404) per M13.3 §0.a decision 5 zero-portfolio
    # semantics.
    path(
        "admin/accounting/journal-entries/list/",
        views_accounting.admin_journal_entry_list,
        name="admin-journal-entry-list",
    ),
    path(
        "admin/accounting/cost-posting-failures/",
        views_accounting.admin_cost_posting_failures,
        name="admin-cost-posting-failures",
    ),
    # Milestone 17 · Increment 1 (SESSION_145) — trial-balance snapshots.
    # Per MILESTONE_17_PLANNING.md §7 M17.1 + §5.a-§5.f. Three endpoints
    # covering freeze (POST), list (GET), and detail (GET). All reuse
    # ``IsSalesManagerOrOwnerAtActiveDealership`` — zero-drift streak
    # extends to nine consecutive milestones. Detail endpoint uses
    # ``<int:pk>`` per §0.a M17.1 decision 3 (pk is canonical
    # identifier; as_of is a queryable attribute).
    path(
        "admin/accounting/trial-balance/snapshots/",
        views_accounting.admin_trial_balance_snapshot_create,
        name="admin-trial-balance-snapshot-create",
    ),
    path(
        "admin/accounting/trial-balance/snapshots/list/",
        views_accounting.admin_trial_balance_snapshot_list,
        name="admin-trial-balance-snapshot-list",
    ),
    path(
        "admin/accounting/trial-balance/snapshots/<int:pk>/",
        views_accounting.admin_trial_balance_snapshot_retrieve,
        name="admin-trial-balance-snapshot-retrieve",
    ),
    # Milestone 27 · Increment 1 (SESSION_192) — GLAccount list substrate.
    # Per MILESTONE_27_PLANNING.md §5.b M27.1. Reuses
    # ``IsSalesManagerOrOwnerAtActiveDealership`` (zero-drift
    # permission-class streak preserved). Shared accounting
    # infrastructure — the M27.2 JE-create dialog is the immediate
    # consumer; future accounting workflows (recurring journals,
    # adjustments, budgets, statement recon, F&I chargebacks,
    # period-open) reuse the same substrate.
    path(
        "admin/accounting/gl-accounts/",
        views_accounting.admin_gl_account_list,
        name="admin-gl-account-list",
    ),
    # Milestone 28 · Increment 1 (SESSION_195) — journal-entry templates.
    # Per MILESTONE_28_PLANNING.md §5.b M28.1. Two verbs (GET list +
    # POST create) under one URL via @api_view(["GET", "POST"]).
    # Reuses ``IsSalesManagerOrOwnerAtActiveDealership`` (zero-drift
    # permission-class streak preserved at 27 → 28 intended). Templates
    # are recipes for recurring journal entries — instantiation flows
    # through the existing M13.1 POST admin/accounting/journal-entries/
    # endpoint pre-populated by the M28.2 dialog.
    path(
        "admin/accounting/journal-entry-templates/",
        views_accounting.admin_journal_entry_template_list_or_create,
        name="admin-journal-entry-template-list-or-create",
    ),
    # Milestone 30 · Increment 1 (SESSION_201) — template detail
    # endpoint supporting PATCH (full-replace edit) + DELETE (soft
    # — sets is_active=False). Per MILESTONE_30_PLANNING.md §5.b
    # D1. Reuses _M131_PERMS (zero-drift permission-class streak
    # preserved at 29 → 30 intended at M30.1 → 31 intended at
    # M30.2). No GET at M30 — the edit-mode dialog populates from
    # the existing list response's projection.
    path(
        "admin/accounting/journal-entry-templates/<int:pk>/",
        views_accounting.admin_journal_entry_template_detail,
        name="admin-journal-entry-template-detail",
    ),
    # Milestone 31 · Increment 1 (SESSION_204) — template restore
    # endpoint. POST reactivates a soft-hidden template by setting
    # is_active = True; idempotent on already-active rows. Per
    # MILESTONE_31_PLANNING.md §5.b D1–D2. Reuses _M131_PERMS
    # (zero-drift permission-class streak preserved at 31 → 32
    # intended at M31.1). Endpoint-shape precedent:
    # admin/vehicle-photos/<uuid:public_id>/restore/ (M21 audit
    # endpoint #68).
    path(
        "admin/accounting/journal-entry-templates/<int:pk>/restore/",
        views_accounting.admin_journal_entry_template_restore,
        name="admin-journal-entry-template-restore",
    ),
    # Milestone 18 · Increment 5 (SESSION_151) — TesterFeedback POST.
    # Per MILESTONE_18_PLANNING.md §7 M18.5 + §5.e Option A. Reuses
    # ``IsSalesManagerOrOwnerAtActiveDealership`` (zero-drift streak
    # extends to fourteen consecutive milestones). Refuses submissions
    # against a non-demo Dealership per §5.g Option A guard.
    path(
        "admin/demo-store/feedback/",
        views_demo_store.admin_demo_store_feedback_create,
        name="admin-demo-store-feedback-create",
    ),
    # Milestone 19 · Increment 3 (SESSION_156) — pilot onboarding admin.
    # Per MILESTONE_19_PLANNING.md §7 M19.3 + §0.a M19.3 decisions:
    # (1) inventory-import endpoint deferred to M19.4 alongside its
    # frontend consumer; (2) gated on IsAuthenticated alone (zero-drift
    # permission-class streak extends to seventeen consecutive milestones).
    path(
        "admin/pilots/create/",
        views_pilot_onboarding.admin_pilot_create,
        name="admin-pilot-create",
    ),
    path(
        "admin/pilots/",
        views_pilot_onboarding.admin_pilot_list,
        name="admin-pilot-list",
    ),
    path(
        "admin/pilots/<slug:slug>/checklist/advance/",
        views_pilot_onboarding.admin_pilot_checklist_advance,
        name="admin-pilot-checklist-advance",
    ),
    # Milestone 19 · Increment 4 (SESSION_157) — pilot inventory import
    # endpoint deferred from M19.3 per §0.a M19.3 decision 1; ships
    # with its M19.4 frontend consumer.
    path(
        "admin/pilots/<slug:slug>/inventory/import/",
        views_pilot_onboarding.admin_pilot_inventory_import,
        name="admin-pilot-inventory-import",
    ),
    path(
        "admin/pilots/<slug:slug>/terminate/",
        views_pilot_onboarding.admin_pilot_terminate,
        name="admin-pilot-terminate",
    ),
]
