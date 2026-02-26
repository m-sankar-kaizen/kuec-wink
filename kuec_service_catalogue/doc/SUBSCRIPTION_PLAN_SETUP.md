# KUEC Portal — Subscription Plan Selector — Setup & Validation

**Module:** wink_kuec_portal / kuec_service_catalogue  
**Feature:** Retainer/Subscription plan selection (Service Detail + Request form)  
**Odoo 18 Enterprise Edition**

---

## STEP 2 — Backend Configuration Guide (Business Admin — No Code)

### 2.1 — Enable subscription on the service product

1. Open the service product in **Odoo backend** (e.g. Sales → Products → open the product).
2. In the **Sales** or **General Information** tab, find the **Recurring** checkbox (labelled "Subscription Product" or "Recurring Invoice" depending on the build).
3. **Enable it** and save. The **Pricing** tab will then show a recurring prices section.

### 2.2 — Add pricing plans

1. Go to the **Pricing** tab.
2. Click **Add a line** for each plan:
   - **Recurrence:** Monthly / Quarterly / Annual (from Sales → Configuration → Recurrences).
   - **Price:** the AED amount for that billing period.
   - **Pricelist:** leave blank for all-customer pricing.
3. Add one line per plan. Three lines = three plan cards in the portal.

### 2.3 — Enter plan features and “Most Popular”

After the developer has added the custom fields to `product.pricing`, you will see two new fields per pricing line:

- **Plan Features** — text field: enter one feature per line (each line becomes a bullet in the portal).
- **Most Popular** — checkbox: check on **exactly one** plan per service. The system will not allow more than one “Most Popular” per product.

### 2.4 — Example of correctly configured plans

| Recurrence | Price (AED) | Most Popular | Features (one per line) |
|------------|-------------|--------------|-------------------------|
| Monthly    | 2,500       | ☐            | Full service access<br>Email support<br>Monthly report |
| Quarterly  | 6,750       | ☐            | Full service access<br>Priority support<br>Monthly report<br>Quarterly review |
| Annual     | 24,000      | ☑            | Full service access<br>Dedicated account manager<br>Monthly report<br>Quarterly review<br>Annual audit |

The developer must make these new fields visible on the `product.pricing` list/form in the backend (see Step 8 in the development prompt).

---

## STEP 11 — Odoo 18 Validation Checklist

Use this checklist before marking the feature complete.

### Backend

- [ ] `product.pricing` records created for the test service with Monthly, Quarterly, Annual recurrences.
- [ ] `kuec_plan_features` and `kuec_is_most_popular` fields visible and editable by admin on product form / pricing lines.
- [ ] “Most Popular” constraint fires correctly when two plans are checked (only one per product).
- [ ] `sale.temporal.recurrence` has correct duration and unit for each period (e.g. Monthly 1 month, Quarterly 3 months, Annual 12 months).

### Portal — Service Detail Page

- [ ] Plan cards appear only when `product.recurring_invoice` (or equivalent) is True.
- [ ] Plan cards do **not** appear for one-time services.
- [ ] Savings badges show correct percentages vs. Monthly baseline.
- [ ] “Most Popular” badge shows on the correct plan only.
- [ ] Features list renders correctly (one bullet per line).
- [ ] Monthly plan has no savings badge.
- [ ] Selecting a plan updates the price display without page reload.
- [ ] CTA navigates to request form with `?plan=<recurrence_id>` in URL.

### Portal — Request Form

- [ ] Selected plan summary shows the correct plan from URL param.
- [ ] “Change Plan” (or back-to-service link) works and allows re-selection.
- [ ] Submitting without a plan selection (when required) returns a validation error.
- [ ] Server-side price validation: manipulated recurrence ID is rejected or defaulted safely.

### Sale Order

- [ ] Confirmed subscription order has `is_subscription = True`.
- [ ] `recurrence_id` is set to the selected plan’s recurrence.
- [ ] Order line price matches the `product.pricing` server-side price.

### My Requests

- [ ] Subscription chip shows correct period name on request list.
- [ ] Request detail shows “Subscription Plan” block (plan name, amount, next renewal, state, “Manage Subscription” link).
- [ ] “Manage Subscription” link on request detail goes to `/my/subscriptions`.
- [ ] Native `/my/subscriptions` page shows the subscription.

### Email

- [ ] Customer confirmation email includes “Your Selected Plan” section for subscription orders.
- [ ] Customer confirmation email does **not** include this section for one-time orders.

---

*End of Setup & Validation — KUEC Subscription Plan Selector (v2)*
