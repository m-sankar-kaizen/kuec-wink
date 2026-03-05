# Lovable Ideas → Odoo Portal — Output Plan

**Purpose:** Plan the output (deliverables) before building. All ideas from the shared React components (Catalogue, CreateRequest) are mapped to Odoo portal pages, templates, and SCSS so implementation can follow this plan step-by-step.

**Scope:** Portal UI only (QWeb + SCSS). No backend logic changes unless stated.

---

## 1) Source Ideas Summary

| React source | Main ideas |
|--------------|------------|
| **Catalogue** | Hero with gradient + search inside; Department filters with icons + counts; Service Nature (Gov/Non-Gov) checkboxes; Delivery Model (Project/Retainer) radio; dept colors (purple/cyan/rose/warning/success); service cards with dept strip, Popular badge, Details/Request; mobile filter bottom sheet + badge count; empty state with Clear filters |
| **CreateRequest** | 4-step wizard (Service → Configure → Employees → Review); Stepper at top; Step 1: search + selectable service cards; Step 2: selected service summary, tier/plan selection cards, start date + notes; Step 3: employee checkboxes/cards or “Add employees” alert; Step 4: review card (key-value + notes + employees); success screen with “What happens next?”; Back/Next/Submit navigation |

---

## 2) Output Plan — What We Will Build

### 2.1 Service Catalogue (`/services`)

| # | Output | Lovable idea | Odoo target |
|---|--------|--------------|-------------|
| CAT-1 | Hero block | `kuec-gradient rounded-2xl`, title “Service Catalogue”, subtitle, search bar inside hero | `wink_catalogue_page.xml` — banner section |
| CAT-2 | Hero pattern | Optional subtle SVG pattern overlay (white/low opacity) | SCSS or inline style in template |
| CAT-3 | Mobile filter trigger | Button with SlidersHorizontal icon; badge with active filter count; opens filter panel/sheet | Template: filter button (visible on mobile only); badge count from controller |
| CAT-4 | Desktop sidebar filters | Sticky `card-premium rounded-2xl`, “Filters” + icon; Department (checkboxes + icon + count); Service Nature (checkboxes); Delivery Model (radio); “Clear All Filters (N)” when N > 0 | Same template: sidebar visible ≥ md; filter form with checkboxes/radios |
| CAT-5 | Department colors | Legal: purple; IT: cyan; HR: rose; Finance: warning; Business Dev: success — for badge, strip, icon | SCSS: e.g. `.dept-strip-legal`, `.badge-wink-dept-*`; map in controller or template from product department |
| CAT-6 | Service cards | Card with optional left/top department strip; Popular badge (Sparkles + warning style); title; description (2-line clamp); badges: department (colored), deliveryModel, type; footer: price or “Custom proposal required”; Details + Request buttons | Existing card snippet; add strip class, Popular badge, footer layout |
| CAT-7 | “Showing N service(s)” | Text above grid | Already present; ensure wording matches |
| CAT-8 | Empty state | Search icon, “No services found”, “Try adjusting your search or filters”, “Clear all filters” button | Template block when filtered list empty |
| CAT-9 | Mobile filter panel | Bottom sheet / drawer with same FilterContent (Department, Nature, Delivery, Clear) | Option A: same sidebar in a collapse/drawer for mobile. Option B: modal. Plan: reuse same filter markup; show in drawer or collapse below hero on mobile |
| CAT-10 | Container | `max-w-7xl` (1280px), `p-4 md:p-6 lg:p-8`, `space-y-6` | Layout wrapper class in SCSS/template |

**Deliverables:**  
- Template: `wink_catalogue_page.xml` (hero, sidebar, grid, empty state, mobile filter trigger).  
- SCSS: department strips/colors, hero pattern if used, card strip, empty state.  
- Controller: pass `departments` with counts, `active_filter_count` (or compute in template), preserve search/filter params.

---

### 2.2 Create New Request — 4-Step Wizard

| # | Output | Lovable idea | Odoo target |
|---|--------|--------------|-------------|
| CR-1 | Single wizard URL | One portal route that shows step 0–3 or success | New or existing route, e.g. `/my/requests/create` or reuse `/my/requests/new` with `?step=0|1|2|3` and post-submit redirect to success view |
| CR-2 | Stepper | Steps: Service → Configure → Employees → Review; current step highlighted | Template: reuse or extend `Stepper`-like partial (steps array, current index); same styling as Delivery Progress |
| CR-3 | Step 0 — Choose Service | Search input; grid of service cards; card selectable (border-2 primary when selected, check icon); each: icon, title, description, department/delivery badges, price or “Custom proposal” | New template section or new page; data: products from catalogue; selection stored in session or form hidden field |
| CR-4 | Step 1 — Configure | Selected service summary card (primary tint); if tiers: “Select Your Tier”, grid of tier cards (radio); if plans: “Choose Your Plan”, grid of plan cards (radio); Requested Start Date (date input); Special Requirements (textarea) | Template section; data: selected product, tiers/plans from product; form fields: start_date, notes, tier_id, plan_id |
| CR-5 | Step 2 — Employees | “Select Employees” + count badge; list of employee cards (checkbox, avatar/initials, name, job title, status); or AlertBanner: “No employees… Add employees here” | Template section; data: employees from `kuec.employee.directory` for partner; form: employee_ids |
| CR-6 | Step 3 — Review | “Review Your Request” card: key-value rows (Service, Type, Tier?, Plan?, Start Date?), Notes block if any, Employees badges; info AlertBanner about coordinator | Template section; data: same as form summary |
| CR-7 | Navigation | Back (outline), Next (primary) or Submit Request (primary); Back from step 3 goes to 2 (or 1 if no employees); Next disabled on step 0 if no service selected | Template: buttons; step transition via form GET or JS |
| CR-8 | Success screen | After submit: card with CheckCircle2, “Request Submitted!”, message with service name, “What happens next?” list, View My Requests + Browse More Services | Same as current success block; ensure it’s the only content when `submitted=1` (or equivalent) |
| CR-9 | Submit | POST to create draft sale order (or existing submit endpoint); then redirect to success view with request id or to request detail with `?submitted=1` | Controller: reuse `submit_request` or new wizard submit; redirect to detail with `?submitted=1` |

**Deliverables:**  
- Template(s): one wizard template with conditional sections per step (or one template per step and controller switches).  
- Controller: one route for GET (step, search, selection) and one for POST (submit step or final submit). Session or form state for selected service, tier, plan, employees.  
- SCSS: step cards (selected state), review card, alert banner — reuse existing where possible.

---

### 2.3 Shared / Global

| # | Output | Lovable idea | Odoo target |
|---|--------|--------------|-------------|
| G-1 | AppLayout | `p-4 md:p-6 lg:p-8`, `max-w-*`, consistent spacing | Portal layout or wrapper: `wink-portal-container` (already in plan); ensure max-w-7xl (1280px) where needed |
| G-2 | Card selected state | `border-2 border-primary bg-primary/[0.04]`, check icon in corner | SCSS class e.g. `.card-selected` or `.wink-card-selected` for wizard cards |
| G-3 | Buttons | rounded-xl, touch-target, outline vs primary | Already in theme; ensure “Back” and “Next” match Lovable |
| G-4 | Form labels | Icons (CalendarDays, StickyNote, Users) next to label | Template: add icon span next to label text where applicable |

---

## 3) Document Outputs (Artifacts)

Before coding, the plan produces:

1. **This file** — `LOVABLE_IDEAS_PLAN.md`: mapping of ideas to outputs (above).
2. **Findings / Issue IDs** — Optional: extend `WINK_PORTAL_LOVABLE_PARITY_REPORT.md` with rows for CAT-* and CR-* so each build task has an ID.
3. **Implementation order** — Recommended build order:
   - Phase A: Catalogue (CAT-1–CAT-10) — hero, filters, cards, empty state, mobile filter.
   - Phase B: Create Request wizard (CR-1–CR-9) — stepper, steps 0–3, success, controller flow.
   - Phase C: Polish — shared classes (G-1–G-4), any missing dept colors or strips.

---

## 4) Data Mapping (Odoo ↔ Lovable)

| Lovable | Odoo |
|---------|------|
| `departments` (name, icon, count) | Product categories or `kuec.classification` / department relation; count = number of published products per department |
| `serviceNatures` | Product attribute or tag (Governmental / Non-Governmental) |
| `deliveryModels` | `delivery_model` (project / retainer) on product |
| `services` (title, department, deliveryModel, type, nature, description, price, customProposal, popular) | `product.template`: name, department_ids, delivery_model, type/classification, description, list_price or price_visibility, ribbon tag for “popular” |
| `catalogServices` / tiers / plans | Products; tiers from bundle or product variants; plans from recurring pricing / `wink.subscription.plan` |
| `mockEmployees` | `kuec.employee.directory` for current partner |

---

## 5) Acceptance (Definition of Done per Output)

- **Catalogue:** Hero with search, filters (dept/nature/delivery) with counts and clear, service cards with dept strip and Popular badge, empty state, mobile filter trigger and panel; no regressions on existing catalogue behavior.
- **Create Request:** 4-step flow with stepper; step 0 select service; step 1 configure (tier/plan if applicable, date, notes); step 2 employees (or skip if not required); step 3 review; submit creates request and shows success screen; Back/Next and Submit match Lovable behavior.

---

## 6) Out of Scope for This Plan

- Backend changes to product or sale order models (unless required for tier/plan/employee binding).
- New API or JSON endpoints for the portal (all form/GET/POST via existing or new HTTP routes).
- Lovable’s exact React state management (use Odoo session or form POST to advance steps).

---

**Next step:** Use this plan as the single reference; implement in order Phase A → Phase B → Phase C, and tick off CAT-* / CR-* / G-* in the report or this doc as each output is done.
