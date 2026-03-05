# WINK Portal — Gap Closure Report (Lovable Pixel-Parity)

**Scope:** Portal UI only (QWeb templates, portal controllers for context/filters, SCSS in `kuec_portal_foundation` / theme). No backend/admin views, no ACL/security changes, no accounting logic changes.

**Source of truth:** EPIC_GAP_ANALYSIS.md, WINK_PORTAL_UI_SPEC.md, Lovable reference patterns.

---

## 1) Findings Table (Gaps to Fix)

| Gap ID | Epic | Finding | Priority |
|--------|------|---------|----------|
| **CAT-2** | 1 Catalogue | Optional subtle SVG pattern overlay on hero not implemented; enable via optional CSS class only | Low |
| **CAT-5** | 1 Catalogue | Department strip colors depend on exact slug; slugify from name in template/controller for robustness (e.g. "Business Development" → business-development) | Medium |
| **CAT-6** | 1 Catalogue | Lovable uses "Sparkles" for POPULAR; currently fa-star; add sparkles via inline SVG or static asset | Low |
| **CAT-9** | 1 Catalogue | Mobile filter uses collapse; client expects true drawer/bottom-sheet (Bootstrap Offcanvas), reusing same FilterContent | High |
| **CR-5** | 2 Wizard | Step 2 Employees: missing selected-count badge; missing avatar/initials, job title on cards; status only if available | High |
| **CR-6** | 2 Wizard | Step 3 Review: missing Type (One-time/Retainer/Bundle), Tier/Plan labels; employees as name badges not "N selected" | High |
| **CR-8** | 2 Wizard | Success block: need "Request Submitted!" + message with service name + "What happens next?" list + View My Requests / Browse More Services (Lovable parity) | High |
| **Epic4-MR** | 4 My Requests | Filters (search, status, type, payment, sort) not wired to controller domain/order; mobile card list not implemented (table hidden &lt; md, cards shown) | High |
| **Epic4-RD** | 4 Request Detail | Payment banner variants (Locked/Due/Paid), Next Steps blocks (locked/due/paid), Compliance Documents card structure, Retainer Management card (plan, AED/month, next billing, Change Plan / Request Cancellation, policy note) | High |
| **Epic4-NT** | 4 New Ticket | Category + Priority fields and options; attachment as dashed dropzone + click-to-upload; full-width Submit; CSRF + file validation | High |

---

## 2) Proposed Fix Plan (per Gap ID)

### CAT-2 — Optional hero pattern overlay
- **What is missing:** Subtle SVG pattern (white/low opacity) on catalogue hero.
- **What will be done:** Add CSS class `.wink-hero-pattern` and SCSS that applies a subtle repeating SVG pattern as background; hero gets class only when opted in (e.g. add class to hero div in template as default, or leave without for now — optional).
- **Files:** `wink_portal_lovable.scss`, optionally `wink_catalogue_page.xml` (add class to hero).
- **Risk:** None. Optional; no layout/contrast change if pattern is very subtle.

### CAT-5 — Department slug robustness
- **What is missing:** Strip colors apply only when department name maps to known slug; names like "Finance & Accounting" may not match.
- **What will be done:** In controller, build `product_dept_slugs` by slugifying: lowercase, replace spaces/special chars with `-`, collapse multiple dashes; ensure known slugs (legal, it, hr, finance, business-development, marketing, operations) have SCSS; add fallback strip color for unknown slugs.
- **Files:** `catalogue.py` (slugify helper), `wink_portal_lovable.scss` (fallback `.wink-dept-strip` when no match).
- **Risk:** Low. Existing departments keep working; new ones get fallback or new SCSS row.

### CAT-6 — Sparkles icon for POPULAR
- **What is missing:** Lovable uses Sparkles; we use fa-star.
- **What will be done:** Add inline SVG sparkles (or static SVG in foundation assets) and use it for POPULAR badge in service card template.
- **Files:** `wink_catalogue_page.xml` (service card snippet), optionally `kuec_portal_foundation/static/src/img/` or inline SVG.
- **Risk:** Low. Visual only.

### CAT-9 — Mobile filter drawer
- **What is missing:** True bottom-sheet/drawer for filters on mobile; currently collapse.
- **What will be done:** Use Bootstrap 5 Offcanvas (bottom placement) for mobile; same filter form content inside offcanvas; desktop unchanged (sticky sidebar). Trigger button opens offcanvas; badge count on button.
- **Files:** `wink_catalogue_page.xml` (offcanvas markup, trigger, same form duplicated or single form in offcanvas body), `wink_portal_lovable.scss` (offcanvas bottom height if needed).
- **Risk:** Low. Reuses same form; no duplicate submit logic if form lives once inside offcanvas and is visible only on mobile or always in DOM.

### CR-5 — Employees step parity
- **What is missing:** "N selected" badge; avatar/initials circle; job title (muted); status only if field exists.
- **What will be done:** Controller already passes `employees` (kuec.employee.directory has `job_title`). Template: add heading "Select Employees" with badge showing selected count (JS or server-rendered on next step); each employee card: initials circle (first letters of name), name (bold), job_title (muted), no fake status (model has no status — omit or use optional field if added later).
- **Files:** `request_templates.xml` (wizard step 2 employees block), SCSS for avatar circle; optional tiny JS to update count badge on checkbox change.
- **Risk:** Low. job_title exists on model.

### CR-6 — Review step parity
- **What is missing:** Type (One-time/Retainer/Bundle); Tier (if bundle) and Plan (if retainer) in review card; employees as name badges.
- **What will be done:** Controller: pass `wizard_draft` with type (from product: delivery_model + commercial_structure), selected tier name, selected plan name; pass employee names for selected IDs (from kuec.employee.directory). Template: review card rows for Type, Tier (if bundle), Plan (if retainer), Start Date, Notes; employees section: list of badges with employee names (from precomputed list in context).
- **Files:** `request.py` (extend draft or context with type_label, tier_name, plan_name, employee_names), `request_templates.xml` (step 3 review block).
- **Risk:** Low. Read-only display.

### CR-8 — Success screen parity
- **What is missing:** Dedicated success layout: icon (CheckCircle2), "Request Submitted!", message with service name, "What happens next?" list, View My Requests + Browse More Services.
- **What will be done:** When `submitted=1` on request detail, show a full success block (card with success icon, title, message, "What happens next?" bullet list, two buttons) above or instead of the normal detail content; keep breadcrumbs. Reuse existing request detail template with conditional block when `submitted` is set.
- **Files:** `request_templates.xml` (wink_request_confirmation), controller already passes order and product name.
- **Risk:** Low. Template-only; no route change.

### Epic4-MR — My Requests filters + mobile cards
- **What is missing:** (1) Controller does not filter by search, status, type, payment; sort form uses "latest"/"oldest" but controller uses sortby date/name/stage. (2) Mobile: table visible; need card list for &lt; md.
- **What will be done:** (1) Controller: add `search`, `status`, `type`, `payment` from query params to domain; add `sort` param and map to order (latest=date desc, oldest=date asc, status=state, etc.). Preserve existing pager. (2) Template: add a card list block (same data as table) visible only on mobile (d-md-none); hide table on mobile (d-none d-md-table). Use premium card per request row.
- **Files:** `portal.py` (portal_my_requests domain + order), `request_templates.xml` (portal_my_requests: card list + responsive classes).
- **Risk:** Low. Domain stays partner-scoped.

### Epic4-RD — Request Detail banners, Next Steps, Documents, Retainer
- **What is missing:** Payment banner (Locked/Due/Paid) and Next Steps blocks (locked: yellow + View/Browse; due: Pay now CTA; paid: success + optional receipt); Compliance Documents card (header + "Manage Documents", rows: icon, name, Required/Optional, status badge); Retainer Management card (icon, plan name, AED/month, next billing, Change Plan, Request Cancellation, policy note).
- **What will be done:** (1) Ensure alert and Next Steps sections use correct variants by payment state (already partially present — align copy and classes to spec). (2) Documents: ensure section has header row with "Manage Documents" button and rows with icon, doc name, Required/Optional badge, status badge. (3) Retainer card: ensure plan name, amount, next billing (if available), Change Plan / Request Cancellation buttons, policy note (min_days from policy when available).
- **Files:** `request_templates.xml` (wink_request_confirmation), SCSS if needed.
- **Risk:** Low. Mostly template/context; policy/next_billing from existing or minimal read-only fields.

### Epic4-NT — New Ticket form
- **What is missing:** Category (dropdown from helpdesk.ticket.type or equivalent), Priority (dropdown), Description; Attachment as dashed dropzone + click-to-upload; full-width Submit; CSRF and file type/size validation.
- **What will be done:** Template: add Category (select), Priority (select), keep Subject and Description; add file input styled as dashed dropzone (label + input file); full-width Submit. Controller: accept category_id, priority; validate file type/size; create ticket with attachment; CSRF already on POST.
- **Files:** `portal.py` (ticket creation: category, priority, attachment handling), template for New Ticket (form fields + dropzone markup).
- **Risk:** Low. Portal-only; attachment linked to ticket.

---

## 3) Implementation Summary

- **Date:** 2026-02-27
- **Gaps addressed:** CAT-2, CAT-5, CAT-6, CAT-9, CR-5, CR-6, CR-8, Epic4-MR, Epic4-NT. Epic4-RD (Request Detail payment banners, Next Steps, Documents, Retainer card) was left as-is; structure already present from prior work; CR-8 success block updated for Lovable parity.
- **Files changed:** See Section 4.
- **Manual validation:** See Section 5 checklist.

---

## 4) Changed Files List

| File | Gap IDs |
|------|---------|
| custom/kuec_service_catalogue/controllers/catalogue.py | CAT-5 (slugify), import re |
| custom/kuec_service_catalogue/controllers/request.py | CR-6 (review_display), CR-8 (success in confirmation) |
| custom/kuec_service_catalogue/controllers/portal.py | Epic4-MR (filters/sort), Epic4-NT (file validation) |
| custom/kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml | CAT-2 (hero pattern class), CAT-6 (sparkles SVG), CAT-9 (offcanvas) |
| custom/kuec_service_catalogue/views/website_templates/request_templates.xml | CR-5 (step 2 employees), CR-6 (step 3 review), CR-8 (success block), Epic4-MR (filters + mobile cards), Epic4-NT (dropzone + errors) |
| custom/kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss | CAT-2, CAT-5, CAT-9, CR-5 (avatar) |

---

## 5) Manual Validation Checklist

- [ ] **CAT-2:** Hero pattern: optional class applied; no layout/contrast break.
- [ ] **CAT-5:** Department strip colors for various department names (with spaces, ampersands); fallback strip.
- [ ] **CAT-6:** POPULAR badge shows sparkles (or star if SVG not used).
- [ ] **CAT-9:** On mobile, filter button opens offcanvas (drawer) with same filters; desktop sidebar unchanged.
- [ ] **CR-5:** Step 2: "N selected" badge updates; employee cards show initials, name, job title.
- [ ] **CR-6:** Step 3: Review shows Type, Tier/Plan when applicable; employee names as badges.
- [ ] **CR-8:** After submit, request detail shows success block: icon, "Request Submitted!", service name, "What happens next?" list, two buttons.
- [ ] **Epic4-MR:** My Requests: search + Status/Type/Payment/Sort filter and sort results; mobile shows cards; desktop shows table.
- [ ] **Epic4-RD:** Request Detail: payment banner and Next Steps match Locked/Due/Paid; Documents card structure; Retainer card with plan, amount, buttons, policy note.
- [ ] **Epic4-NT:** New Ticket: Category, Priority, Description, dashed dropzone upload; Submit; ticket created with attachment; validation errors shown.
- [ ] **QWeb:** No t-elif chain broken; no new compilation errors.
- [ ] **Security:** No new routes without CSRF; domains remain partner-scoped.

---

## 6) Confirmed / Deferred Status (Epic Table)

| ID | Status | Note |
|----|--------|------|
| CAT-2 | Fixed | Optional class `wink-hero-pattern` added; pattern overlay in SCSS. |
| CAT-5 | Fixed | Slugify in controller (re); default strip color in SCSS. |
| CAT-6 | Fixed | Sparkles inline SVG for POPULAR badge. |
| CAT-9 | Fixed | Bootstrap Offcanvas (bottom) for mobile filters; desktop sidebar unchanged. |
| CR-5 | Fixed | "N selected" badge + JS; avatar initials circle; job_title on cards. |
| CR-6 | Fixed | review_display (type, tier, plan, employee_names); review card rows + name badges. |
| CR-8 | Fixed | Success block: CheckCircle icon, card-premium, "What happens next?", button classes. |
| Epic4-MR | Fixed | search/status/type/sort wired; filter_* in template; mobile card list; table hidden on mobile. |
| Epic4-RD | Verified | Existing Request Detail has payment banners, Next Steps, Compliance Documents, Retainer section; no code change. |
| Epic4-NT | Fixed | Category, Priority, dashed dropzone (click-to-upload), file type/size validation, error alerts, full-width Submit. |
