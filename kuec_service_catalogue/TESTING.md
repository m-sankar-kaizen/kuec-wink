# Testing the KUEC Service Catalogue (WINK Portal)

## 1. Prerequisites

- **Odoo** running with `kuec_service_catalogue` (and its dependencies) installed/upgraded.
- **Portal/website** enabled so the routes below are served (e.g. your Odoo base URL + `/services`).
- At least one **portal user** (customer) to log in and test.

## 2. Data setup (backend)

1. **Products**
   - Go to the product (service) and ensure **Available on WINK** is checked.
   - For **retainer**: set **Delivery model** = Retainer, **Commercial structure** = Standalone. Optionally link **Subscription plans** (Odoo quotation templates) so the customer can choose a plan.
   - For **bundle**: set **Commercial structure** = Bundled and link a **Bundle** (with tiers, e.g. Pro, Gold). Optionally link **Subscription plans** so the customer chooses plan + tier.

2. **Employees (optional)**
   - Create **Employee directory** records linked to the portal user’s company (partner) so “Select employees” appears when the service requires it.

3. **Documents (optional)**
   - Attach **Service documents** (required/optional) to the product so the request shows document upload steps.

4. **Subscription plans (for plan selection)**
   - Create **Quotation templates** (Sales → Configuration → Quotation Templates) and link them to the retainer/bundle product via **Subscription plans** on the product form.

## 3. Main URLs

| What | URL |
|------|-----|
| Service catalogue (list) | `/services` |
| Service detail | `/services/<product_id>` |
| New request (form) | `/my/requests/new?product_id=<product_id>` |
| My requests (list) | `/my/requests` |
| Request detail | `/my/requests/<order_id>` |
| Request documents | `/my/requests/<order_id>/documents` |
| Bundle activation | `/my/requests/<order_id>/bundle/` |

Use your instance base URL, e.g. `https://your-odoo.com/services`.

## 4. Test scenarios

### A. Retainer (standalone)

1. Open **Services** → pick a **Retainer-Based Standalone** service → **Request Service**.
2. If the product has **multiple subscription plans**: you should see **“Select Your Plan”** (radio options) first.
3. Fill **Requested Start Date** and **Special Requirements / Notes** (if shown).
4. Click **Submit Request**.
5. Check: redirect to request detail; **Manage your retainer** (plan, upgrade/downgrade, request cancellation) if it’s a retainer and state allows.

### B. Bundle (plan + tier)

1. Open **Services** → pick a **bundle** service → **Request Service**.
2. If the product has **subscription plans**: you should see **“Select Your Plan”** (Odoo native) first.
3. Then **“Select Your Tier”** (e.g. Pro, Gold) with prices and included items.
4. For each child service that requires employees, select employees (and optionally use Select all / Deselect all).
5. Fill start date and notes if shown → **Submit Request**.
6. Check: request detail shows the chosen plan and tier; you can go to **Bundle activation** when the order is confirmed.

### C. Documents

1. From request detail, open **Documents** (or the link that points to `/my/requests/<id>/documents`).
2. Upload required files; check that errors appear if required docs are missing and that success messages appear after upload.

### D. Retainer: upgrade / downgrade / cancel

1. Open a **confirmed retainer** request detail.
2. In **Manage your retainer**: use **Upgrade / Downgrade plan** (if more than one plan is available) and **Request cancellation**.
3. Confirm cancellation: you should see the cancellation-requested state and no more actions (or as per your business rules).

### E. Validation checks

- **Retainer/Bundle with subscription plans**: submit without selecting a plan → form should re-display with “Please select a plan.”
- **Service that requires employees**: submit without selecting required employees → form should re-display with an error.
- **Requested Start Date**: if validated, submitting an invalid or missing date should show an error.

## 5. Quick smoke test (minimal)

1. Log in as a portal user.
2. Go to **`/services`** → open one service → **Request Service**.
3. Fill the form (plan/tier if shown, start date, notes) → **Submit Request**.
4. Open **`/my/requests`** and confirm the new request appears; open it and check **Documents** and **Pay** (if applicable).

## 6. Demo data (optional)

If the module loads **demo data** (`demo_data.xml`), you get sample departments, products, documents, FAQs, and employees. Load demo when installing the module (or in Apps: install with demo) to get these records for testing.
