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
