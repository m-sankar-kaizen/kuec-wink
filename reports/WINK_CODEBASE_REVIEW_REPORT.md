# WINK Codebase Review Report (Re-Verified)

## 1. Executive Summary
This report contains a **fresh, verified re-check** of the actual KUEC WINK Shared Services codebase (`kuec_portal_foundation` and `kuec_service_catalogue`). The conclusions here are explicitly based ONLY on currently implemented models, controllers, and templates.

The re-check confirms that while most of the core logic (bundle entitlements, retainer changes, document compliance, and portal routes) is implemented, there are discrepancies between previous assumptions and the actual code, specifically regarding Dashboard KPIs (which are missing).

## 2. Corrections to Previous Review

| Feature / Workflow | Old Conclusion | New Verified Conclusion | Reason for Correction |
|-------------------|----------------|-------------------------|-----------------------|
| **Dashboard KPIs** | Complete / Assumed | **Missing** | Code scan confirmed no KPI logic or templates exist in the `kuec_service_catalogue` controllers or views. |
| **Plan Selection Bug** | Missing / Buggy | **Verified Fixed** | In `request.py`, plan selection and pricing ID preservation via URL/form kwargs is explicitly handled (v2 recurrence logic) overriding legacy logic. |
| **Payment Gating UX** | Partial | **Partial** | The boolean flag `wink_price_confirmed` works for gating payment, but the frontend UX remains dependent on backend coordinator actions without automated push notifications to the portal. |
| **Portal Tags (UI-TAG)** | Partial / Unverified | **Verified Complete** | `wink_catalogue_page.xml` actively implements `UI-TAG-001` (Diagonal Ribbon) and `UI-TAG-002` (Pill Tags) styling them correctly based on backend colors. |

## 3. Verified Workflow Inventory

| Workflow | Verified Status | Evidence (Files) | Notes |
|----------|-----------------|------------------|-------|
| **Catalogue & Service Detail** | Confirmed Complete | `controllers/catalogue.py`, `request.py`, `wink_catalogue_page.xml` | Browsing, search, filtering, tags, and ribbons successfully implemented. |
| **Request Wizard** | Confirmed Complete | `controllers/request.py`, `request_templates.xml` | Step 1 (choose service), Step 2 (configure params / plan / tier), Step 3 (select employees / WINK bundles) is correctly wired. |
| **My Requests & Request Detail** | Confirmed Complete | `portal.py`, `request.py`, `request_templates.xml` | Portal layout correctly embeds `portal_my_requests`. Detail page shows all required order info, documents, and bundle tracking. |
| **Document Compliance** | Confirmed Complete | `models/kuec_document_submission.py`, `request.py`, Document XMLs | Upload works, integrates with requirements defined dynamically on the product/bundle. |
| **Employee Directory** | Confirmed Complete | `models/kuec_employee_directory.py`, `employee_portal_templates.xml` | Full CRUD operations for portal users, isolated properly. |
| **Bundle Workflows (BND-001/005)** | Confirmed Complete | `models/wink_bundle.py`, `models/wink_bundle_entitlement.py`, `models/sale_order_line.py`, `project_task.py` | Idempotent activation locks, repeated qty-based activations, per-activation document and employee requirements all verified in code. |
| **Retainer Workflows** | Confirmed Complete | `models/kuec_service_request.py`, `request.py`, `services/wink_retainer_change_service.py` | Plan changes, prorations, and cancellation routes are strictly verified to exist and enforce policy. |
| **Support Tickets** | Confirmed Complete | `portal.py`, `helpdesk` integrations | `/my/ticket/new` and `/my/ticket/submit` confirmed implementation. |
| **Dashboard KPIs** | **Confirmed Missing** | N/A | No code for analytic portal widgets has been found. |

## 4. Verified Issue Status

| Issue ID | Status | Evidence | Notes |
|----------|--------|----------|-------|
| **WF-BND-001** (Employees per activation) | Verified Fixed | `project_task.py`, `request.py:1164` | Code actively branches employee mapping dynamically based on activated lines. |
| **WF-BND-002** (Docs per activation) | Verified Fixed | `request.py:1234` | Code checks requirements only against the child service product. |
| **UI-TAG-001/002** | Verified Fixed | `wink_catalogue_page.xml` | Diagonal ribbon on card/detail and pill badges dynamically render backend colors. |
| **UI-BUG-005** (Plan selection) | Verified Fixed | `request.py:872-917` | explicitly maps `selected_pricing_id` protecting against overwrite. |
| **GAP-001** (Multi-Company Bleed) | **Still Open** | `models/wink_bundle.py`, `models/wink_subscription_group.py` | Models still lack `company_id` and strict rule boundaries, verifying the previous architectural review gap. |

## 5. Final Recommended Next Actions

1. **Critical Workflow Bugs**: There are no critical blockers in the verified core workflows (Bundles, Requests, Retainers, Docs). However, GAP-001 (Multi-company bleed on global config objects) requires immediate `company_id` database updates before letting internal coordinators configure global instances.
2. **Security / Multi-Company Risks**: Apply `company_id` and Odoo multi-company record rules to `wink.bundle`, `wink.subscription.group`, and `kuec.service.document`.
3. **Portal User-Facing Gaps**: Build the missing **Dashboard KPIs** for portal users (e.g., Active Retainers, Open Requests, Unpaid Invoices widgets).
4. **Cosmetic / UI Parity**: Improve Payment Gating UX to supply immediate visual feedback (e.g., blocking payment natively using CSS/Alerts instead of only relying heavily on post-submit backend validation).

---

## 6. Re-Verified Issue Status — 2026-03-07

> Second pass code audit performed by handover agent. Corrections and additions below.

| Issue ID | Old Conclusion | New Verified Status | Correction / Evidence |
|----------|---------------|--------------------|-----------------------|
| **WF-BND-001** | Verified Fixed | **Still Verified Done** | `sale_order_line.wink_selected_employee_ids` M2M confirmed. `action_activate(employee_ids=None)` at `wink_bundle_entitlement.py:120` confirmed. `project_task.create` preference chain confirmed at `project_task.py:34-43`. |
| **WF-BND-002** | Verified Fixed | **Still Verified Done** | `_wink_required_docs_approved_for_product()` at `kuec_service_request.py:279` confirmed. Called inside `action_activate()` at line 171. Raises UserError with doc name list. |
| **WF-BND-003** | Verified Fixed | **Still Verified Done** | `project_task.write()` at `project_task.py:70-84` confirmed: scopes doc check to `sale_line.product_id.product_tmpl_id` when `wink_entitlement_id` present. |
| **WF-BND-004** | Verified Fixed | **Still Verified Done** | `bundle_activation_map` computed in `request_detail` at `request.py:1346-1387`. `is_complete` from `stage.fold` or stage name keyword fallback. |
| **WF-BND-005** | Verified Fixed | **Still Verified Done** | No false blocking. SQL atomic update prevents race. Template uses `ent.qty_activated < ent.qty_entitled` condition. |
| **UI-TAG-001/002** | Verified Fixed | **Still Verified Done** | `.wink-ribbon-wrapper` + `.wink-ribbon` in SCSS at lines 299-327. Lambda dedup at `wink_catalogue_page.xml:52, 307`. |
| **WF-BUNDLE-UI-006** | Verified Fixed | **Still Verified Done** | `t-attf-style` at `request_templates.xml:2030`. No unsafe `%` formatting. |
| **WF-BUNDLE-PLAN-002** | Verified Fixed | **Still Verified Done** | `wink.subscription.plan` in model list at `request.py:895`. `is_fake_plan` check at line 1108. `wink_plan_id` priority at `request_detail:1266`. |
| **UI-REV-001** | Not Previously Verified | **STILL OPEN (partial)** | Plan names: visible on service detail (verified). "Compare Plans" HTML link at `request_templates.xml:591-593` — NO matching CSS (grep: no `.wink-compare` in SCSS) and NO JS handler. Functionally inert. Fix: add CSS + JS toggle. |
| **UI-REV-002** | Not Previously Verified | **Verified Done** | `review_display` dict at `request.py:473-559` passes type_label, tier_name, plan_name, price_str, currency_symbol, employee_names. Template at `request_templates.xml:288-349` renders all fields with proper dl/dt/dd layout. |
| **UI-REV-003** | Not Previously Verified | **Enhancement — Not Implemented** | Documented only. Requires product owner approval. Complex implications for hidden-price and bundle flows. |
| **EPIC7-DASH-001** | Confirmed Missing | **Still Missing** | Zero code files reference dashboard KPI. No controller route, no template block, no model computed field for portal dashboard metrics. |
