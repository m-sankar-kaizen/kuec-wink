# Upgrade / Downgrade / Cancellation Workflow — Best-of-Best Implementation Plan

**Module:** `kuec_service_catalogue`  
**Scope:** Retainer subscription plan changes and cancellation  
**Goal:** World-class, transparent, automated, and coordinator-friendly workflow

---

## 1. Current State Summary

| Aspect | Current Implementation | Gaps |
|--------|------------------------|-----|
| **Policy** | `wink.subscription.group`: allow_upgrade/downgrade/cancellation, min_days_before_change, credit policies | effective_date_policy not enforced; no per-plan restrictions |
| **Proration** | `(monthly_std_price ÷ 30) × remaining_days` | Correct formula; not shown before user commits |
| **Upgrade/Downgrade** | Link to new request form with `change_from=order_id`; creates new quote | No price preview; no clear upgrade vs downgrade; coordinator re-approval every time |
| **Cancellation** | POST to `/retainer/cancel`; sets `wink_cancellation_requested` | Manual processing; no automatic refund/wallet; no SLA |
| **Plan mapping** | `wink.subscription.plan` ↔ product.pricing via `recurrence_name_hint` | Weak linkage; `wink_plan_id` often unset |
| **UX** | Generic "Upgrade / Downgrade Plan" button | No plan comparison; no "you will pay X" or "you will receive Y credit" |

---

## 2. Target Architecture (Best-of-Best)

### 2.1 Principles

1. **Transparency first** — Customer sees exact amounts (proration, new price, credit) before committing.
2. **Automation where safe** — Immediate upgrades with payment; downgrades with credit; cancellations with policy-driven refund.
3. **Coordinator control** — Configurable approval gates; audit trail; override capability.
4. **Single source of truth** — `wink.subscription.plan` ↔ `product.pricing` explicit mapping.
5. **Policy-driven** — All behavior from `wink.subscription.group`; no hardcoding.

---

## 3. Data Model Enhancements

### 3.1 `wink.subscription.plan`

| Field | Type | Purpose |
|-------|------|---------|
| `product_pricing_id` | Many2one → product.pricing | **New.** Explicit link to Odoo recurring price (replaces fuzzy recurrence_name_hint). |
| `sequence` | Integer | Lower = lower tier (Bronze=10, Silver=20, Gold=30). Used to determine upgrade vs downgrade. |

**Migration:** Populate `product_pricing_id` from product + recurrence where possible; keep `recurrence_name_hint` as fallback for display.

### 3.2 `wink.subscription.group`

| Field | Change | Purpose |
|-------|--------|---------|
| `upgrade_requires_approval` | **New** (Boolean, default=False) | If True, upgrade creates draft quote; if False, customer pays immediately (when price known). |
| `downgrade_requires_approval` | **New** (Boolean, default=True) | If True, downgrade creates draft; if False, apply credit and switch plan at next cycle. |
| `cancellation_requires_approval` | **New** (Boolean, default=True) | If False, cancellation auto-processes per policy (refund/wallet); if True, coordinator approves. |
| `min_days_before_cancellation` | **New** (Integer, optional) | Override for cancellation only (e.g. 30 days notice). Falls back to `min_days_before_change` if not set. |

### 3.3 `sale.order`

| Field | Change | Purpose |
|-------|--------|---------|
| `wink_plan_id` | Keep | Must be set on creation for retainers (from selected product.pricing → wink.subscription.plan). |
| `wink_change_type` | **New** (Selection: 'upgrade', 'downgrade', False) | Explicit change type for reporting and automation. |
| `wink_proration_credit` | **New** (Monetary) | Stored credit from previous plan (downgrade) applied to this order. |
| `wink_proration_charge` | **New** (Monetary) | Stored charge for remaining period (upgrade) to add to this order. |

### 3.4 New: `wink.credit.wallet` (Optional — Phase 2)

| Field | Type | Purpose |
|-------|------|---------|
| `partner_id` | Many2one | Commercial partner. |
| `balance` | Monetary | Available credit. |
| `line_ids` | One2many | Credit entries (source order, amount, date, description). |

Use when `downgrade_credit_policy = 'wallet'` or `cancellation_credit_policy = 'wallet'`.

---

## 4. Workflow Design

### 4.1 Upgrade Flow (Best-of-Best)

```
Customer on Bronze (100/mo) → wants Silver (200/mo)
Remaining: 15 days
Proration credit from Bronze: (100/30)×15 = 50
Proration charge for Silver: (200/30)×15 = 100
Net to pay: 100 - 50 = 50
```

**Steps:**

1. Customer clicks **Upgrade** on portal request detail.
2. **New route:** `GET /my/requests/<id>/retainer/change-plan`  
   - Renders plan comparison page: current plan vs all other plans.
   - For each target plan: compute upgrade/downgrade, show "You will pay X" or "You will receive Y credit".
   - Enforce policy: `allow_upgrade`, `min_days_before_change`, `wink_plan_id` set.
3. Customer selects target plan (e.g. Silver).
4. **New route:** `POST /my/requests/<id>/retainer/change-plan` with `target_plan_id` (wink.subscription.plan id).
5. Backend:
   - Resolve `product.pricing` from `target_plan_id.product_pricing_id`.
   - Compute proration (credit from current, charge for new).
   - If `upgrade_requires_approval`:
     - Create new sale.order (draft) with `wink_change_from_order_id`, `wink_change_type='upgrade'`, `wink_proration_credit`, `wink_proration_charge`, line with new plan price + proration adjustment.
     - Redirect to new quote; customer approves when ready.
   - If not:
     - Create order, confirm, add proration to amount; redirect to payment. (Requires payment flow integration.)
6. On payment/approval: link subscription; coordinator (or automation) closes old subscription at period end or per `effective_date_policy`.

### 4.2 Downgrade Flow (Best-of-Best)

```
Customer on Silver (200/mo) → wants Bronze (100/mo)
Remaining: 15 days
Credit from Silver: (200/30)×15 = 100
Charge for Bronze: (100/30)×15 = 50
Net credit: 100 - 50 = 50
```

**Policy handling:**

- `downgrade_credit_policy = 'wallet'`: Add 50 to wallet; apply to future invoices.
- `downgrade_credit_policy = 'next_cycle'`: Reduce next invoice by 50.
- `downgrade_credit_policy = 'no_refund'`: No credit; just switch plan at next cycle.

**Steps:**

1. Customer clicks **Downgrade** (or "Change plan" and selects lower tier).
2. Same plan comparison page; for downgrade show "Credit: X (to wallet / next invoice)".
3. `POST /my/requests/<id>/retainer/change-plan` with `target_plan_id`.
4. If `downgrade_requires_approval`:
   - Create draft order with negative proration (credit); coordinator reviews.
5. If not:
   - Create wallet entry (if wallet) or schedule credit for next cycle.
   - Set `effective_date_policy`: immediate = end current period and start new; next_cycle = at next renewal.
6. Coordinator (or cron) applies plan change in Odoo subscription at effective date.

### 4.3 Cancellation Flow (Best-of-Best)

```
Customer on Silver (200/mo), 15 days remaining
Refund: (200/30)×15 = 100
```

**Policy handling:**

- `cancellation_credit_policy = 'refund'`: Process refund (manual or automated).
- `cancellation_credit_policy = 'wallet'`: Add to wallet.
- `cancellation_credit_policy = 'no_refund'`: No refund; subscription ends at period end.

**Steps:**

1. Customer clicks **Request Cancellation**.
2. **New route:** `GET /my/requests/<id>/retainer/cancel/preview`  
   - Show: "Your subscription ends on X. Refund (per policy): Y. [Confirm] [Back]."
3. `POST /my/requests/<id>/retainer/cancel` (existing, enhanced):
   - Set `wink_cancellation_requested = True`.
   - If `cancellation_requires_approval = False`:
     - Create refund/wallet entry per policy.
     - Churn subscription (or schedule churn at period end).
   - If True:
     - Notify coordinator; coordinator approves → same automation.
4. Email to customer: "Cancellation received. Refund: X. Effective date: Y."

---

## 5. Portal UI Enhancements

### 5.1 "Manage your retainer" Card (Request Detail)

| Element | Current | Target |
|---------|---------|--------|
| Current plan | Shown | Same + `wink_plan_id` label (e.g. "Bronze") |
| Upgrade/Downgrade | Single button → new request | **Change plan** → dedicated plan-change page |
| Cancellation | Single button with confirm | **Request cancellation** → preview page with refund amount |
| Proration | Shown after cancel requested | Show **before** cancel (preview) |

### 5.2 New: Plan Change Page

- **Layout:** Current plan (left) | Target plans (right, cards).
- **Per target plan:**
  - Plan name, monthly price.
  - "Upgrade" or "Downgrade" badge.
  - **Upgrade:** "You will pay: X (proration for remaining period)."
  - **Downgrade:** "Credit: X — [Wallet / Next invoice / No refund]."
- **Effective date:** "Immediate" or "Next billing cycle" (from policy).
- **CTA:** "Switch to [Plan]" → POST.

### 5.3 New: Cancellation Preview Page

- Remaining days, end date.
- Refund amount (or "No refund").
- Policy label (Refund / Wallet / No refund).
- "Confirm cancellation" → POST.

---

## 6. Coordinator / Back-Office

### 6.1 Sale Order Form

- **Portal Request tab:** Show `wink_change_type`, `wink_proration_credit`, `wink_proration_charge`, `wink_change_from_order_id`.
- **Smart button:** "Plan change from" → link to source order.
- **Cancellation:** Filter/search for `wink_cancellation_requested = True`; bulk action "Process cancellations".

### 6.2 Subscription Group Config

- All new policy fields in form.
- Help text for each (when to use approval vs auto).

### 6.3 Reporting

- Plan change requests (upgrade/downgrade) by period.
- Cancellation requests by period.
- Proration amounts (credit/charge) for reconciliation.

---

## 7. Implementation Phases

### Phase 1 — Foundation (2–3 days)

1. **Plan–pricing link:** Add `product_pricing_id` to `wink.subscription.plan`; migration to populate from products.
2. **Order fields:** Add `wink_change_type`, `wink_proration_credit`, `wink_proration_charge`.
3. **Policy fields:** Add `upgrade_requires_approval`, `downgrade_requires_approval`, `cancellation_requires_approval`, `min_days_before_cancellation`.
4. **Ensure `wink_plan_id`:** Set on order creation from selected plan (product.pricing → plan).

### Phase 2 — Plan Change Flow (3–4 days)

1. **Route:** `GET /my/requests/<id>/retainer/change-plan` — plan comparison with proration.
2. **Route:** `POST /my/requests/<id>/retainer/change-plan` — create new order or apply change.
3. **Template:** `wink_retainer_change_plan` — plan cards, upgrade/downgrade badges, amounts.
4. **Controller logic:** Proration calculation, policy checks, order creation with proration lines.

### Phase 3 — Cancellation Preview (1–2 days)

1. **Route:** `GET /my/requests/<id>/retainer/cancel/preview` — refund amount, policy, confirm.
2. **Enhance:** `POST /retainer/cancel` — optional auto-processing when `cancellation_requires_approval = False`.

### Phase 4 — Wallet (Optional, 2–3 days)

1. **Model:** `wink.credit.wallet`, `wink.credit.wallet.line`.
2. **Portal:** Show balance; apply to checkout.
3. **Integration:** Downgrade/cancellation credit → wallet when policy = 'wallet'.

### Phase 5 — Automation & Polish (2 days)

1. **effective_date_policy:** Enforce immediate vs next_cycle in subscription handling.
2. **Cron or server action:** Process approved cancellations (refund/wallet) when `cancellation_requires_approval = False`.
3. **Email templates:** Plan change confirmation; cancellation confirmation with refund/effective date.
4. **Tests:** Unit tests for proration; HTTP tests for plan-change and cancel flows.

---

## 8. API / Controller Summary

| Route | Method | Purpose |
|-------|--------|---------|
| `/my/requests/<id>/retainer/change-plan` | GET | Plan comparison page with proration |
| `/my/requests/<id>/retainer/change-plan` | POST | Submit plan change (target_plan_id) |
| `/my/requests/<id>/retainer/cancel/preview` | GET | Cancellation preview (refund amount) |
| `/my/requests/<id>/retainer/cancel` | POST | Confirm cancellation (existing, enhanced) |

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|-------------|
| Proration rounding | Use currency rounding; document formula. |
| Plan–pricing mismatch | Validation: plan must belong to product's subscription group; pricing must exist for product. |
| Double change | Block change if `wink_change_from_order_id` already set on target; or if change request pending. |
| Refund automation | Start with manual; add automation only when payment provider supports it. |
| Wallet abuse | Audit trail; optional max balance; expiry rules. |

---

## 10. Success Criteria

- [ ] Customer sees exact proration and net amount before committing to upgrade/downgrade.
- [ ] Customer sees refund amount before confirming cancellation.
- [ ] Upgrade/downgrade/cancellation respect all policy flags.
- [ ] `wink_plan_id` is always set for retainer orders.
- [ ] Coordinator can process cancellations and plan changes from a single place.
- [ ] Audit trail: chatter on both source and target orders for plan changes.
- [ ] No hardcoded policies; all from `wink.subscription.group`.

---

## 11. Out of Scope (For Later)

- Full payment provider refund automation (Stripe, etc.).
- Multi-currency proration edge cases.
- Proration for mid-cycle plan changes with usage-based billing.
- Customer self-service "undo" of cancellation before effective date.
