# KUEC Service Catalogue (`kuec_service_catalogue`)

## Purpose
Provides the WINK service catalogue and portal for KUEC customers. Manages service products, bundle subscriptions, employee selection, government charges, and the full request-to-delivery workflow.

## Key Features
- Service catalogue portal with department/nature filtering and ribbon tags
- Bundle subscriptions with tier-based entitlements and per-service activation
- Employee selection per service request and bundle activation
- Government charges (known/unknown mode) with automatic invoice generation
- Per-employee government charge calculation: `base + (employees × per_emp_rate)`
- Portal payment flow for government charges (direct or coordinator-confirmed)
- Project/task auto-creation via `sale_project` integration
- Customer satisfaction ratings on folded project stages
- eWallet integration for portal payments
- Bundle import wizard for coordinator bulk-setup

## Dependencies
- `sale_management`, `sale_project`, `project`, `website_sale`, `portal`
- `mail`, `account`, `product`
- `kuec_employee_directory` (internal employee directory)

## Installation
```bash
docker exec odoo_18_ai odoo -i kuec_service_catalogue -d PORTAL --no-http --stop-after-init
```

## Access Roles
| Role | Access |
|---|---|
| Portal User | View catalogue, submit requests, activate bundle services, pay invoices |
| Coordinator (internal) | Manage entitlements, confirm gov charges, set prices |
| Admin | Full access — product config, bundle setup, pricing |

## Configuration
1. Enable **Available on Wink** on product templates to publish to portal.
2. Configure **Wink** tab: department, nature, delivery model, commercial structure.
3. For government charges: enable **Requires Government Charges**, then toggle **Charge Amount is Fixed** for known vs unknown mode.
4. Bundle products: set **Is Bundle**, configure tiers and child services.

---

## Changelog

### 18.0.2.24.0 — 2026-03-28
- [FIX] Portal file upload: accumulate files across selections using DataTransfer API; add per-chip × remove button — re-selecting files no longer wipes previous choices
- [FIX] Activation modal: add `modal-dialog-scrollable` to all portal modals so overflowing content is reachable on small viewports
- [UPDT] T&C per product: add `wink_terms_html` field on `product.template`; portal T&C link passes `?product_id=X` when product has own T&C, controller falls back to global company T&C
- [UPDT] Satisfaction Rate: rename "Label" column to "Satisfaction Rate" in CX report; map 1–5 score to 5-point labels (Extremely Unsatisfied → Extremely Satisfied) via `wink_satisfaction_label` computed field on `rating.rating`

### 18.0.2.23.0 — 2026-03-24
- [ADD] `/wink/packages` route: smart landing page — 1 bundle → 302 redirect to tier-selection; 2+ bundles → full-width packages listing with tier cards per bundle
- [UPDT] "Packages Only" catalogue button now links to `/wink/packages` instead of filter param
- [ADD] `wink_packages_page.xml` template: responsive multi-row bundle cards with tier pricing, Most Popular badge, service count, and direct CTA

### 18.0.2.22.10 — 2026-03-24
- [FIX] request_templates.xml: removed orphaned `</t>` left after ps!=cancelled wrapper was removed — fixes XMLSyntaxError (div/t mismatch at line 2910) that broke all portal request pages

### 18.0.2.22.9 — 2026-03-24
- [FIX] Standalone/retainer cancelled page: service details card now shows for all stages — removed ps!=cancelled wrapper; ps==active block closes correctly before service details
- [FIX] Redundant "This request has been closed" banner suppressed for non-bundle; bundles retain it

### 18.0.2.22.8 — 2026-03-24
- [FIX] Request detail page: show service details and communication history even when cancelled — removed ps != 'cancelled' guard from action bar; added "Service Cancelled" card with credit note reference
- [FIX] Bundle confirmed banner no longer shows after churn

### 18.0.2.22.7 — 2026-03-24
- [FIX] Coordinator confirm cancellation: call _set_closed_state() directly instead of set_close() — set_close() only churns when end_date <= today, leaving active subscriptions open

### 18.0.2.22.6 — 2026-03-24
- [FIX] action_wink_mark_cancellation_processed: always compute credit note via _wink_compute_proration() (removes dead policy guard); churn subscription via set_close() on confirm

### 18.0.2.22.5 — 2026-03-24
- [FIX] Standalone retainer/flexible cancel: _wink_compute_proration() now computes Story 1.12 refund (monthly_price/30 × remaining_days) from sale.subscription.pricing — same as bundle flow
- [FIX] Retainer cancel page: show_refund now driven by proration result, not stub policy; formula note and remaining days displayed

### 18.0.2.22.4 — 2026-03-24
- [FIX] _wink_get_tier_monthly_price(): filter sale.subscription.pricing by product_variant_ids (Many2many) to get variant-specific price, not just first row on the template

### 18.0.2.22.3 — 2026-03-24
- [FIX] _wink_get_tier_monthly_price() restored to read from sale.subscription.pricing — reference plan first, then 1-month billing period plan, fallback to tier.price_monthly
- [FIX] Upgrade/downgrade zero-amount note now shows actual cause (price not configured vs no remaining days)

### 18.0.2.22.2 — 2026-03-24
- [UPDT] Downgrade portal page: formula note and remaining-days display added to tier cards (matches upgrade template treatment)

### 18.0.2.22.1 — 2026-03-24
- [FIX] Simplified price source: _wink_get_tier_monthly_price() now reads tier.price_monthly directly — removes complex sale.subscription.pricing lookup
- [UPDT] Bundle form: price_monthly now editable inline on the tier list (no need to open individual tier forms)
- [UPDT] product_variant_id column moved to optional/hidden on tier list

### 18.0.2.22.0 — 2026-03-24
- [UPDT] Story 1.12: Bundle refund/charge/credit now uses monthly standard price exclusively (`sale.subscription.pricing` reference plan → 1-month plan → `tier.price_monthly` fallback)
- [UPDT] New `_wink_get_tier_monthly_price()` replaces `_wink_get_tier_effective_price()` — queries `sale.subscription.pricing` correctly (annual discount always forfeited)
- [FIX] `_wink_bundle_remaining_days()`: period start always derived from `plan_id.billing_period` relative to `next_invoice_date` — fixes stale value after subscription renewal
- [FIX] Upgrade charge formula: `(new_monthly − old_monthly) / 30 × remaining_days`
- [FIX] Downgrade credit formula: `(old_monthly − new_monthly) / 30 × remaining_days`
- [FIX] Cancellation refund formula: `(monthly_price / 30) × remaining_days`
- [FIX] `wink_cancellation_processed_by` now set on bundle self-service cancellation
- [FIX] Invoice and credit note lines now include correct `taxes_id` from product
- [FIX] Credit note `sale_line_ids` now links to original subscription line only (not upgrade charge lines)
- [UPDT] Removed `pro_rata` from `cancel_refund_policy` selection (Story 1.12 mandates monthly rate)
- [REF] All inline `from datetime import` and `from odoo import fields` moved to file top

### 18.0.2.21.1 — 2026-03-23
- [UPDT] Activation modal now shows a Government Charges notice when the service requires gov charges — known mode displays base amount and per-employee rate with invoice pay notice; unknown mode shows a coordinator-confirmation warning

### 18.0.2.21.0 — 2026-03-23
- [UPDT] Two-mode government charges system: known (pre-configured amount, auto-invoice on activation/request) and unknown (coordinator confirms later, portal notifies customer)
- [UPDT] Per-employee government charge field (`gov_charge_per_employee`): total = base + (selected employees × rate)
- [UPDT] Standalone request submission: auto-injects known gov charge line at submission time
- [UPDT] Portal detail page: gov charge status card with pending/confirmed/paid states and "Pay Gov. Charges" button
- [UPDT] Bundle activation: per-activation gov charge line created with correct known/unknown amounts
- [UPDT] `sale.order.line.write()` override: auto-notifies customer on chatter when coordinator sets gov charge price
- [UPDT] Targeted gov charge invoice creation (`_prepare_invoice` + `_prepare_invoice_line`) — only gov charge lines included
- [UPDT] `pay-gov-charges` portal route: reuses existing clean gov charge invoice or creates new targeted one
- [UPDT] `gov_charge_map` injected into bundle portal context for per-entitlement charge state display
