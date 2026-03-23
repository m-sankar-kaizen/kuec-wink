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
