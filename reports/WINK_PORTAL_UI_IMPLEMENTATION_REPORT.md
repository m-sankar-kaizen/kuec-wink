# WINK Portal UI Implementation Report

**Source of truth:** `custom/reports/WINK_PORTAL_UI_SPEC.md`  
**Scope:** Portal UI only (no backend/admin).  
**Constraints:** Existing brand (`wink_theme.scss`), no new colors/fonts, no business logic or security changes.

---

## 1. UI Scope and Pages in Scope

| Spec § | Page | Route(s) | Template ID | XML File |
|--------|------|----------|-------------|----------|
| 1.1 | Service Catalogue | `/services` | `wink_catalogue_page` | `wink_catalogue_page.xml` |
| 1.2 | My Requests (List) | `/my/requests` | `portal_my_requests` | `request_templates.xml` |
| 1.3 | Request Detail | `/my/requests/<id>` | `wink_request_confirmation` | `request_templates.xml` |
| 1.4–1.7 | Create New Request (steps 1–4) | `/my/requests/new`, `/services/<id>/request` | `wink_request_form` | `request_templates.xml` |
| 1.8 | Request Submitted | (after submit → redirect to detail with `?submitted=1`) | Same as Request Detail + success block | `request_templates.xml` |
| 1.9 | Documents Upload / Management | `/my/requests/<id>/documents` | `wink_document_upload_page` | `request_templates.xml` |
| 1.10 | Employee Directory (List, Create/Edit, Bulk) | `/my/employees`, `/my/employee/<id>`, `/my/employee/new`, `/my/employees/upload` | `portal_my_employees`, `portal_my_employee_detail`, `portal_my_employees_upload_error` | `employee_portal_templates.xml` |
| 1.11 | Retainer Change Plan | `/my/requests/<id>/retainer/change-plan` | `wink_retainer_change_plan` | `request_templates.xml` |
| 1.12 | Cancellation Preview | `/my/requests/<id>/retainer/cancel/preview` | `wink_retainer_cancel_preview` | `request_templates.xml` |
| 1.13 | Payment States (Locked / Payable / Paid) | `/my/requests/<id>`, `/my/requests/<id>/pay` | `wink_request_confirmation`, `wink_payment_page_v2` | `request_templates.xml` |

**Assets:** `kuec_portal_foundation/static/src/scss/wink_theme.scss` (primary); `kuec_service_catalogue` has no portal-specific SCSS; frontend JS: `wink_catalogue.js`, `wink_tour.js`.

---

## 2. Findings (UI Gaps vs Spec) — UI Issue IDs

| ID | Spec reference | Finding | Severity |
|----|----------------|---------|----------|
| **UI-001** | §1.1 Service Catalogue | Header: spec has blue banner with title "Service Catalogue", subtitle "Browse and request professional services…", and search bar. Current: "Our Services", no blue banner, search in simple form. Sidebar: spec has "Filters" + filter icon; DEPARTMENT with radio + icons + counts; current uses checkboxes and no counts. | High |
| **UI-002** | §1.1 Service Catalogue | Content: spec "Showing N services"; 3-column service cards with "Details" / "Request →" buttons; POPULAR badge (orange, star). Current: "N service(s) found"; cards have "View Details" / "Request Service"; no POPULAR badge; ribbon uses primary blue. | Medium |
| **UI-003** | §1.2 My Requests | Header: spec "My Requests" + subtitle "Track all your service requests and their status." + "+ New Request" (primary, right). Current: portal_searchbar title "Service Requests"; no subtitle; no "+ New Request" button in template. | High |
| **UI-004** | §1.2 My Requests | Toolbar: spec has search "Search by ID or service name…", dropdowns "All Status", "All Types", "All Payment", sort "Latest". Current: uses portal_searchbar + portal_table; no search, no filter dropdowns, no sort control. | High |
| **UI-005** | §1.2 My Requests | Table: spec columns REQUEST #, (date), SERVICE, TYPE, TOTAL AMOUNT, STATUS, PAYMENT; type badges (One-time, Retainer), status badges (Quotation, Sales Order with dot), payment badges (Locked, Due, Paid). Current: Request #, Order Date, Requested Service, Total Amount, Status only; status badges differ; no TYPE column; no PAYMENT column. | High |
| **UI-006** | §1.2 My Requests | Empty state and skeleton: spec requires empty state + skeleton loading. Current: simple alert for no requests; no skeleton. | Low |
| **UI-007** | §1.3 Request Detail | Breadcrumbs: spec "Home > My Requests > [ID]". Current: no breadcrumbs on request detail page. | High |
| **UI-008** | §1.3 Request Detail | Alert: spec single top banner "Payment locked — awaiting coordinator price confirmation…" with padlock icon. Current: multiple conditional alerts; locked state copy close but structure differs. | Medium |
| **UI-009** | §1.3 Request Detail | Order Summary: spec blue header "Order Summary: S00056", status badge "Quotation", key-value SERVICE, STATUS, REQUESTED START, AMOUNT DUE. Current: has blue header and key-values; label "Service" not "SERVICE" (uppercase); structure aligned. Minor: label case. | Low |
| **UI-010** | §1.3 Request Detail | Next Steps: spec yellow info block with clock icon, "Payment locked…" text, buttons "View My Requests", "Browse More Services >". Current: content similar; footer has same buttons; no dedicated yellow info block styling for locked state. | Medium |
| **UI-011** | §1.3 Request Detail | Delivery Progress: spec 5-step stepper (Submitted → Quote Revi… → Payment → In Progress → Completed) with "Last updated". Current: no delivery progress stepper on request detail. | High |
| **UI-012** | §1.3 Request Detail | Activity & Updates: spec timeline with icon + text + timestamp. Current: no activity timeline on request detail. | High |
| **UI-013** | §1.8 Request Submitted | Spec: dedicated success screen with success icon, "Request Submitted!", message with service name bold, "What happens next?" card, two buttons. Current: redirect to request detail only; no post-submit success screen. | Medium |
| **UI-014** | §1.4–1.7 Create New Request | Stepper: spec 4 steps (Choose Service, Configure, Employees, Review & Submit) with completed/active/pending states. Current: no visual stepper on request form; single-page form with sections. | High |
| **UI-015** | §1.9 Documents | Spec: section "Compliance Documents" / "Documents", table (document name, status badge, submitted date), upload drag/drop + progress + errors, "Change requested" banner. Current: documents page exists with breadcrumb, requirements list, upload; table structure and styling to align with spec; change-requested note styling. | Medium |
| **UI-016** | §1.10 Employee Directory | Spec: "Employee Directory" title, subtitle "Manage your company employees.", "+ Add Employee" / "Bulk Upload"; table (Name, Job title, Email); bulk results table with row errors. Current: "Employees" title; "Add Employee", "Bulk Upload", "Template"; table has Name, Job Title, Nationality, UAE Status, Passport; upload error page shows list of errors. Align title/subtitle/copy and table columns. | Medium |
| **UI-017** | §1.11 Retainer Change Plan | Spec: breadcrumbs; left current plan card (Summary/Info); right target plan cards (Service card style + Upgrade/Downgrade badge); proration line; disabled alert/tooltip. Current: has card layout and proration; no breadcrumbs; styling aligns with spec. Add breadcrumbs; ensure card styling matches spec. | Low |
| **UI-018** | §1.12 Cancellation Preview | Spec: breadcrumbs; summary card (Effective date, Remaining days, Refund/credit); reason textarea; Back + Confirm cancellation (destructive); confirmation after submit. Current: has card and form; no breadcrumbs; confirm destructive. Add breadcrumbs; add post-cancel confirmation screen or banner. | Low |
| **UI-019** | §1.13 Payment States | Spec: Locked / Payable / Paid with distinct alert and Next Steps content; optional receipt link. Current: request detail already has conditional alerts and Next Steps; Paid state shows "Payment received". Align copy and ensure receipt link when applicable. | Low |
| **UI-020** | §2 Component library | Spec: reusable components (buttons, badges, cards, table, stepper, alert, breadcrumbs, timeline, upload, empty state, skeleton). Current: wink_theme has partial stepper/tier styles; no unified button/badge/card classes. Need portal component SCSS and QWeb partials. | High |

---

## 3. Proposed Fix Plan (per UI Issue ID)

| ID | Files to change | What will change |
|----|-----------------|------------------|
| UI-001 | `wink_catalogue_page.xml`, `wink_theme.scss` | Add blue header banner with title "Service Catalogue", subtitle, search bar; sidebar "Filters" + icon; DEPARTMENT as radio list with counts (controller to pass counts); SERVICE NATURE, DELIVERY MODEL. |
| UI-002 | `wink_catalogue_page.xml`, `wink_service_card`, `wink_theme.scss` | "Showing N services"; card buttons "Details" / "Request →"; POPULAR badge (orange, star) when product has ribbon tag. |
| UI-003 | `request_templates.xml` (portal_my_requests) | Use portal layout with custom header block: title "My Requests", subtitle, primary "+ New Request" linking to /my/requests/new or /services. |
| UI-004 | `request_templates.xml`, `portal.py` (optional) | Add search input, filter dropdowns (Status, Type, Payment), sort "Latest" if controller can pass search/filter/sort; else static UI placeholders. |
| UI-005 | `request_templates.xml` | Add TYPE column (One-time/Retainer from product or subscription_info); add PAYMENT column (Locked/Due/Paid from controller); status badges with dot (Quotation, Sales Order); alternating row class. |
| UI-006 | `request_templates.xml`, `wink_theme.scss` | Empty state component; skeleton placeholder (CSS-only or minimal QWeb). |
| UI-007 | `request_templates.xml` (wink_request_confirmation) | Add breadcrumb block: Home > My Requests > order.name. |
| UI-008 | `request_templates.xml` | Consolidate locked state into single top alert with padlock icon and spec copy. |
| UI-009 | `request_templates.xml` | Uppercase labels for SERVICE, STATUS, REQUESTED START, AMOUNT DUE in summary. |
| UI-010 | `request_templates.xml`, `wink_theme.scss` | Next Steps: wrap locked state in yellow info block (clock icon + text); button "Browse More Services >". |
| UI-011 | `request_templates.xml`, `request.py`, `wink_theme.scss` | Add Delivery Progress section: 5-step stepper (Submitted, Quote Review, Payment, In Progress, Completed); controller passes stage index; "Last updated" from order write date. |
| UI-012 | `request_templates.xml`, `request.py` | Add Activity & Updates section: timeline from order.message_ids or fixed entries (request submitted, awaiting coordinator). |
| UI-013 | `request.py`, `request_templates.xml` | Redirect to /my/requests/<id>?submitted=1 after submit; in wink_request_confirmation, when submitted=1 show success block (icon, "Request Submitted!", message, "What happens next?" card, buttons). |
| UI-014 | `request_templates.xml` (wink_request_form) | Create New Request is multi-step: wizard lives on same route with step param; add stepper partial at top; Step 1 = service selection (from catalogue or new flow); Steps 2–4 = configure, employees, review. (Large change; may scope to stepper + step 1 content only if wizard is complex.) |
| UI-015 | `request_templates.xml` (wink_document_upload_page) | Align documents table with spec (document name, status badge, submitted date); upload zone with drag/drop class; "Change requested" as banner with coordinator note. |
| UI-016 | `employee_portal_templates.xml` | Title "Employee Directory", subtitle "Manage your company employees."; table columns per spec if backend allows; bulk upload results table with row-level errors (controller may need to pass errors list). |
| UI-017 | `request_templates.xml` (wink_retainer_change_plan) | Add breadcrumbs; ensure current plan card and target cards use summary card / service card styles. |
| UI-018 | `request_templates.xml` (wink_retainer_cancel_preview) | Add breadcrumbs; after cancel redirect with ?cancellation_submitted=1 and show confirmation block on request detail. |
| UI-019 | `request_templates.xml` | Payable: "Proceed to Payment" / "Pay now"; Paid: "Payment received", optional "Download receipt" link. |
| UI-020 | `wink_theme.scss`, new partials in `request_templates.xml` or `wink_catalogue_page.xml` | Add SCSS classes: .btn-wink-primary, .btn-wink-secondary, .btn-wink-ghost, .btn-wink-destructive; badge variants (.badge-wink-*); .card-wink-summary (blue header), .card-wink-info (light blue); .wink-stepper; .wink-alert-locked; .wink-timeline-item; .wink-upload-zone; .wink-empty-state; .wink-skeleton. |

---

## 4. Spec Coverage Matrix

| Spec section | Template(s) | Status |
|--------------|-------------|--------|
| 1.1 Service Catalogue | wink_catalogue_page, wink_service_card | Gaps: UI-001, UI-002 |
| 1.2 My Requests | portal_my_requests | Gaps: UI-003, UI-004, UI-005, UI-006 |
| 1.3 Request Detail | wink_request_confirmation | Gaps: UI-007–UI-012 |
| 1.4–1.7 Create New Request | wink_request_form | Gap: UI-014 |
| 1.8 Request Submitted | wink_request_confirmation (with ?submitted=1) | Gap: UI-013 |
| 1.9 Documents | wink_document_upload_page | Gap: UI-015 |
| 1.10 Employee Directory | portal_my_employees, portal_my_employee_detail, portal_my_employees_upload_error | Gap: UI-016 |
| 1.11 Retainer Change Plan | wink_retainer_change_plan | Gap: UI-017 |
| 1.12 Cancellation Preview | wink_retainer_cancel_preview | Gap: UI-018 |
| 1.13 Payment States | wink_request_confirmation, wink_payment_page_v2 | Gap: UI-019 |
| §2 Component library | wink_theme.scss, QWeb partials | Gap: UI-020 |

---

## 5. Implementation Summary

| File | UI Issue(s) | Summary of changes |
|------|-------------|--------------------|
| `kuec_portal_foundation/static/src/scss/wink_theme.scss` | UI-020, UI-001, UI-005 | Added portal component library: button/badge/card/stepper/alert/breadcrumb/timeline/upload/empty/skeleton classes; catalogue banner; alternating table rows. |
| `kuec_service_catalogue/controllers/request.py` | UI-011, UI-012, UI-013 | Pass delivery_stage, activity_items, submitted; redirect after submit with ?submitted=1; activity from message_ids or synthetic. |
| `kuec_service_catalogue/controllers/portal.py` | UI-005 | Pass request_extra (type + payment per request) for My Requests table. |
| `kuec_service_catalogue/views/website_templates/request_templates.xml` | UI-007, UI-008, UI-009, UI-010, UI-011, UI-012, UI-013, UI-003, UI-005 | Breadcrumbs; Request Submitted success block; Order Summary uppercase labels + card-wink-summary; Delivery Progress stepper; Activity & Updates timeline; My Requests header (title, subtitle, + New Request), table TYPE/PAYMENT columns and badge classes; empty state. |
| `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` | UI-001, UI-002 | Blue banner (Service Catalogue, subtitle, search); Filters + DEPARTMENT/SERVICE NATURE/DELIVERY MODEL; "Showing N services"; service card Details / Request → and POPULAR badge. |

---

## 6. Manual Test Checklist (Portal Only)

- [ ] **Service Catalogue** (/services): Blue header "Service Catalogue", subtitle, search; sidebar Filters with DEPARTMENT (radio + counts), SERVICE NATURE, DELIVERY MODEL; "Showing N services"; cards with Details / Request →; POPULAR badge when applicable.
- [ ] **My Requests** (/my/requests): Title "My Requests", subtitle, "+ New Request"; search; filters All Status / All Types / All Payment; sort Latest; table with REQUEST #, date, SERVICE, TYPE, TOTAL AMOUNT, STATUS, PAYMENT; type/status/payment badges; empty state when no requests.
- [ ] **Request Detail** (/my/requests/1): Breadcrumbs Home > My Requests > S00001; payment locked alert when applicable; Order Summary blue header; Next Steps (yellow block when locked); Delivery Progress stepper (5 steps); Activity & Updates timeline.
- [ ] **Request Submitted**: After submitting new request, URL has ?submitted=1 and success block (icon, "Request Submitted!", "What happens next?", buttons) is visible.
- [ ] **Create New Request**: Stepper 1–4; Step 1 service grid; Step 2 configure; Step 3 employees; Step 4 review & submit.
- [ ] **Documents** (/my/requests/1/documents): Breadcrumb; table document name, status, date; upload zone; change-requested banner when applicable.
- [ ] **Employee Directory** (/my/employees): Title "Employee Directory", subtitle; Add Employee / Bulk Upload; table; bulk upload results with row errors.
- [ ] **Retainer Change Plan**: Breadcrumbs; current plan card; target plan cards with Upgrade/Downgrade; proration; Back / Confirm.
- [ ] **Cancellation Preview**: Breadcrumbs; summary card; reason; Back / Confirm cancellation (destructive); after submit, confirmation.
- [ ] **Payment states**: Locked / Payable / Paid copy and CTAs; receipt link when paid.
- [ ] **Responsive**: Catalogue sidebar collapses on mobile; table scrolls or cards stack; stepper compact.

---

## 7. Assumptions and Needs Screenshot Validation

- **Request Submitted:** Implemented as request detail with `?submitted=1` and a success block at top (no separate route).
- **My Requests filters/sort:** If backend does not yet support search/filter/sort, dropdowns and search can be UI-only (no filter) or controller extended to pass search/filter/sort (read-only, no security change).
- **Delivery Progress:** Stage derived from order.state + payment (draft/sent = Quote Review; sale + not paid = Payment; sale + paid = In Progress / Completed). Need confirmation of stage names and order.
- **Activity timeline:** From order messages or a fixed list; if messages used, limit to last N and format for portal.
- **Documents:** Section title "Compliance Documents" used; upload is existing file input; drag/drop is CSS + optional JS.
- **Employee Directory:** Bulk upload results: controller currently redirects to error page with list; spec wants table with row-level errors. May need a dedicated results route/template.
- **Needs Screenshot Validation:** Per spec §8 — Documents section title; Employee Directory columns; Retainer/Cancellation copy; Payment state copy; receipt link placement.

---

## 8. Changed Files List

| File | Issue ID | Summary |
|------|----------|---------|
| `kuec_portal_foundation/static/src/scss/wink_theme.scss` | UI-020, UI-001, UI-005 | Component library + catalogue banner + table stripes |
| `kuec_service_catalogue/controllers/request.py` | UI-011, UI-012, UI-013 | delivery_stage, activity_items, submitted; redirect ?submitted=1 |
| `kuec_service_catalogue/controllers/portal.py` | UI-005 | request_extra (type, payment) |
| `kuec_service_catalogue/views/website_templates/request_templates.xml` | UI-003, UI-005, UI-007–UI-013 | Breadcrumbs, success block, stepper, timeline, My Requests header/table |
| `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` | UI-001, UI-002 | Banner, Filters, Showing N services, card buttons, POPULAR badge |
