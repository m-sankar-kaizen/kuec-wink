# Epic-by-Epic Gap Analysis — Client Request vs Delivered

**Purpose:** Walk through each epic one by one to confirm any gap between the client request (Lovable/spec) and what was delivered.  
**Use:** Tick “Confirmed” when you’ve verified; note gaps and actions in the right column.

---

## Epic 1 — Service Catalogue (`/services`)

| ID | Client request (from LOVABLE_IDEAS_PLAN / spec) | Delivered? | Gap / Notes |
|----|-------------------------------------------------|------------|-------------|
| **CAT-1** | Hero: `kuec-gradient rounded-2xl`, title “Service Catalogue”, subtitle, **search bar inside hero** | ✅ Yes | Hero has gradient, rounded-2xl, title, subtitle, search inside. |
| **CAT-2** | Optional **subtle SVG pattern overlay** (white/low opacity) on hero | ⚠️ Partial | No SVG pattern added. Optional in plan — confirm if client wants it. |
| **CAT-3** | **Mobile** filter trigger: SlidersHorizontal icon; **badge with active filter count**; opens filter panel | ✅ Yes | Button with `fa-sliders`, badge with `active_filter_count`, collapse to sidebar. |
| **CAT-4** | Desktop sidebar: **Sticky** `card-premium rounded-2xl`; “Filters” + icon; Department **(checkboxes + count)**; Service Nature; Delivery Model (radio); **“Clear All Filters (N)” when N > 0** | ✅ Yes | Sidebar in card-premium, sticky-top, dept count `(N)`, Clear All Filters (N) when active. |
| **CAT-5** | Department colors: Legal purple, IT cyan, HR rose, Finance warning, Business Dev success — **badge + strip** | ✅ Yes | SCSS: `.wink-dept-strip.wink-dept-legal|it|hr|finance|business-dev`; strip on cards. **Check:** Dept names must match slug (e.g. “Business Development” → `business-development`). |
| **CAT-6** | Cards: **left/top department strip**; Popular badge (Sparkles + warning); title; **description 2-line clamp**; badges (dept, deliveryModel, type); **footer: price or “Custom proposal”**; Details + Request | ✅ Yes | Strip, POPULAR (fa-star), clamp, badges, price or `price_hidden_label`, Details + Request. **Check:** “Sparkles” icon vs “fa-star” — confirm with design. |
| **CAT-7** | “Showing N service(s)” above grid | ✅ Yes | “Showing N service(s)” with plural. |
| **CAT-8** | Empty state: **Search icon**, “No services found”, “Try adjusting your search or filters”, “Clear all filters” button | ✅ Yes | `wink-empty-state` with fa-search, message, “Clear all filters” link. |
| **CAT-9** | Mobile filter: **bottom sheet / drawer** with same FilterContent | ⚠️ Partial | Same sidebar content in **collapse** (not bottom sheet). Plan said “Option A: same sidebar in collapse”. Confirm if client expects true bottom sheet/drawer. |
| **CAT-10** | Container: **max-w-7xl (1280px)**, p-4 md:p-6 lg:p-8, space-y-6 | ✅ Yes | `wink-catalogue-container` max-width 1280px, responsive padding. |

**Epic 1 summary:**  
- **Gaps to confirm:** CAT-2 (hero pattern), CAT-9 (collapse vs bottom sheet), CAT-6 (Sparkles vs star).  
- **Data check:** Department slug mapping (e.g. “Business Development” → `business-development` or `business-dev`) for strip colors.

---

## Epic 2 — Create New Request (4-step wizard)

| ID | Client request (from plan / spec) | Delivered? | Gap / Notes |
|----|-----------------------------------|------------|-------------|
| **CR-1** | **Single wizard URL**; step 0–3 or success; reuse `/my/requests/new` with `?step=0|1|2|3`; post-submit → success view | ✅ Yes | One route; step 0 (no product_id), 1–3 with product_id; redirect to detail with `?submitted=1`. |
| **CR-2** | **Stepper**: Service → Configure → Employees → Review; **current step highlighted** | ✅ Yes | Stepper on step 0 template and in form (steps 1–3); current step with dot/check. |
| **CR-3** | Step 0: **Search**; grid of **selectable** service cards; **border-2 primary + check icon** when selected; icon, title, description, dept/delivery badges, price or “Custom proposal” | ✅ Yes | Search, grid, radio selection, `.wink-card-selected` + check icon. **Check:** Per-card “icon” (department icon?) not added — only strip/badges. |
| **CR-4** | Step 1 — Configure: **Selected service summary card (primary tint)**; if tiers “Select Your Tier” + tier cards (radio); if plans “Choose Your Plan” + plan cards (radio); **Requested Start Date**; **Special Requirements** (textarea) | ✅ Yes | Service context card, tier/plan selectors, start date, notes. **Check:** “Primary tint” on summary card — current card uses existing style; confirm if stronger tint needed. |
| **CR-5** | Step 2 — Employees: “Select Employees” + **count badge**; employee cards (checkbox, **avatar/initials**, name, **job title, status**); or alert “No employees… Add employees here” | ⚠️ Partial | “Select Employees” + checkboxes; alert when no employees. **Missing:** Count badge (e.g. “3 selected”), avatar/initials, job title, status on cards. |
| **CR-6** | Step 3 — Review: “Review Your Request” card: **key-value** (Service, Type, Tier?, Plan?, Start Date?), Notes, **Employees badges**; info AlertBanner about coordinator | ⚠️ Partial | Key-value (Service, Start Date, Notes, “N selected” for employees). **Missing:** Type, Tier/Plan labels in review; employee names as badges. |
| **CR-7** | Navigation: **Back (outline), Next (primary)** or **Submit Request**; Back from step 3 → step 2; **Next disabled on step 0 if no service selected** | ✅ Yes | Back/Next/Submit; Back from 3→2, 2→1, 1→0. Step 0 form uses `required` on radio so submit blocked until selection. |
| **CR-8** | **Success screen**: CheckCircle2, “Request Submitted!”, message with **service name**, **“What happens next?” list**, View My Requests + Browse More Services | ⚠️ Partial | Success is **request detail with `?submitted=1`** (existing block). **Check:** Dedicated success screen vs current “submitted” block; “What happens next?” list and exact copy. |
| **CR-9** | Submit → create draft sale order; redirect to **success view** (request id or detail with `?submitted=1`) | ✅ Yes | `submit_request` unchanged; redirect to `/my/requests/{id}?submitted=1`; wizard draft cleared. |

**Epic 2 summary:**  
- **Gaps:** CR-5 (count badge, avatar/initials, job title, status), CR-6 (Type/Tier/Plan in review, employee name badges), CR-8 (success screen copy and “What happens next?” list).  
- **Optional check:** CR-3 card icon; CR-4 summary card “primary tint”.

---

## Epic 3 — Shared / Global (G-1 to G-4)

| ID | Client request | Delivered? | Gap / Notes |
|----|----------------|------------|-------------|
| **G-1** | AppLayout: p-4 md:p-6 lg:p-8, **max-w-***, consistent spacing | ✅ Yes | `wink-portal-container`, `wink-catalogue-container` (max-w 1024/1280). |
| **G-2** | Card selected: **border-2 border-primary**, **bg-primary/[0.04]**, **check icon in corner** | ✅ Yes | `.wink-card-selected`, `.wink-card-selected-check` (fa-check-circle) in corner. |
| **G-3** | Buttons: **rounded-xl**, **touch-target**, outline vs primary | ✅ Yes | Wizard and key CTAs use `rounded-xl touch-target`; Back outline, Next/Submit primary. |
| **G-4** | Form labels: **Icons** (CalendarDays, StickyNote, Users) next to label | ✅ Yes | fa-calendar (Start Date), fa-sticky-note (Notes), fa-users (Select Employees). |

**Epic 3 summary:** No material gaps.

---

## Epic 4 — Portal pages (My Requests, Request Detail, Service Detail, New Ticket)

*Reference: WINK_PORTAL_LOVABLE_PARITY_REPORT.md (UI-LOV-001 to UI-LOV-020).*

| Issue / area | Client request (spec / report) | Delivered? | Gap / Notes |
|--------------|--------------------------------|------------|-------------|
| **My Requests** | Premium card wrap; **filters row**: search + **Status / Type / Payment / Sort** dropdowns; empty state with icon + CTA; **mobile card list** (table hidden &lt; md) | ⚠️ Partial | Premium card, filters row (search + dropdowns), empty state done (UI-LOV-006, 008). **Check:** Status/Type/Payment/Sort wired to backend; mobile **card list** (UI-LOV-007) — table/cards responsive. |
| **Request Detail** | Payment banner (Locked/Due/Paid); Order Summary with **gradient header + status badge**; Next Steps (locked/due/paid); Delivery Progress + Activity; Compliance Documents; **Retainer Management** card | ⚠️ Partial | Gradient summary, status badges, stepper, timeline done. **Check:** Payment banner variants, Next Steps blocks, Compliance Documents rows, Retainer card (UI-LOV-009, 011, 013, 014). |
| **Service Detail** | Breadcrumbs; **sticky right CTA** (gradient, “Starting at AED…” or “Get a Quote”); **mobile sticky bottom CTA bar** | ✅ Yes | Breadcrumbs; CTA card with gradient; mobile sticky bar (UI-LOV-015–017). |
| **New Support Ticket** | Title + subtitle; premium card **gradient header**; form: Subject, **Category**, **Priority**, Description, **Attachment**; full-width Submit | ⚠️ Partial | Page + controller (UI-LOV-019). **Check:** Category/Priority fields and options; attachment dropzone and upload handling. |

**Epic 4 summary:** My Requests filters + mobile cards; Request Detail payment/next steps/documents/retainer; New Ticket Category/Priority/Attachment — confirm and close gaps.

---

## Epic 5 — Out-of-scope / not in plan

| Topic | In plan? | Delivered? | Note |
|-------|----------|------------|------|
| Refund / Credit Note workflow | No (separate) | — | “Refund not working and Credit not done” — separate from Lovable UI. |
| Pricing logic (“Standard Monthly Price”) | No | — | Clarification doc, not UI. |
| Payment & cancellation UI improvements | Mentioned in chat | Partial | Request Detail payment/cancellation states. |
| InvalidDomainError `group_id,=` | No | — | Backend/domain fix. |
| 404 on `/services` | No | — | Route exists; check proxy/config. |

---

## How to use this doc (one by one)

1. **Epic 1:** Open `/services` — go through CAT-1 to CAT-10 rows; tick “Confirmed” in your copy when verified; note any gap (e.g. “CAT-2: add hero pattern”) and decide **Accept as-is** or **Fix**.  
2. **Epic 2:** Run wizard from “Create New Request” and from catalogue “Request” — check CR-1 to CR-9; confirm success screen and review step content; list missing items (e.g. CR-5 count badge, CR-8 “What happens next?”).  
3. **Epic 3:** Spot-check layout and buttons on catalogue + wizard — confirm G-1–G-4.  
4. **Epic 4:** Open My Requests, a request detail, a service detail, New Ticket — compare to spec/report; confirm filters, mobile cards, payment/documents/retainer, ticket form.  
5. **Epic 5:** Treat as separate backlogs; add to a “Post–Lovable” list if needed.

---

## Quick checklist (copy and tick)

```
Epic 1 — Catalogue
[ ] CAT-1 Hero + search
[ ] CAT-2 Hero pattern (optional)
[ ] CAT-3 Mobile filter + badge
[ ] CAT-4 Sidebar + counts + Clear (N)
[ ] CAT-5 Dept colors/strip
[ ] CAT-6 Cards (strip, Popular, clamp, price/CTA)
[ ] CAT-7 "Showing N services"
[ ] CAT-8 Empty state
[ ] CAT-9 Mobile filter UX (collapse vs drawer)
[ ] CAT-10 Container

Epic 2 — Wizard
[ ] CR-1 Single URL + steps + success redirect
[ ] CR-2 Stepper
[ ] CR-3 Step 0 selectable cards
[ ] CR-4 Step 1 configure (tier/plan/date/notes)
[ ] CR-5 Step 2 employees (count, avatar, job, status)
[ ] CR-6 Step 3 review (Type/Tier/Plan, employee badges)
[ ] CR-7 Back/Next/Submit + disabled Next step 0
[ ] CR-8 Success screen copy + "What happens next?"
[ ] CR-9 Submit + redirect

Epic 3 — Global
[ ] G-1 Container/layout
[ ] G-2 Card selected
[ ] G-3 Buttons
[ ] G-4 Label icons

Epic 4 — Portal pages
[ ] My Requests filters + mobile cards
[ ] Request Detail banners + documents + retainer
[ ] Service Detail CTA + mobile bar
[ ] New Ticket form (Category, Priority, Attachment)
```

---

## Confirmed Status (Post Gap Closure)

| ID | Status |
|----|--------|
| CAT-2 | Fixed |
| CAT-5 | Fixed |
| CAT-6 | Fixed |
| CAT-9 | Fixed |
| CR-5 | Fixed |
| CR-6 | Fixed |
| CR-8 | Fixed |
| Epic4-MR | Fixed |
| Epic4-RD | Verified |
| Epic4-NT | Fixed |

See `WINK_PORTAL_GAP_CLOSURE_REPORT.md` for implementation summary and manual validation checklist.

---

**Next:** For each epic, confirm row by row; document “Accept”, “Fix”, or “Clarify with client” and update this file or your backlog accordingly.
