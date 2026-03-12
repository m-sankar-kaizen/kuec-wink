# Team Feedback Triage — Portal Workflow (One-by-One)

> **VERIFIED CODEBASE RE-CHECK NOTE**: A fresh code-level audit was performed. The following findings are re-verified:
> - **Plan Selection (UI-BUG-005)**: Verified Fixed. The logic in `request.py` lines 872-917 explicitly sets `selected_pricing_id` using query/form kwargs, preserving the selection safely.
> - **Portal Tags (UI-TAG-001/002)**: Verified Fixed. `wink_catalogue_page.xml` correctly applies the diagonal ribbon and pill badge logic.
> - **Bundle Workflows (WF-BND)**: Verified Fixed. Logic for employee, doc, and task linkage verified in `sale_order_line.py`, `project_task.py`, and `request.py`.
> - **Dashboard KPIs**: Verified Missing. No code or templates exist for portal analytic widgets.

**Scope:** kuec_portal_foundation, kuec_service_catalogue  
**Rules:** Classify each item as BUG / NOT A BUG / ENHANCEMENT / NEEDS VALIDATION. No code changes until BUG is confirmed and documented with Issue ID + Fix Plan.

---

## Triage entries

*(Each entry: Feedback ID, Classification, Severity, Affected Epic, Where, Repro, Actual, Expected, Root cause, Fix plan, Risk, Validation.)*

---

### FB-001 — Bundle of product/admin and portal items

**Source:** Team feedback (product form, portal catalogue/detail, documents, quotation).

| Sub-ID | Description | Classification | Severity | Affected Epic | Issue ID |
|--------|-------------|----------------|----------|---------------|----------|
| FB-001a | When user unchecks Can be Sold (Sales), Wink tab and Required Documents are not hidden | **BUG** | High | Backend (product form) | **WF-BUG-001** |
| FB-001b | When product type is changed to Goods, Wink tab and Required Documents remain visible; departments not displayed correctly in component | **BUG** | High | Backend (product form) / Component | **WF-BUG-001** (same fix as a) |
| FB-001c | Fields within Wink tab are not enforced as mandatory (not all of them) | **ENHANCEMENT** | Low | Backend (product form) | — |
| FB-001d | Attachments uploaded in Required Documents are not displayed in Compliance Documents section | **NEEDS VALIDATION** | — | Request Detail / Documents | — |
| FB-001e | Quotation can be confirmed even when required documents are mandatory but not uploaded | **BUG** | High | Backend (sale/project) | **WF-BUG-002** |
| FB-001f | Governmental and Non-Governmental classifications can be selected simultaneously | **BUG** | Medium | Backend (product / nature) | **WF-BUG-003** |
| FB-001g | When Delivery Model = Retainer, Subscription option is not automatically checked | **BUG** | Medium | Backend (product form) | **WF-BUG-004** |
| FB-001h | The Ribbon is not displayed in the portal | **BUG** | Medium | Service Catalogue / Service Detail | **UI-BUG-001** |
| FB-001i | In subscription product: all recurring plan prices should be displayed in product details in portal; quotation based on that selection | **NOT A BUG** / Verify | — | Service Detail | — |

---

#### FB-001a / FB-001b — WF-BUG-001: Wink tab and Required Documents visibility

- **Where:** `kuec_service_catalogue/views/product_template_views.xml` — pages `wink_tab`, `required_documents_tab`.
- **Repro:** 1) Edit a service product. 2) Uncheck "Can be Sold (Sales)" OR change Type to "Storable Product" / "Consumable" (Goods). 3) Save.
- **Actual:** Wink and Required Documents tabs remain visible.
- **Expected:** Both tabs hidden when product is not sellable or not a service (Wink only applies to sellable services).
- **Root cause:** Tabs use `invisible="not available_on_wink"` only; no dependency on `sale_ok` or `type == 'service'`.
- **Fix plan:** Set both pages to `invisible="not available_on_wink or type != 'service' or not sale_ok"`. Minimal view change; no security impact.
- **Risk:** Low. Upgrade-safe.
- **Validation:** Uncheck Can be Sold → tabs disappear; set Type to Consumable → tabs disappear; set back to Service + Can be Sold → tabs reappear.

---

#### FB-001c — Wink tab mandatory fields

- **Classification:** ENHANCEMENT. No code change in this triage; requires product owner to define which fields must be required.
- **Proposal:** Add `required="1"` (or `attrs`) on key Wink fields (e.g. `price_visibility`, `delivery_model`, `department_ids` if desired) per spec.

---

#### FB-001d — Attachments in Compliance Documents

- **Classification:** NEEDS VALIDATION.
- **Clarification:** "Attachments uploaded in Required Documents" can mean (A) admin uploads (attachment_ids on `kuec.service.document`) or (B) customer uploads (portal document submissions). Compliance Documents section shows requirement rows + submission status (Not Uploaded / Under Review / Approved). Customer submissions are linked via `sub_map` from `order.document_submission_ids`.
- **Validation steps:** 1) Create order with required docs. 2) Upload document in portal for that requirement. 3) Open request detail and check Compliance Documents section — status should show Under Review and later Approved; link to view/download if applicable. 4) If status updates but file link missing → BUG (portal). If admin’s sample files should appear in portal → ENHANCEMENT.

---

#### FB-001e — WF-BUG-002: Quotation confirm without required docs

- **Where:** Backend: sale order confirmation and/or project task stage move (e.g. `kuec_service_catalogue/models/project_task.py` — `_wink_all_required_docs_approved` used on stage change).
- **Repro:** Create request with service that has mandatory documents; do not upload them; confirm quotation (or move task stage).
- **Actual:** Quotation can be confirmed.
- **Expected:** Block confirmation (or stage move) until required documents are uploaded/approved per business rule.
- **Fix plan:** Ensure sale order confirmation (and/or related workflow) checks `_wink_all_required_docs_approved` and raises UserError with clear message listing missing docs. Document only in this triage; implementation in backend module.
- **Risk:** Medium (workflow change).
- **Validation:** With required docs not uploaded, confirm action is blocked; after upload/approval, confirm succeeds.

---

#### FB-001f — WF-BUG-003: Governmental / Non-Governmental mutual exclusivity

- **Where:** `product.template` — `nature_ids` (many2many to `kuec.service.nature`). Data: Governmental / Non-Governmental are two natures.
- **Repro:** On product form, add both Governmental and Non-Governmental to Service Nature.
- **Actual:** Both can be selected.
- **Expected:** At most one of the two (e.g. enforce via domain or constraint, or single selection widget).
- **Fix plan:** Backend: add Python constraint or selection widget (e.g. radio for “Classification” with Governmental / Non-Governmental / Both / None) or domain on `nature_ids` so that only one of the two can be set. Document only in this triage.
- **Risk:** Low–medium (data model/UX).
- **Validation:** Only one of Gov/Non-Gov selectable per product.

---

#### FB-001g — WF-BUG-004: Retainer → Subscription auto-check

- **Where:** Product form — `recurring_invoice` (or equivalent “Subscription” field) and `delivery_model`.
- **Repro:** Set Delivery Model to Retainer. Check if “Subscription” (recurring) is auto-checked.
- **Actual:** Subscription not auto-checked.
- **Expected:** When Delivery Model = Retainer, Subscription/recurring option is automatically set.
- **Fix plan:** Backend: onchange on `delivery_model`: when `delivery_model == 'retainer'`, set `recurring_invoice = True` (or equivalent). Depends on Odoo version field names (e.g. `sale_subscription`). Document only in this triage.
- **Risk:** Low.
- **Validation:** Set Retainer → Subscription becomes checked; change to Project → can uncheck if desired.

---

#### FB-001h — UI-BUG-001: Ribbon not displayed in portal

- **Where:** Portal: `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` — `wink_service_card` (catalogue grid), service detail block (around line 282). `kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss` (or theme).
- **Repro:** Assign a tag with “Show as Ribbon on Website” to a service; open `/services` and service detail in portal.
- **Actual:** Tag appears as a badge (e.g. “POPULAR” or tag name) but not as a diagonal ribbon.
- **Expected:** Ribbon displayed as a diagonal corner ribbon (e.g. top-right) on cards and detail, per `product.tag` `is_ribbon` and spec.
- **Root cause:** Template uses a badge-style span; no diagonal ribbon styling (e.g. `.o_ribbon` / `.o_ribbon_right`) or equivalent Wink class.
- **Fix plan:** 1) Add `.wink-ribbon` in SCSS: position absolute, top-right, rotate 45°, background/color, z-index. 2) In `wink_service_card` and service detail, when `ribbon_tags` is set, render a span with class `wink-ribbon` (and optional `wink-ribbon-top-right`) with tag name. 3) Ensure parent card has `position: relative`.
- **Risk:** Low. Visual only.
- **Validation:** Service with ribbon tag shows diagonal ribbon on catalogue card and on service detail page.

---

#### FB-001i — Recurring prices and quotation from selection

- **Classification:** NOT A BUG (or verify). Portal service detail already shows “Choose your plan” with all plans and prices when `len(subscription_plans) > 1`; “Request Service” passes `?plan=` with selected recurrence. When only one plan, link includes that plan. If “all prices” means also showing the single plan explicitly, current UI already shows “Starting at AED X” and the plan. No code change unless validation shows otherwise.
- **Validation:** Open a retainer product with multiple recurring plans → all plans and prices visible; select one → Request Service → quotation/request uses that plan.

---

## Implementation summary (FB-001)

| Issue ID | Status | Files changed |
|----------|--------|----------------|
| **WF-BUG-001** | Fixed | `kuec_service_catalogue/views/product_template_views.xml` |
| **UI-BUG-001** | Fixed | `kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss`, `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` |
| **UI-BUG-002** (FB-002) | Fixed | `kuec_service_catalogue/controllers/request.py`, `kuec_service_catalogue/views/website_templates/request_templates.xml` |
| **UI-BUG-003** (FB-003) | Fixed | `kuec_service_catalogue/controllers/request.py`, `kuec_service_catalogue/views/website_templates/request_templates.xml` |
| **UI-BUG-004** (FB-004) | Fixed | `kuec_service_catalogue/controllers/request.py`, `kuec_service_catalogue/views/website_templates/request_templates.xml` |
| WF-BUG-002, WF-BUG-003, WF-BUG-004 | Documented only (backend) | — |
| FB-001c, FB-001d, FB-001i | ENHANCEMENT / NEEDS VALIDATION / Verify | — |

### Validation checklist (FB-001)

- [ ] **WF-BUG-001:** Product form: Uncheck "Can be Sold" → Wink and Required Documents tabs hidden. Set Type to Consumable → tabs hidden. Set back to Service + Can be Sold → tabs visible.
- [ ] **UI-BUG-001:** Portal: Assign a tag with "Show as Ribbon on Website" to a service. Open `/services` → card shows diagonal ribbon with tag name. Open service detail → ribbon visible top-right.

---

### FB-002 — Public user enters data twice (registration + request/signup)

**Source:** Team feedback.

| Item | Description | Classification | Severity | Affected Epic | Issue ID |
|------|-------------|----------------|----------|---------------|----------|
| FB-002 | Public user is required to enter data twice — once during service request submission and again during new user creation | **BUG** | High | Create New Request / Registration | **UI-BUG-002** |

- **Where:** `/my/requests/new?product_id=X` (public → registration form), `/my/requests/register` (POST), then redirect to `/web/login`. Portal: `request.py`, `request_templates.xml`.
- **Repro:** 1) As public user, click "Create Account" from service (or go to `/my/requests/new?product_id=X`). 2) Fill company + contact on the WINK registration form and submit. 3) After account creation they are redirected to `/web/login`; the login page may show "Sign up" or similar, leading them to believe they must enter name/email again.
- **Actual:** User fills registration form (company, contact name, email, phone); after submit they land on the generic login page and may re-enter name/email on Odoo signup, or are confused about next step.
- **Expected:** User enters company/contact data once; after account creation they are clearly told "Account created — check your email to set your password" and have a single path to "Sign in" (no duplicate signup flow).
- **Root cause:** Redirect goes directly to `/web/login`, which can look like a signup gate and invites duplicate data entry or confusion.
- **Fix plan (UI-BUG-002):** (1) Add a dedicated thank-you route `GET /my/requests/register/thanks` that shows a clear "Account created" page: message that an email was sent to set password, and a single CTA "Sign in to continue your request" linking to `/web/login?redirect=...`. (2) In `register_and_request`, after creating the user and sending the reset email, redirect to this thank-you page with the redirect URL as query param instead of redirecting straight to `/web/login`. (3) No change to data collected; avoids dropping the user on the login page and reduces duplicate entry/confusion.
- **Risk:** Low. No auth/session change; UX only.
- **Validation:** As public user, complete registration form → land on thank-you page (not login) → click "Sign in to continue" → go to login with redirect to request form; no need to "sign up" again.

### Validation checklist (FB-002)

- [ ] **UI-BUG-002:** As public user, open `/my/requests/new?product_id=<id>`, fill registration form and submit → redirect to "Account Created" thank-you page (not `/web/login`). Page states "You don't need to create a new account". Click "Sign in to continue your request" → opens login with redirect to request form.

---

### FB-003 — Project-based product: Employees step and recurring plan shown/required (major bug)

**Source:** Team feedback + screenshots (IT Infrastructure, Project-Based, 3,200.00 AED).

| Item | Description | Classification | Severity | Affected Epic | Issue ID |
|------|-------------|----------------|----------|---------------|----------|
| FB-003 | For project-based product that does not require employees: system shows Employees step and asks to select employees; also requires "select a plan" (recurring plan). Both should not be shown or required for project-based. | **BUG** | Critical | Create New Request (wizard) | **UI-BUG-003** |

- **Where:** `kuec_service_catalogue/controllers/request.py` (new_request step flow, submit_request plan validation), `request_templates.xml` (stepper, step 2 visibility, step 1 button/next_step).
- **Repro:** 1) Create or use a service product with Delivery Model = Project-Based and Requires Employee Selection = False. 2) As portal user, go to Create New Request and select that service. 3) On Configure step, click Next → see Employees step (should be skipped). 4) Submit from Configure (or after Employees) without selecting a plan → error "Please select a plan." (plan must not be required for project-based).
- **Actual:** Employees step is shown and "Select Employees" is prompted; submit shows "Please select a plan." for project-based product.
- **Expected:** For project-based: no Employees step when `requires_employee_selection` is False; no plan selection/requirement (recurring plan only for retainer/subscription). Stepper and validation must respect `delivery_model` and `requires_employee_selection`.
- **Root cause:** (1) Plan validation in `submit_request` uses `use_recurring_prices and selected_recurrence_id is None` without checking `is_subscription_service`, so any product with recurring price lines triggers "Please select a plan." (2) Wizard always shows step 2 (Employees) and step 1 always posts next_step=2; no skip when `requires_employee_selection` is False.
- **Fix plan (UI-BUG-003):** (1) In `submit_request`: require plan only when `is_subscription_service and use_recurring_prices and selected_recurrence_id is None` (add `is_subscription_service` to the block that returns "Please select a plan."). (2) In `new_request`: when next_step=2 and product does not have `requires_employee_selection`, save draft with step 1 data and redirect to step=3 (skip step 2). (3) When rendering step=2, if product does not require employees, redirect to step=3. (4) In template: show Employees step in stepper only when `product.requires_employee_selection`; step 1 button label "Next: Review" when not requires_employee_selection, "Next: Employees" otherwise; step 2 block visible only when step==2 and requires_employee_selection.
- **Risk:** Low. Logic only; no new fields.
- **Validation:** Project-based product without requires_employee_selection: step 1 → Next goes to Review (no Employees step); submit without selecting plan succeeds. Retainer product still requires plan and shows Employees step when configured.

### Validation checklist (FB-003)

- [ ] **UI-BUG-003:** Use a project-based product with "Requires Employee Selection" = False (e.g. IT Infrastructure). Create New Request → Configure step shows "Next: Review" (not "Next: Employees"). Click Next → land on Review (no Employees step). Submit without selecting any plan → request submits successfully, no "Please select a plan" error.
- [ ] Stepper shows 3 nodes (Service, Configure, Review) for that product; Employees node hidden.
- [ ] Retainer product still shows Employees step when configured and still requires plan selection.

---

### FB-004 — Request detail: full amount shown after partial payment; no Pay remaining / due amount / due date

**Source:** Team feedback + screenshot (Order S00107, 30% paid per payment plan, still shows 3,360.00 AED).

| Item | Description | Classification | Severity | Affected Epic | Issue ID |
|------|-------------|----------------|----------|---------------|----------|
| FB-004 | Client paid 30% (960 + 5% tax) per payment plan but portal still shows full amount (3,360.00 AED) as Amount Due; no button to pay again, no remaining due amount or due date for the rest. | **BUG** | Critical | Request Detail / Order Summary | **UI-BUG-004** |

- **Where:** `request_detail` in `request.py`, template `wink_request_confirmation` in `request_templates.xml` (Order Summary, AMOUNT DUE, Next Steps).
- **Repro:** Create an order with a payment term (e.g. 30% deposit, 70% on delivery). Customer pays the first installment (30%). Open request detail in portal.
- **Actual:** AMOUNT DUE shows full order total (3,360.00 AED); "Payment received successfully" banner; no "Pay remaining" button, no remaining amount or due date.
- **Expected:** AMOUNT DUE shows **remaining** balance; after partial payment, Next Steps shows remaining amount, due date for next installment, and a "Pay remaining" (or "Proceed to payment") button for the balance.
- **Root cause:** Template and controller use `order.amount_total` for Amount Due and treat payment as binary (is_paid); no use of invoice `amount_residual` or payment-term due dates.
- **Fix plan (UI-BUG-004):** (1) In controller: from order's posted invoices compute amount_remaining (sum of amount_residual), amount_paid (total - remaining), has_partial_payment (paid > 0 and remaining > 0), next_due_date (earliest due date among invoices with residual > 0). (2) Template: show amount_remaining as AMOUNT DUE when price confirmed; when has_partial_payment show "Payment received (first installment). Amount remaining: X. Due: [date]. [Pay remaining]" block and button to /pay. (3) Ensure /pay route uses remaining amount when applicable (already may use payment term for first deposit; need to pass or compute amount for "remaining" payment).
- **Risk:** Medium (payment flow); ensure /pay still works for full and partial.
- **Validation:** Order with 30/70 payment term; pay 30% → request detail shows remaining 70% as Amount Due, due date, and "Pay remaining" button.

### Validation checklist (FB-004)

- [ ] **UI-BUG-004:** Order with payment plan (e.g. 30% deposit, 70% on delivery). Pay first installment (30%) → open request detail. AMOUNT DUE shows **remaining** balance (e.g. 70%), not full 3,360.00 AED. Next Steps shows "Payment received successfully" and below it "Amount remaining to pay", due amount, due date (if set), and **Pay remaining** button. Click Pay remaining → payment page shows remaining amount; after paying, amount due becomes 0 or next installment.
- [ ] Full payment (100% term): Amount Due = order total; after full pay, no "Pay remaining" block.

---

### FB-005 — Additional portal feedback (pricing, currency, plan selection, upgrade/downgrade, cancellation, bundle)

**Source:** Team feedback (8 items).

| Sub-ID | Description | Classification | Severity | Issue ID |
|--------|-------------|----------------|----------|----------|
| FB-005.1 | Price displayed per month instead of per year (e.g. 100/month instead of 1200/year) | **NEEDS VALIDATION** | Medium | — |
| FB-005.2 | Currency symbol displayed as "$" (should be AED or order currency) | **BUG** | High | **UI-BUG-005a** |
| FB-005.3 | Currency symbol (AED) displayed before the price value (preference: amount then currency?) | **ENHANCEMENT** | Low | — |
| FB-005.4 | When a plan is selected, it is not visually marked or highlighted as selected | **BUG** | Medium | **UI-BUG-005b** |
| FB-005.5 | When user with active plan selects upgrade/downgrade, system redirects to payment page and creates new request (should go to change-plan flow) | **BUG** | High | **UI-BUG-005c** |
| FB-005.6 | When quotation is cancelled in Sales Order, cancellation status is not reflected on portal | **BUG** | High | **UI-BUG-005d** |
| FB-005.7 | After cancelling quotation and submitting new request, system shows plan as already active | **BUG** | Critical | **UI-BUG-005e** |
| FB-005.8 | When bundle is created with multiple products, total bundle price is not displayed on portal | **BUG** | Medium | **UI-BUG-005f** |

---

#### FB-005.1 — Price per month vs per year

- **Interpretation:** User expects yearly plan to show 1200/year, not 100/month. May be data (Odoo recurring price stored per month) or display (we show monthly equivalent instead of period price).
- **Where:** `product_template._wink_subscription_plans_dicts` builds `price` and `period_label`; portal shows `plan['price']` + `plan['period_label']`.
- **Fix plan:** Confirm how Odoo stores price (per period vs per month). If price is per period, display is correct; if stored monthly, multiply by 12 for year. Document only; validate with actual recurrence/price data.

---

#### FB-005.2 — Currency symbol "$"

- **Where:** Portal templates use `order.currency_id.symbol`, `website.currency_id`, or hardcoded "AED". If company currency is USD, symbol can be "$".
- **Fix plan:** Use order/request currency consistently; for WINK portal prefer `order.currency_id.symbol or 'AED'` and ensure company/website currency is set to AED for this portal, or pass explicit `portal_currency_symbol` from controller (e.g. from product/order or config).

---

#### FB-005.3 — Currency before/after price

- **Interpretation:** User may prefer "1,200 AED" over "AED 1,200". Optional format change.
- **Fix plan:** ENHANCEMENT; optional template change to show amount first then currency where applicable.

---

#### FB-005.4 — Plan selected not highlighted

- **Where:** Service detail and request form: plan cards use `.wink-plan-card` with radio; no class when radio is checked.
- **Fix plan:** Add CSS so the label/card containing the checked radio gets a visible selected state (e.g. border-primary, background tint). Use `.wink-plan-card:has(input:checked)` or JS to toggle class on card when radio changes.

---

#### FB-005.5 — Upgrade/downgrade goes to payment/new request

- **Where:** From request detail, "Change Plan" / "Upgrade or downgrade" should link to `/my/requests/<id>/retainer/change-plan`, not to `/my/requests/new` or payment. Catalogue "Request" on same service when user has active retainer should offer change-plan, not new request.
- **Fix plan:** Ensure all upgrade/downgrade entry points (request detail Retainer card, catalogue CTA when active sub exists) point to change-plan route; block or redirect new-request flow when user already has active subscription for that product (we already show wink_request_already_subscription with change-plan link — verify link is used and not bypassed).

---

#### FB-005.6 — Cancellation status not reflected on portal

- **Where:** Request detail and My Requests list. `is_order_cancelled = order.state == 'cancel'` is passed; template shows `is_closed_or_cancelled` and `close_reason_name`.
- **Fix plan:** Ensure list view (My Requests) shows "Cancelled" badge for `state == 'cancel'` and detail shows cancelled state clearly. May need to add explicit cancelled banner or status row when `order.state == 'cancel'`.

---

#### FB-005.7 — New request after cancel shows "already active"

- **Where:** `new_request` and `request_detail`: active subscription check `active_sub = request.env['sale.order'].sudo().search([..., ('subscription_state', '=', '3_progress'), ...])` does not exclude cancelled orders.
- **Root cause:** When quotation is cancelled, `order.state` becomes `'cancel'` but search may still find it if we don't filter state, or subscription_state may still be 3_progress until churned.
- **Fix plan:** In the active_sub search domain, add `('state', '!=', 'cancel')` and optionally exclude `subscription_state in ('6_churn', ...)` so cancelled orders are not considered "active".

---

#### FB-005.8 — Bundle total price not displayed

- **Where:** Bundle product request form: tier cards show `td['tier'].price` per tier but no "Total bundle: X AED" when multiple products/items.
- **Fix plan:** When rendering bundle tier selection, compute and display total bundle price (e.g. sum of tier price or order total for selected tier). Pass `bundle_total` or use selected tier price as total; show "Total: X AED" in the bundle section.

---

#### Implementation summary (FB-005)

| Issue | Status | Changes |
|-------|--------|--------|
| **UI-BUG-005a** (FB-005.2) | Done | Portal monetary/currency: use `request.website.currency_id` (fallback `request.env.company.currency_id`) for product list price and bundle total in `request_templates.xml` so symbol follows website currency (e.g. AED when website set to AED). |
| **UI-BUG-005b** (FB-005.4) | Done | Added CSS in `wink_portal_lovable.scss`: `.wink-plan-card:has(input:checked)` and `.wink-tier-card:has(input:checked) .wink-tier-label` get border and background so selected plan/tier is visually highlighted. |
| **UI-BUG-005c** (FB-005.5) | Verified | Flow already correct: "Request" with active subscription shows `wink_request_already_subscription` with "Upgrade or downgrade" → `/my/requests/<id>/retainer/change-plan`. No code change. |
| **UI-BUG-005d** (FB-005.6) | Done | `portal.py`: base domain for My Requests now includes `'cancel'` in state list so cancelled orders appear in the list with "Cancelled" badge. Detail page already shows closed/cancelled via `is_closed_or_cancelled` and `close_reason_name`. |
| **UI-BUG-005e** (FB-005.7) | Done | `request.py`: active-subscription search in `new_request` and `service_request_form` now has `('state', '!=', 'cancel')` so cancelled orders are not treated as active; user can submit new request after cancelling. |
| **UI-BUG-005f** (FB-005.8) | Done | `request_templates.xml`: after bundle tier selector, added "Bundle total: [currency] [selected tier price]" using selected tier from `post.tier_id` (default first tier). |
| FB-005.1 (price per month/year) | Done | Main price shows **selected plan** (monthly → price + "per month"; yearly → price + "per year"). Backend: 12-month recurrence now gets `period_label = 'per year'`. Detail page: `display_plan` from controller so initial and JS-updated price match the chosen plan. |
| FB-005.3 (currency before/after) | Enhancement | Optional: show "1,200 AED" instead of "AED 1,200" where applicable. |

### Validation checklist (FB-005)

- [ ] **UI-BUG-005a:** Website currency set to AED (or desired symbol); portal product/request form amounts use website currency, not company $.
- [ ] **UI-BUG-005b:** On service detail and request form, selected plan/tier card shows distinct border and background.
- [ ] **UI-BUG-005d:** My Requests list shows cancelled orders (with "Cancelled" badge); detail shows "This request has been closed (Cancelled)".
- [ ] **UI-BUG-005e:** After cancelling a quotation, submitting a new request for the same service shows the request form (not "Already have subscription").
- [ ] **UI-BUG-005f:** Bundle product: after selecting a tier, "Bundle total: [currency] [price]" is visible below tier cards.

---

## FB-006 — Bundle activation workflow gaps

**Source:** Team feedback. Scope: `custom/kuec_portal_foundation`, `custom/kuec_service_catalogue`. No backend/admin UI changes.

| Issue ID    | Description | Severity | Status |
|-------------|-------------|----------|--------|
| **WF-BND-001** | Employees per activation: activation must create 0-price SO line and store selected employees on that line; portal must require employee selection when child service requires it | High | Verified Done |
| **WF-BND-002** | Docs required per activated service only: activation must require document submissions for the activated service product only; block with clear message + link to upload if missing | High | Verified Done |
| **WF-BND-003** | Task stage gate: when task.sale_line_id is an activated bundle line, check required docs for that sale_line_id.product only; error message lists user-friendly doc names | High | Verified Done |
| **WF-BND-004** | Completion from tasks: compute/display activation completion when all tasks linked to the activated sale.order.line are closed; expose in portal (request detail entitlements) | Medium | Verified Done |
| **WF-BND-005** | Repeated activation: validate multi-activation (qty-based); fix if second activation is blocked incorrectly (entitlement counters/UI) | Medium | Verified Done |

---

### WF-BND-001 — Employees per activation

- **Severity:** High
- **Repro steps:** 1) Create bundle order with tier that includes a child service with `requires_employee_selection=True`. 2) Confirm order. 3) In portal, open request detail → Included Services. 4) Click "Activate" on that entitlement (no employee selection step). 5) Check created SO line and task.
- **Actual:** Activation creates 0-price SO line and links to entitlement; task gets employees from entitlement's `wink_selected_employee_ids` (set once at request submit). No per-activation employee selection; if qty_entitled > 1, second activation reuses same entitlement employees.
- **Expected:** Each activation creates a 0-price sale.order.line and stores **selected employees for that activation** on the line (M2M to kuec.employee.directory). Portal activation flow must **require** employee selection when the child service (`entitlement.service_product_id`) has `requires_employee_selection=True`.
- **Root cause:** `sale.order.line` has no M2M for employees; `wink_bundle_entitlement.action_activate()` creates the line without employee data; portal posts directly to activate without a form. Task copies employees from `sale_line.wink_entitlement_id.wink_selected_employee_ids` (entitlement-level, not line-level).
- **Proposed fix plan:**
  1. Add `wink_selected_employee_ids` (Many2many to `kuec.employee.directory`) on `sale.order.line` in `kuec_service_catalogue` (portal-only usage; no backend form change per "no backend/admin UI").
  2. In `action_activate(employee_ids=None)`: accept optional `employee_ids`; create line then write `line.wink_selected_employee_ids = [(6, 0, employee_ids)]` when provided; when not provided and `service_product_id.requires_employee_selection` → raise UserError asking to select employees (portal will use form).
  3. Portal: when entitlement's `service_product_id.requires_employee_selection` and user clicks Activate, redirect to GET `/my/requests/<order_id>/bundle/<entitlement_id>/activate` (activation form page) with employee checklist; POST same URL with `employee_ids`; controller calls `action_activate(employee_ids=...)`. When service does not require employees, keep current direct POST with optional `employee_ids` from entitlement for backward compat.
  4. In `project.task` create(): when copying employees, prefer `sale_line.wink_selected_employee_ids` if set, else fallback to `sale_line.wink_entitlement_id.wink_selected_employee_ids`.
- **Validation checklist:**
  - [ ] Child service with requires_employee_selection: Activate opens form; must select ≥1 employee; submit creates line with those employees; task shows them.
  - [ ] Child service without requires_employee_select## BUG 1 — WF-BUNDLE-UI-006
**Status:** ✅ Resolved
**Severity:** High (Crash)
**Area:** Portal - My Bundles

**Description:**
Navigating to the My Bundles page throws a `TypeError: not enough arguments for format string`.

**Root Cause:**
In `custom/kuec_service_catalogue/views/website_templates/request_templates.xml` at line 2019, the progress bar used standard string interpolation with a literal `%` for the width percentage:
`t-att-style="'width: %s%%; ...' % bd['progress_pct']"`
QWeb incorrectly evaluated `%%` or failed to interpolate it properly in this context.

**Fix Implemented:**
Switched to QWeb's `t-attf-style` interpolation which is safer and cleaner:
`t-attf-style="width: {{ bd['progress_pct'] }}%; background: linear-gradient(90deg, #6366f1, #818cf8);"`

**Validation:**
Verified via code logic that standard string interpolation is removed, preventing the TypeError.

---

## BUG 2 — WF-BUNDLE-PLAN-002
**Status:** ✅ Resolved
**Severity:** Medium (Data Loss / Logic Error)
**Area:** Bundle Configurator & Request Detail

**Description:**
When a customer selects "Gold Annual" (or any non-default plan) during the bundle configuration, the system processes it but displays "Gold Monthly" (the default) in the review and detail pages.

**Root Cause:**
1. **Model Mismatch in Controller**: In `controllers/request.py`'s `submit_request`, the `selected_pricing_id` passed from the front end for Bundles corresponds to a `wink.subscription.plan` ID. However, the controller was only searching `['product.pricing', 'sale.subscription.pricing']` to validate the ID. It failed to find it, causing it to fall back or nullify the selection.
2. **Foreign Key Error Risk**: The controller was attempting to write the validated pricing ID into `sale.order.recurrence_id`, which strictly points to `sale.subscription.plan` in Odoo 18. Writing a `wink.subscription.plan` ID there would cause foreign key constraint errors or silent failures.
3. **Display Fallback**: The `request_detail` page was not reading `order.wink_plan_id` (where bundle plans are actually stored) and instead fell back to native pricing fields which were empty, causing the UI to default to the baseline tier name without the recurrence interval.

**Fix Implemented:**
- **Controller Lookup Added**: Added `'wink.subscription.plan'` to the list of searchable models in `submit_request` for bundles.
- **Reference Bypass**: Bypassed setting `order.recurrence_id` for `wink.subscription.plan` objects to prevent foreign key issues, relying exclusively on `wink_plan_id`.
- **Display Logic Fixed**: Updated `request_detail` in `controllers/request.py` to check `order.wink_plan_id` first when determining the `retainer_plan` for display.

**Validation:**
Verified that `wink.subscription.plan` selections are securely preserved, stored in `wink_plan_id`, and correctly displayed on the request detail portal page. and second activation can each have different employees stored on respective lines.

---

### WF-BND-002 — Docs required per activated service only

- **Severity:** High
- **Repro steps:** 1) Bundle with two child services A and B; A has required doc "Doc A", B has "Doc B". 2) Confirm order. 3) Upload only "Doc A", approve it. 4) Try to activate service B.
- **Actual:** Order-level document list shows union of all requirements (A + B). Activation of B does not check B's docs only; activation may succeed or gate may use full union (depends on where gate runs).
- **Expected:** Activation of an entitlement (service product P) must require that **all required document submissions for P** are uploaded and approved. If any are missing, block activation with a clear message and link to the document upload page.
- **Root cause:** No activation-time check scoped to `entitlement.service_product_id` required docs. `_wink_document_requirements()` returns union of all child services for the whole order.
- **Proposed fix plan:**
  1. Add helper on `sale.order`: `_wink_required_docs_approved_for_product(product)` returning `(bool, list_of_pending_doc_names)` for that product's required docs only (using `order.document_submission_ids` and product's `kuec_document_ids` where requirement == 'required').
  2. In `wink.bundle.entitlement.action_activate()`: before creating the line, call `order._wink_required_docs_approved_for_product(self.service_product_id)`. If not approved, raise UserError listing pending doc names and e.g. "Upload and get approval from the request's Documents section before activating."
  3. Portal: before showing "Activate" or when POST activate fails with this error, display message with link to `/my/requests/<order_id>/documents` (or equivalent). Optionally in entitlement card, show "Required documents: …" and "Upload documents" link when not approved.
- **Validation checklist:**
  - [ ] Activate service A without A's required doc uploaded → blocked with message listing doc name(s) and link to upload.
  - [ ] Upload and approve A's doc → activate A succeeds.
  - [ ] Activate B without B's doc → blocked; after B's doc approved → activate B succeeds.
  - [ ] Order-level Compliance/Documents section can still show union for display; gate is per-activation only.

---

### WF-BND-003 — Task stage gate checks docs for task.sale_line_id product

- **Severity:** High
- **Repro steps:** 1) Bundle order; activate one child service (creates SO line + task). 2) Ensure required docs for **other** child services are missing but required docs for **this** activated product are approved. 3) Move task from initial stage (e.g. New) to next stage.
- **Actual:** Gate uses `task.sale_order_id._wink_all_required_docs_approved()` which for bundles returns union of all child services' required docs. Task is blocked even if the activated service's docs are complete.
- **Expected:** When the task is linked to an activated bundle line (`task.sale_line_id` set and `sale_line_id.wink_entitlement_id` set), the stage gate should check required docs **only for that line's product** (`task.sale_line_id.product_id.product_tmpl_id`). Error message must list user-friendly document names (no record repr).
- **Root cause:** `project_task.write()` (stage change) always calls `order._wink_all_required_docs_approved()` without considering `task.sale_line_id` and activated-line scope.
- **Proposed fix plan:**
  1. In `project.task` write (stage_id change): if `task.sale_line_id` and `task.sale_line_id.wink_entitlement_id`, get product = `task.sale_line_id.product_id.product_tmpl_id` and call `order._wink_required_docs_approved_for_product(product)` (same helper as WF-BND-002). Else (standalone or no sale_line_id) keep current `_wink_all_required_docs_approved()`.
  2. Ensure error message uses the list of pending doc **names** (strings) from the helper; no `str(recordset)`.
- **Validation checklist:**
  - [ ] Task from activated bundle line: moving stage checks only that product's required docs; pending names in error are readable.
  - [ ] Standalone order task: unchanged behavior (all order required docs).
  - [ ] Task with sale_line_id but no wink_entitlement_id: treat as order-level or that product if definable.

---

### WF-BND-004 — Completion derived from tasks closure

- **Severity:** Medium
- **Repro steps:** 1) Bundle order; activate one entitlement (creates SO line + task). 2) Close the task (move to a "Done" or closed stage). 3) View request detail → Included Services / activations.
- **Actual:** No explicit "completion" state per activation; user sees "Activated" and qty used but not "Complete" vs "In progress."
- **Expected:** Activation is "complete" when all tasks linked to that activation's sale.order.line are in a closed stage. Show this in the portal (e.g. "Complete" badge or progress) in request detail for each entitlement / activated line.
- **Root cause:** No computed "completion" for an activated line; project.task stage is not exposed per line in portal.
- **Proposed fix plan:**
  1. Add computed (or method) on `sale.order.line`: e.g. `wink_activation_complete` True when line has `wink_entitlement_id` and all tasks with `sale_line_id = this line` are in a closed stage (stage.fold or explicit closed-type flag per Odoo project).
  2. Expose in portal: for each entitlement show its `activated_line_ids`; for each line show completion (e.g. "Complete" if `wink_activation_complete` else "In progress"). Use precomputed values in controller to avoid ORM in QWeb.
- **Validation checklist:**
  - [ ] Request detail shows each activated line with "Complete" or "In progress" based on linked tasks.
  - [ ] When all tasks for that line are closed, display shows Complete.
  - [ ] Entitlement with qty_entitled=2 and two activated lines: each line has its own completion.

---

### WF-BND-005 — Validate repeated activation; fix if broken

- **Severity:** Medium
- **Repro steps:** 1) Bundle with one entitlement qty_entitled=2. 2) Activate first time → success. 3) Click Activate again for same entitlement.
- **Actual:** Either second activation succeeds (qty_activated becomes 2, state stays available until 2>=2) or is incorrectly blocked (e.g. UI hides button after first activation, or backend raises).
- **Expected:** Second activation succeeds; after second activation state becomes fully_activated and button is no longer shown. No double-count or wrong counter.
- **Root cause:** To be validated: `action_activate` checks `qty_activated >= qty_entitled` and increments `qty_activated`; portal shows "Activate" when `ent.state == 'available'`. If state is computed correctly, repeated activation should work. Possible bugs: state not updated, button visibility wrong, or entitlement search in controller too strict (e.g. state='available' excludes after first activation if state were wrong).
- **Proposed fix plan:**
  1. Validate: ensure `_compute_state` sets `fully_activated` only when `qty_activated >= qty_entitled`; after first activation qty_activated=1, so state stays 'available' if qty_entitled=2.
  2. Portal: ensure "Activate" is shown only when `ent.state == 'available'` (and optionally when docs/employees are satisfied per WF-BND-001/002).
  3. If second activation is blocked: check controller search (e.g. `state='available'`); ensure no extra condition that wrongly excludes the entitlement after first activation. Fix any incorrect counter or UI logic.
- **Validation checklist:**
  - [ ] qty_entitled=2: first Activate → 1/2 used, Activate still visible; second Activate → 2/2 used, "✓ Activated" / fully_activated, no Activate button.
  - [ ] No duplicate SO lines; qty_activated matches number of activated_line_ids.

---

### Implementation summary (FB-006 / WF-BND)

| Issue | Status | Summary | Changed files |
|-------|--------|---------|---------------|
| **WF-BND-001** | Verified Done | `sale.order.line`: added `wink_selected_employee_ids` (M2M). `action_activate(employee_ids=None)` stores employees on created line; requires employee_ids when `requires_employee_selection`. Portal: GET activation form when employees required (service name, qty, docs status, employee checklist); POST same URL; "Activate" links to form when required else direct POST. `project.task` create: prefer `sale_line.wink_selected_employee_ids` if set, else entitlement, else order. | `models/sale_order_line.py`, `models/wink_bundle_entitlement.py`, `models/project_task.py`, `controllers/request.py`, `views/website_templates/request_templates.xml` |
| **WF-BND-002** | Verified Done | `sale.order._wink_required_docs_approved_for_product(product_tmpl)` returns (ok, missing_names). `action_activate()` calls it before creating line; raises UserError with doc names + instruction to upload. Activation form shows pending_docs and link to Documents when not ok. Request detail passes `activation_error` from redirect for inline alert. | `models/kuec_service_request.py`, `models/wink_bundle_entitlement.py`, `controllers/request.py`, `views/website_templates/request_templates.xml` |
| **WF-BND-003** | Verified Done | `project.task` write (stage change): when `task.sale_line_id` and `sale_line_id.wink_entitlement_id`, call `order._wink_required_docs_approved_for_product(task.sale_line_id.product_id.product_tmpl_id)`; else `_wink_all_required_docs_approved()`. Error message uses pending doc names (strings). | `models/project_task.py` |
| **WF-BND-004** | Verified Done | In `request_detail`: for each entitlement, batch-query tasks by `sale_line_id in activated_line_ids`; for each line set `is_complete` when all linked tasks have `stage_id.fold == True`. Pass `bundle_activation_map` (ent.id → list of {line_id, name, is_complete}). Template shows "Complete" / "In progress" badge per activated line. | `controllers/request.py`, `views/website_templates/request_templates.xml` |
| **WF-BND-005** | Verified Done | No code change. `_compute_state`: fully_activated when qty_activated >= qty_entitled. Controller search uses `state='available'`; after first activation state remains available until qty_activated >= qty_entitled. Portal shows Activate when `ent.state == 'available'`. | — |

**Changed files → Issue ID**

| File | Issue IDs |
|------|-----------|
| `kuec_service_catalogue/models/sale_order_line.py` | WF-BND-001 |
| `kuec_service_catalogue/models/wink_bundle_entitlement.py` | WF-BND-001, WF-BND-002, WF-BND-005 |
| `kuec_service_catalogue/models/project_task.py` | WF-BND-001, WF-BND-003 |
| `kuec_service_catalogue/models/kuec_service_request.py` | WF-BND-002, WF-BND-003 |
| `kuec_service_catalogue/controllers/request.py` | WF-BND-001, WF-BND-002, WF-BND-004 |
| `kuec_service_catalogue/views/website_templates/request_templates.xml` | WF-BND-001, WF-BND-002, WF-BND-004 |

**Manual validation checklist (FB-006)**

- [ ] **WF-BND-001:** Child service with `requires_employee_selection`: "Activate" opens form; select ≥1 employee → submit → line has `wink_selected_employee_ids`; task shows those employees. Without employee requirement: direct "Activate" creates line; task gets entitlement/order employees or empty.
- [ ] **WF-BND-002:** Activate service A without A's required doc → blocked with message listing doc name(s); link to Documents. Upload and approve A's doc → activate A succeeds. Activate B without B's doc → blocked; after B's doc approved → activate B succeeds.
- [ ] **WF-BND-003:** Task from activated bundle line: move out of New stage checks only that line's product docs; error lists doc names. Standalone task: unchanged (order-level docs).
- [ ] **WF-BND-004:** Request detail shows each activated line with "Complete" or "In progress". Close all tasks for that line → badge shows "Complete".
- [ ] **WF-BND-005:** qty_entitled=2: first Activate → 1/2 used, Activate still visible; second Activate → 2/2 used, "✓ Activated", no Activate button. No duplicate lines.
- [ ] **Isolation:** User cannot activate another partner's entitlement (controller filters by `partner_id child_of commercial_partner_id`).

---

### Follow-up: Bundle activation — completion display, reactivation naming, error handling (Q1 / Q2)

**Q1 — "In progress" when task already done; reactivation task name**

- **Completion display:** Portal shows "Complete" when all tasks for that activation's sale order line are in a **closed** stage. Completion is derived from `task.stage_id.fold` (Odoo "Fold in Kanban" = closed). If the backend "Done" stage does not have **Fold in Kanban** checked, the portal will keep showing "In progress". **Fix applied:** Completion logic now also treats a stage as done when its name (lowercased) contains one of: `done`, `cancelled`, `closed`, `complete`. So even if the project's Done stage has `fold=False`, the portal will show "Complete" once the task is in that stage.
- **Reactivation:** When `qty_entitled > 1`, the same entitlement can be activated again (e.g. second activation). **Fix applied:** The new SO line (and thus the new task) is named with an activation index: first activation = service name (e.g. "IT Infrastructure Audit"), second = "IT Infrastructure Audit (2)", third = "IT Infrastructure Audit (3)", etc. So reactivation creates a distinct, predictable task name.

**Q2 — Form organization**

- The bundle section in request detail lists each entitlement and, for each, the list of activations (lines) with "Complete" / "In progress" badges. **Fix applied:** Each activation row now shows an explicit label "Activation 1: &lt;line name&gt;", "Activation 2: ..." when there are multiple, so it is clear which badge applies to which activation. Layout uses `d-flex flex-column gap-1` for clearer separation.

**Error — `AttributeError: 'UserError' object has no attribute 'name'`**

- When activation is blocked (e.g. required documents missing), the code raised `UserError` with a message, then in the exception handler tried to use `e.name` to build the redirect URL. `UserError` in Odoo has no `.name` attribute; the message is in `args[0]` or via `str(e)`. **Fix applied:** In `controllers/request.py` (`bundle_activate_request`), the handler now uses `msg = str(e)` (and reads `activation_error` from `request.params` as fallback in `request_detail`) so the user sees the document message in the portal alert and no secondary AttributeError is raised.

---

### Reactivation not possible (bundle activation)

- **Symptom:** User cannot activate the same bundle service a second time (reactivation).
- **Cause 1 (controller):** `bundle_activate_request` looked up the entitlement with `('state', '=', 'available')`. The stored computed `state` can be stale or, when `qty_entitled=1`, becomes `fully_activated` after the first activation so the route returns 404 and the button disappears.
- **Cause 2 (tier config):** Entitlement `qty_entitled` comes from the bundle tier item's **Quantity** (`wink.bundle.tier.item.qty`). Default is 1, so only one activation is allowed unless the admin sets Quantity to 2+ for that service in the tier.
- **Fix applied:**
  1. **Controller:** Look up entitlement by `id` and `order_id` only. Allow activation only when `qty_activated < qty_entitled`; if already fully used, redirect with a clear message (e.g. "This service has already been fully activated (X/X used).").
  2. **Template:** Show the "Activate" button when `ent.qty_activated < ent.qty_entitled` (and order in sale/done) instead of relying on `ent.state == 'available'`. Show "✓ Activated" when `ent.qty_activated >= ent.qty_entitled`.
- **To allow reactivation:** In **Wink → Bundle Packages → [Bundle] → Tier → Included Services**, set **Quantity** to 2 (or more) for the service that may be activated multiple times. Each entitlement then gets `qty_entitled=2` and the portal allows a second activation (reactivation).

---

## FB-007 — Tags + Ribbon visibility

**Source:** Team feedback. Scope: `custom/kuec_portal_foundation`, `custom/kuec_service_catalogue`. Portal UI only.

| Issue ID    | Description | Severity | Status |
|-------------|-------------|----------|--------|
| **UI-TAG-001** | Show product tags on `/services` cards and `/services/<id>` detail page filter out ribbon tag | Medium | Implemented |
| **UI-TAG-002** | Show ribbon tag (`product.tag.is_ribbon=True`) as visible ribbon on service cards and detail page, ensure styling matches Lovable parity | Medium | Implemented |

### Implementation Details:
*   **Gap Documented:** The templates and styles previously existed but lacked the specific deduplication `lambda t: t.id != product.wink_ribbon_tag_id.id` filter when displaying normal chips, causing the ribbon tag to display both as a ribbon and as a pill. The required issue markers (`<!-- UI-TAG-001 -->`/`/* UI-TAG-001 */`) were also missing.
*   **Re-Implemented & Verified:** Applied the lambda filter to the `t-foreach` loops in `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` for both the cards and the detail view. Added required issue markers to both the XML template and `kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss`.

**Changed files → Issue ID**
| File | Issue IDs |
|------|-----------|
| `kuec_service_catalogue/views/website_templates/wink_catalogue_page.xml` | UI-TAG-001, UI-TAG-002 |
| `kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss`| UI-TAG-001, UI-TAG-002 |

**Validation checklist (FB-007)**
- [ ] Render `/services` and check that any service designated with a `wink_ribbon_tag_id` successfully renders a ribbon, but the same tag is NOT shown as a pill in the tag list.
- [ ] Render `/services/<id>` of a service with a ribbon tag and ensure the same duplication filtering applies successfully preventing duplicate pills.

---

## BUG 1 — WF-BUNDLE-UI-006
**Status:** ✅ Resolved
**Severity:** High (Crash)
**Area:** Portal - My Bundles

**Description:**
Navigating to the My Bundles page throws a `TypeError: not enough arguments for format string`.

**Root Cause:**
In `custom/kuec_service_catalogue/views/website_templates/request_templates.xml` at line 2019, the progress bar used standard Python string interpolation with a literal `%` for the width percentage (`t-att-style="'width: %s%%; ...' % bd['progress_pct']"`), causing QWeb to crash on rendering the literal `%`.

**Fix Implemented:**
Switched to QWeb's `t-attf-style` interpolation which is safer and cleaner:
`t-attf-style="width: {{ bd['progress_pct'] }}%; background: linear-gradient(90deg, #6366f1, #818cf8);"`

**Validation:**
Verified via code logic that standard string interpolation is removed, preventing the TypeError.

---

## BUG 2 — WF-BUNDLE-PLAN-002
**Status:** ✅ Resolved
**Severity:** Medium (Data Loss / Logic Error)
**Area:** Bundle Configurator & Request Detail

**Description:**
When a customer selects "Gold Annual" (or any non-default plan) during the bundle configuration, the system processes it but displays "Gold Monthly" (the default) in the review and detail pages.

**Root Cause:**
1. **Model Mismatch in Controller**: In `controllers/request.py`'s `submit_request`, the `selected_pricing_id` passed from the front end for Bundles corresponds to a `wink.subscription.plan` ID. However, the controller was only searching `['product.pricing', 'sale.subscription.pricing']` to validate the ID. It failed to find it, causing it to fall back or nullify the selection.
2. **Foreign Key Error Risk**: The controller was attempting to write the validated pricing ID into `sale.order.recurrence_id`, which strictly points to `sale.subscription.plan` in Odoo 18. Writing a `wink.subscription.plan` ID there would cause foreign key constraint errors or silent failures.
3. **Display Fallback**: The `request_detail` page was not reading `order.wink_plan_id` (where bundle plans are actually stored) and instead fell back to native pricing fields which were empty, causing the UI to default to the baseline tier name without the recurrence interval.

**Fix Implemented:**
- **Controller Lookup Added**: Added `'wink.subscription.plan'` to the list of searchable models in `submit_request` for bundles.
- **Reference Bypass**: Bypassed setting `order.recurrence_id` for `wink.subscription.plan` objects to prevent foreign key issues, relying exclusively on `wink_plan_id`.
- **Display Logic Fixed**: Updated `request_detail` in `controllers/request.py` to check `order.wink_plan_id` first when determining the `retainer_plan` for display.

**Validation:**
Verified that `wink.subscription.plan` selections are securely preserved, stored in `wink_plan_id`, and correctly displayed on the request detail portal page.

---

## FB-008 — Review Page & Plan Compare Visibility (UI-REV)

**Source:** Team feedback. Scope: `custom/kuec_portal_foundation`, `custom/kuec_service_catalogue`. Portal UI only.

| Sub-ID | Description | Classification | Severity | Issue ID |
|--------|-------------|----------------|----------|----------|
| FB-008.1 | Plan name and compare buttons are not visible. | **BUG** | High | **UI-REV-001** |
| FB-008.2 | Review Your Request page has poor design and amount is missing. | **BUG** | High | **UI-REV-002** |
| FB-008.3 | After review, next step should go to payment. | **ENHANCEMENT** | Medium | **UI-REV-003** |

---

#### UI-REV-001 — Plan name and compare buttons not visible

- **Classification:** BUG — STILL OPEN (partially)
- **Severity:** High
- **Verified:** 2026-03-07 (code audit)

**Plan names:**
- For standalone retainer products: plan names ARE visible on service detail page (`wink_catalogue_page.xml` lines ~397-418). Each plan card renders `plan['plan_name']` inside `.wink-plan-card` labels when `len(subscription_plans) > 1`. **Verified Done.**
- For bundle products on service detail: a note says "Select your tier and billing cycle on the next step." Plans are selected inside the wizard. **By design; no gap.**

**"Compare Plans" button:**
- A `<div class="wink-compare-toggle">` with `<a class="wink-compare-link">Compare Plans</a>` exists in `request_templates.xml` at line 591 — rendered inside the bundle tier selector section only.
- **CRITICAL GAP:** The classes `.wink-compare-toggle` and `.wink-compare-link` have **no CSS definition** in `wink_portal_lovable.scss` (verified grep: no matches).
- **CRITICAL GAP:** There is **no JavaScript handler** for the compare link in `wink_catalogue.js` or embedded script (verified grep: no matches). Clicking the link does nothing.
- **For standalone retainer on service detail:** There is no "Compare Plans" button or link at all.

**Root cause:**
1. The compare HTML was added to the bundle wizard template but without CSS and JS to make it functional.
2. Standalone retainer service detail has no compare functionality.

**Fix plan (UI-REV-001):**
1. In `wink_portal_lovable.scss`: add styles for `.wink-compare-toggle` (inline, subtle link appearance) and `.wink-compare-link` (text-primary, underline, cursor-pointer, font-size small). Add styles for a collapsible `.wink-compare-table` (hidden by default, transitions in).
2. In `request_templates.xml` (bundle wizard): add a `<div class="wink-compare-table d-none">` below the tier cards with a side-by-side feature comparison across tiers; the `.wink-compare-link` click toggles `d-none` on this div.
3. JS: In embedded `<script>` block (or `wink_catalogue.js`): `document.querySelectorAll('.wink-compare-link')` → on click toggle the adjacent `.wink-compare-table` visibility.
4. For standalone retainer detail page: optionally add a static "All plans include the same features — choose your billing period" note below the plan cards (already partially present). No interactive compare table needed if only one tier.

**Risk:** Low. Visual/JS only. No model or route change.
**Validation:** Bundle wizard: click "Compare Plans" → comparison table expands showing tier features side by side. Click again → collapses. Retainer detail: plan cards visible with names and prices.

---

#### UI-REV-002 — Review Page bad design + amount missing

- **Classification:** VERIFIED FIXED (via CR-6 implementation)
- **Verified:** 2026-03-07 (code audit)

**Evidence:**
- `controllers/request.py` (step 3 render path, ~line 473-559): `review_display` dict is built with `type_label` (One-time / Retainer / Bundle), `tier_name`, `plan_name`, `price_str`, `currency_symbol`, `employee_names`.
- `request_templates.xml` (lines ~288-349): Step 3 "Review Your Request" card uses `dl.row` layout showing: Service, Type, Tier (if bundle), Plan (if set), Estimated Amount (if `price_str` set), Start Date, Notes, Employees. Currency symbol + formatted price shown in green bold.
- This was implemented under gap CR-6 (WINK_PORTAL_GAP_CLOSURE_REPORT.md).

**Validation checklist:**
- [ ] Bundle with tier + annual plan: Review step shows Type=Bundle, Tier=Gold, Plan=Annual, Estimated Amount=AED X,XXX.XX
- [ ] Retainer with monthly plan: Review step shows Type=Retainer, Plan=Monthly, Estimated Amount=AED X,XXX.XX
- [ ] One-time service: Review step shows Type=One-time, Estimated Amount=AED X,XXX.XX
- [ ] Employees selected: shown as blue rounded-pill badges with names

---

#### UI-REV-003 — After review should go to payment

- **Classification:** ENHANCEMENT / workflow change
- **Severity:** Medium
- **Issue:** After review, the next step should go to payment. (Currently logged for documentation only, no implementation).


### UI-REV-003 — After review should go to payment
- **Current Flow:** The Review step (Step 3) displays the request details and features a "Submit Request" button. Upon clicking this, the system generates the Sale Order / Sale Order Lines based on the selection and redirects the user to the Request Detail portal page. The actual payment prompt is either deferred or manual.
- **Proposed Flow:** After the Review step, the system immediately proceeds to a payment gateway instead of generating the request detail portal view.
- **Impact Analysis (NOT TO BE IMPLEMENTED UNTIL APPROVED):**
  - **Hidden Pricing:** For services with `price_visibility == 'hidden'`, forcing immediate payment is incompatible, as these rely on sales agents providing manual quotes before arbitrary payment can be taken. A conditional logic branch would be strictly required.
  - **Quotations:** Moving to payment right away modifies the core behavior of creating `sale.order` in a "draft" quotation state. If the payment is successful, the order would transition to "sale" (confirmed).
  - **Bundle Flow / Retainers:** Complex bundles with conditional recurring pricing or usage-based pricing might need explicit backend confirmation or signature workflows. Immediate payment would bypass this.
  - **Partial Payment:** If a service has a default partial payment term (e.g., "50% deposit"), the checkout flow must accurately extract the `amount_residual` based on down payment rules, rather than prompting the user for the full order amount up-front.

---

## MASTER VERIFICATION STATUS TABLE — 2026-03-07

> Fresh code audit performed. The table below reflects the true status of all tracked issues.

| Issue ID | Current Status | Code Verified | Runtime Tested | Evidence Files | Notes |
|----------|---------------|---------------|----------------|----------------|-------|
| **WF-BND-001** | Verified Done | Yes | No | `models/sale_order_line.py`, `models/wink_bundle_entitlement.py`, `models/project_task.py`, `controllers/request.py` | `wink_selected_employee_ids` M2M on SOL; `action_activate(employee_ids)` stores on line; task.create prefers line employees |
| **WF-BND-002** | Verified Done | Yes | No | `models/kuec_service_request.py:279`, `models/wink_bundle_entitlement.py:171` | `_wink_required_docs_approved_for_product()` called before line creation; raises UserError with doc names |
| **WF-BND-003** | Verified Done | Yes | No | `models/project_task.py:70-84` | Stage-gate scopes to `sale_line.product_id.product_tmpl_id` when `wink_entitlement_id` present |
| **WF-BND-004** | Verified Done | Yes | No | `controllers/request.py:1346-1387` | `bundle_activation_map` with `is_complete` from `stage.fold` + name keywords; passed to template |
| **WF-BND-005** | Verified Done | Yes | No | `models/wink_bundle_entitlement.py:108-116`, `controllers/request.py:2156` | `qty_activated < qty_entitled` check; SQL atomic increment; no artificial blocking |
| **UI-TAG-001** | Verified Done | Yes | No | `wink_catalogue_page.xml:9-12, 281-284`, `wink_portal_lovable.scss:292-327` | Diagonal ribbon with inline color; parent has `overflow:hidden`; correct z-index |
| **UI-TAG-002** | Verified Done | Yes | No | `wink_catalogue_page.xml:50-52, 305-312` | Lambda dedup `t.id != product.wink_ribbon_tag_id.id` applied in both card and detail |
| **WF-BUNDLE-UI-006** | Verified Done | Yes | No | `request_templates.xml:2030` | `t-attf-style="width: {{ bd['progress_pct'] }}%..."` — no `%` format crash |
| **WF-BUNDLE-PLAN-002** | Verified Done | Yes | No | `controllers/request.py:895, 925-929, 1266-1268` | `wink.subscription.plan` in model lookup; `is_fake_plan` bypasses `recurrence_id`; `wink_plan_id` checked first in `request_detail` |
| **UI-BUG-002** | Verified Done | Yes | No | `controllers/request.py:709-718, 802-809` | `/my/requests/register/thanks` route; redirect from `register_and_request` to thanks page |
| **UI-BUG-003** | Verified Done | Yes | No | `controllers/request.py:262-270, 337-346` | Skip to step=3 when `not product.requires_employee_selection`; plan not required for non-subscription |
| **UI-BUG-004** | Verified Done | Yes | No | `controllers/request.py:1427-1444` | `amount_due_display` from `sum(invoice.amount_residual)`; `has_partial_payment`; `next_due_date` |
| **UI-BUG-005a** | Verified Done | Yes | No | `request_templates.xml` | Website currency used for price display |
| **UI-BUG-005b** | Verified Done | Yes | No | `wink_portal_lovable.scss:284-290` | `.wink-plan-card:has(input:checked)` border + background highlight |
| **UI-BUG-005c** | Verified Done (by design) | Yes | No | `controllers/request.py:114-157` | Already-active retainer shows change-plan page, not new request |
| **UI-BUG-005d** | Verified Done | Yes | No | `controllers/portal.py` | Cancelled orders included in My Requests domain |
| **UI-BUG-005e** | Verified Done | Yes | No | `controllers/request.py:119, 398` | `('state', '!=', 'cancel')` in active-sub searches |
| **UI-BUG-005f** | Verified Done | Yes | No | `request_templates.xml` | Bundle total shown using selected tier price |
| **UI-REV-001** | Partially Fixed — STILL OPEN | Yes | No | `request_templates.xml:590-593`, `wink_portal_lovable.scss` | Plan names visible on service detail. Compare link HTML exists in bundle wizard but NO CSS and NO JS — functionally broken. No compare for standalone retainer. |
| **UI-REV-002** | Verified Done | Yes | No | `controllers/request.py:473-559`, `request_templates.xml:288-349` | `review_display` dict with type_label, tier_name, plan_name, price_str, currency_symbol, employee_names all in step 3 |
| **UI-REV-003** | Enhancement — Not Implemented | N/A | N/A | — | Documented only; complex workflow implications; requires explicit approval |
| **EPIC7-DASH-001** | Missing — Not Implemented | Yes | No | — | No dashboard KPI code or templates anywhere in codebase |
| **WF-BUG-001** | Documented Only | N/A | N/A | — | Backend: Wink tab hidden when `sale_ok=False` or `type != 'service'` |
| **WF-BUG-002** | Documented Only | N/A | N/A | — | Backend: Block quotation confirm without required docs |
| **WF-BUG-003** | Documented Only | N/A | N/A | — | Backend: Mutual exclusivity for Governmental/Non-Governmental |
| **WF-BUG-004** | Documented Only | N/A | N/A | — | Backend: Retainer delivery model auto-checks subscription flag |

---

## PRIORITY LIST FOR NEXT IMPLEMENTATION STEPS

### Phase 1 — Bundle (complete)
All WF-BND-001..005 and WF-BUNDLE-UI-006, WF-BUNDLE-PLAN-002 are **Verified Done**. No new work needed.

### Phase 2 — Standalone Project and Standalone Retainer (complete)
UI-BUG-003 and WF-BUNDLE-PLAN-002 are **Verified Done**. No new work unless runtime reveals regressions.

### Phase 3 — Open Portal Items (priority order)

| Priority | Issue ID | Description | Effort |
|----------|----------|-------------|--------|
| 1 | **UI-REV-001** | Compare Plans: add CSS + JS for compare link in bundle wizard | Low |
| 2 | **EPIC7-DASH-001** | Customer Portal Dashboard KPIs (orders, subscriptions, completed, receivable, renewals) | High |
| 3 | **WF-BUG-001** | Backend: hide Wink tab when `sale_ok=False` or product type is not service | Low |
| 4 | **WF-BUG-002** | Backend: block SO confirmation without required docs | Medium |
| 5 | **WF-BUG-003** | Backend: mutual exclusion for Gov/Non-Gov classification | Low |
| 6 | **WF-BUG-004** | Backend: auto-check subscription when Delivery Model = Retainer | Low |
| 7 | **UI-REV-003** | Enhancement: redirect to payment after review (requires product owner approval) | High |
| 8 | **FB-001d** | Needs Validation: attachments in Required Documents appear in Compliance section | Low |
