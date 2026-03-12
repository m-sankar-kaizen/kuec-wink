# Commercial Structure — Features and Workflows

This document describes the **Commercial Structure** options on the product (Service) and the **workflow for each type** in the WINK portal.

---

## 1. Commercial Structure options

Defined on **Product Template** (`product.template`, Wink tab). Field: `commercial_structure`.

| Value        | Label      | Description |
|-------------|------------|-------------|
| **standalone** | Standalone | Single service sold on its own. One product per request; employees and documents are at order level. |
| **bundled**    | Bundled    | Service is sold only as part of a **Bundle**. Product must have **Bundle Package** (`wink_bundle_id`) set. Customer chooses a **tier** (e.g. Starter, Pro); each tier has multiple **items** (child services). Price and entitlements come from the selected tier. |
| **flexible**   | Flexible   | Display-only classification. In the portal it shows a "Flexible" badge on the catalogue; **request flow is the same as Standalone** (no bundle tier selection, no bundle entitlements). |

**Related product fields**

- **Delivery Model** (`delivery_model`): `Project` | `Retainer` — drives whether the service uses subscription plans, plan change, and cancellation (retainer) or one-time/project delivery (project).
- **Bundle Package** (`wink_bundle_id`): Required when `commercial_structure == 'bundled'`. Links to `wink.bundle` (tiers and items).
- **Subscription Group** (`wink_subscription_group_id`): For retainer services; defines upgrade/downgrade/cancellation policy and proration.
- **Requires Employee Selection** (`requires_employee_selection`): If set, the request wizard shows the **Employees** step.

---

## 2. Workflow by Commercial Structure

### 2.1 Standalone

**Catalogue**

- Shown with badge **Standalone**.
- Price: visible list price, or “Price based on plan” (retainer), or hidden with custom label.

**Request flow (wizard)**

1. **Step 1 — Configure**
   - Service context (name, delivery model badge, price).
   - **Retainer:** “Select Your Plan” (recurring plans from product’s Recurring Prices). Plan is required.
   - **Project / one-time:** No plan selector (unless product is also retainer).
   - Start date, notes.
   - If **not** `requires_employee_selection`: button “Next: Review” → go to **Step 3**.
   - If `requires_employee_selection`: “Next: Employees” → **Step 2**.

2. **Step 2 — Employees** (only if `requires_employee_selection`)
   - Select one or more employees from the directory.
   - “Next: Review”.

3. **Step 3 — Review**
   - Summary: type (One-time / Retainer / Bundle), plan name (if retainer), start date, notes, employees.
   - Submit → order created.

**After submit**

- **Employees:** Stored on the order (`wink_selected_employee_ids`).
- **Documents:** Required documents come from the **product** (`kuec_document_ids`).
- **Auto-confirm:** If `request_frequency == 'one_time'` and price is confirmed, order can be auto-confirmed; otherwise it stays quotation until coordinator confirms.

**Request detail (portal)**

- Order summary, status, documents, payment.
- **Retainer:** Current plan, upgrade/downgrade, request cancellation (if policy allows).

---

### 2.2 Bundled

**Catalogue**

- Shown with badge **Bundled**.
- Product must have `wink_bundle_id` (Bundle Package) with at least one tier.

**Request flow (wizard)**

1. **Step 1 — Configure**
   - Service context (name, delivery model, price hint).
   - **Select Your Tier:** Choose one of the bundle’s tiers (e.g. Starter, Pro). Each tier has:
     - Name and **price** (shown on card).
     - **Items:** list of included child services.
   - **Bundle total** is shown (selected tier’s price).
   - Start date, notes.
   - If any **child service** in the selected tier `requires_employee_selection`, the **Employees** step is used (Step 2); otherwise “Next: Review” goes to Step 3.

2. **Step 2 — Employees** (per child service)
   - Sections per tier item that require employees.
   - User selects employees per included service (form fields `employee_ids_<tier_id>_<index>`).
   - “Next: Review”.

3. **Step 3 — Review**
   - Summary: type **Bundle**, **tier name**, start date, notes, employee names.
   - Submit → order created.

**After submit**

- **Order line:** Single line for the bundle product; `price_unit` and line name set from the selected **tier** (e.g. “Service Name — Pro”).
- **Tier on order:** `wink_bundle_tier_id` = selected tier.
- **Entitlements:** One `wink.bundle.entitlement` per tier item (child service, qty, name). Employees stored per entitlement (`wink_selected_employee_ids` on entitlement).
- **Documents:** Required documents = union of all **child services’** required documents (`kuec_document_ids` on each entitlement’s `service_product_id`).
- No auto-confirm for bundles (only standalone one-time with confirmed price).

**Request detail (portal)**

- Order summary, status, **Bundle entitlements** (list of included services and usage).
- Document compliance from child services.
- **Retainer:** If the bundle product is retainer, same plan/upgrade/cancel as standalone.

**Backend**

- Bundled products cannot be added as normal standalone lines (validation in `sale.order.line`): they must be requested via the bundle product and tier.

---

### 2.3 Flexible

**Catalogue**

- Shown with badge **Flexible** (and same delivery/price as other types).

**Request flow**

- **Same as Standalone.** No bundle tier, no bundle entitlements, no “Select Your Tier”.
- Steps: Configure (with optional plan if retainer, optional employees if `requires_employee_selection`) → optional Employees → Review → Submit.
- Employees and documents at **order** level, from the single product.

**Use case**

- Purely a **label** to indicate the service can be offered in different ways (e.g. standalone or as part of a package later). Logic does not differ from standalone.

---

## 3. Cross-cutting: Delivery Model

Workflow branches further by **Delivery Model** (and related flags):

| Delivery Model | Plan selection | After order | Portal actions |
|----------------|----------------|------------|----------------|
| **Project**    | No             | Project/tasks (if `project_template_id` etc.) | View request, documents, payment. No plan change. |
| **Retainer**   | Yes (required) | Subscription; recurring invoicing | View request, pay, **change plan** (upgrade/downgrade), **request cancellation** (policy-driven). |

- **Already have subscription:** If the user already has an active (non-cancelled) retainer for the same product, they see “Already have subscription” and can go to **Change plan** instead of creating a new request.
- **Plan change:** From request detail, “Upgrade or downgrade” → `/my/requests/<id>/retainer/change-plan` (select new plan, proration, then pay if needed).
- **Cancellation:** “Request cancellation” → preview (refund/credit per policy) → confirm; coordinator processes and can create credit note.

---

## 4. Summary table

| Commercial Structure | Tier selection | Employees | Documents source     | Order line / entitlements      |
|---------------------|----------------|-----------|------------------------|---------------------------------|
| **Standalone**      | No             | On order  | Product                | One order line, no entitlements |
| **Bundled**         | Yes (required) | Per entitlement (per child) | Child services (union) | One line (tier price); entitlements per tier item |
| **Flexible**        | No             | On order  | Product                | Same as standalone              |

All three types use the same **wizard steps** (Configure → optional Employees → Review); only **Bundled** adds tier selection and per-child employees and documents.
