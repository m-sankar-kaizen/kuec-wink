## 1) Module Discovery

### 1.1 `kuec_portal_foundation`

- **Module name**: WINK Portal Foundation (`kuec_portal_foundation`)
- **Version**: 18.0.1.0.0
- **Category**: Hidden
- **Dependencies**:
  - `base_setup`, `portal`, `sale_management`, `sale_subscription`, `project`, `account`, `helpdesk`, `website`, `website_sale`, `web`, `sign`, `mass_mailing`
- **Key models**:
  - No custom Python models; relies on core Odoo models with additional security and theming.
- **Key menus**:
  - No explicit menuitems defined; module works via security, record rules, and frontend assets.
- **Security groups** (`security/groups.xml`):
  - `group_kuec_admin`: Full backend access to WINK configuration.
  - `group_kuec_coordinator`: Manages requests, quotes, and delivery.
  - `group_kuec_finance`: Finance users for invoices and payments.
  - `group_kuec_vendor`: Vendor portal users, implied from `base.group_portal`.
- **Record rules** (`security/record_rules.xml`):
  - Portal users restricted to:
    - Their own sale orders (by `message_partner_ids`).
    - Their own projects and tasks.
    - Their own helpdesk tickets.
    - Their own invoices.
    - Their own partner/vendor record.
- **ACLs** (`security/ir.model.access.csv`):
  - Header-only; no new model-level ACLs (no custom models).
- **Assets / Theming**:
  - `kuec_portal_foundation/static/src/css/wink_theme.css`: Compiled CSS variables and styling for portal UI (buttons, typography, stage progress bar, bundle cards).
  - `views/portal_templates/branded_layout.xml`: Injects the compiled portal styling inline through the shared website layout.
- **Scheduled actions**:
  - None defined in this module.

### 1.2 `kuec_service_catalogue`

- **Module name**: KUEC Service Catalogue (`kuec_service_catalogue`)
- **Version**: 18.0.2.4.0
- **Category**: Sales
- **Depends on**:
  - `kuec_portal_foundation`, `sale_management`, `website_sale`, `project`, `portal`, `account`, `payment`, `hr`, `web`, `web_tour`, `sale_project`
- **Key models** (`models/`):
  - `product.template` (inherit):
    - Flags/services for WINK availability, classification, subscription plans, portal description, FAQs, payment terms, employee selection rules.
  - `sale.order` (inherit):
    - WINK-specific fields: requested start date, notes, portal flag, source product, bundle tier, recurring pricing linkage, cancellation flag, change-from order link.
    - Cron `_cron_send_expiry_reminders` for subscription expiry emails.
  - `sale.order.line` (inherit):
    - Link to bundle entitlement, with confirm-time validation preventing standalone purchase of bundled-only products.
  - `project.task` (inherit):
    - Employee linkage and compliance-gated stage changes for WINK requests.
  - `project.task.type` (inherit):
    - `portal_visible` flag for controlling which stages are exposed in portal progress bars.
  - `res.partner` (inherit):
    - WINK-specific company metadata and flag for enabling the Employee Directory portal app.
  - `res.config.settings` (inherit):
    - Global configuration parameter for default reminder days before subscription expiry.
  - `product.tag` (inherit):
    - `is_ribbon` flag to show tag as a visual ribbon on website cards.
  - `kuec.service.document`:
    - Per-service required/optional document definitions.
  - `kuec.department`, `kuec.service.nature`:
    - Classification dimensions for services.
  - `kuec.service.faq`:
    - Per-service FAQs for portal display.
  - `kuec.employee.directory`:
    - Employee records per customer company (for selection in service requests and tasks).
  - `kuec.document.submission`:
    - Portal-uploaded documents per requirement and order, with review workflow and mail tracking.
  - `wink.bundle`, `wink.bundle.tier`, `wink.bundle.tier.item`:
    - Definition of service bundles, tiers (Bronze/Silver/Gold, etc.), and included child services/quantities.
  - `wink.bundle.entitlement`:
    - Per-order entitlements for bundle child services, tracking activation counts and creating zero-priced service lines on demand.
  - `wink.subscription.group`, `wink.subscription.plan`:
    - Subscription policy groups and plans for retainers (upgrade/downgrade/cancellation policy, standard monthly price, proration logic).
- **Key wizards**:
  - No separate wizard models; portal flows are controller/QWeb-driven.
- **Controllers** (`controllers/`):
  - `catalogue.py`:
    - `/services`, `/services/<id>`: Public service catalogue and detail pages with filtering and subscription plan display.
  - `request.py`:
    - Registration of new companies/portal users.
    - Authenticated request creation, upgrade/downgrade flows, subscription plan validation, bundle handling, payment integration, retainer cancellation, portal document upload flows, bundle activation, and request detail views.
  - `portal.py`:
    - Portal home counters for WINK.
    - `/my/requests`: Listing of WINK service requests.
    - `/my/employees` and related routes: Employee Directory list, form, and save endpoints.
  - `excel_upload.py`:
    - Downloadable Excel template for employees.
    - JSON-based bulk employee import endpoint.
  - `main.py`:
    - Checkout/payment hardening to block payment for quotes with hidden prices until coordinator unlocks.
- **Views / QWeb** (`views/`):
  - Backend forms/tree views for:
    - Departments, service natures, bundle structures, subscription groups/plans, employee directory, required documents, FAQs.
    - Extended views for `product.template`, `res.partner`, `sale.order`, `project.task`, `project.task.type`, `res.config.settings`.
  - Website/portal templates:
    - Service catalogue, service detail pages, WINK request forms, confirmation page, document upload page, employee directory pages, payment page.
- **Security**:
  - `security/ir.model.access.csv`: ACLs for internal users, coordinators, and portal/public on service docs, FAQs, bundles, entitlements, subscription groups/plans, employee directory, document submissions.
  - `security/record_rules.xml`: Portal record rules for employee directory, document submissions, and bundle entitlements, isolating by commercial partner.
- **Data / Scheduled actions**:
  - `data/ir_cron_data.xml`: Daily cron `ir_cron_kuec_subscription_expiry` calling `sale.order._cron_send_expiry_reminders`.
  - Mail templates for coordinators and customers, demo data, tour data, default classifications, tags, and payment terms.

---

## 2) Functional Explanation (As-Is)

### 2.1 Business Layer – `kuec_portal_foundation`

- **Purpose**:
  - Provides the foundational security groups, record rules, and branding layer for the WINK Shared Services portal.
  - Centralizes portal access patterns so that higher-level catalogue and delivery features can assume clean “own data only” isolation for portal and vendor users.
- **Target departments / stakeholders**:
  - Portal administrators configuring the WINK portal.
  - Service coordinators and finance users consuming portal-submitted work in the backend.
  - Vendor organizations accessing vendor-specific portal views.
- **User roles**:
  - **KUEC Admin**: Back-office administrators with full control over WINK configuration and features.
  - **KUEC Coordinator**: Operational owners handling customer service requests, quotations, project delivery, and approvals.
  - **KUEC Finance**: Finance team handling invoicing and payment oversight for WINK services.
  - **Vendor Portal User**: External vendors accessing a constrained portal view (tickets and assigned work only).
- **Pain points it solves**:
  - Standardizes portal access (customers, vendors) without custom duplication per feature module.
  - Ensures portal users and vendors only see their own orders, projects, tasks, tickets, invoices, and partner records.
  - Provides a central place to apply WINK branding and CSS so that all downstream portal UIs look consistent.

#### Workflow & Data – `kuec_portal_foundation`

- **Security & data isolation**:
  - Extends portal behaviour so that:
    - Customers (portal users) see only those sale orders, projects, tasks, helpdesk tickets, and invoices where their partner is part of the chatter (`message_partner_ids`) or is directly set as partner.
    - Vendor users (in `group_kuec_vendor`) are explicitly denied all sale orders, limited to tickets where they are assigned, and constrained to their own partner record hierarchy.
  - Works entirely at record-rule and group level; no custom workflow or new models are introduced.
- **Branding / UI**:
  - `wink_theme.css` defines CSS variables for brand colours, typography, portal menu decoration, and reusable UI components such as:
    - Multi-stage delivery progress bar.
    - Bundle tier selector card visuals.
  - `branded_layout.xml` injects the compiled portal CSS inline through `website.layout`.

### 2.2 Business Layer – `kuec_service_catalogue`

- **Purpose**:
  - Implements the WINK Shared Services catalogue, portal ordering, subscription/retainer policies, document compliance, and employee directory.
  - Bridges customer-facing web flows (catalogue and portal) with backend delivery (projects/tasks) and billing (sales/subscriptions).
- **Target departments**:
  - Shared Services / Operations managing catalogue offerings and service delivery.
  - Sales/Customer success teams configuring bundles and subscription tiers.
  - Compliance teams tracking and approving customer-submitted documents.
  - HR / Admin teams at the customer side managing employee directories.
- **User roles**:
  - **Customer (portal user)**:
    - Browses public catalogue, registers company, submits service requests, uploads compliance documents, manages retainers, and optionally manages employee directory entries.
  - **Coordinator (`group_kuec_coordinator`)**:
    - Reviews new requests, finalizes pricing (including hidden-price scenarios), manages subscription change requests, checks document compliance, and coordinates task progression.
  - **Back-office user (`base.group_user`)**:
    - Internal staff configuring catalogue metadata (departments, natures, documents, FAQs, bundles, subscription groups/plans).
  - **Administrator (`group_kuec_admin`)**:
    - Configures global settings, security, and oversees the entire WINK configuration.

#### 2.2.1 Workflow – From Catalogue to Closure

**1) Discover services (public website – `/services`)**

- Any visitor (public or logged-in) can:
  - View the WINK catalogue of services that are:
    - `available_on_wink = True`
    - `sale_ok = True`
    - `active = True`
  - Filter by:
    - Departments (`kuec.department`)
    - Service natures (`kuec.service.nature`)
    - Delivery model (`project` vs `retainer`)
    - Free-text search on service name.
- Each service card uses `wink_description` converted to plain text and truncated for a short teaser.

**2) Inspect a service (public website – `/services/<id>`)**

- The service detail page shows:
  - Full service overview (`wink_description`).
  - Classification tags (departments, natures).
  - FAQs (`kuec.service.faq`).
  - For retainers:
    - Subscription plans built from native Recurring Prices/pricing models via `_wink_subscription_plans_dicts`.
    - Monthly/annual pricing, equivalent monthly cost, savings banners, and feature bullets.
- If the visitor is authenticated:
  - A “Request” action is available, linking to the service request form.
- If the visitor is anonymous:
  - They are redirected into a registration flow before the request form.

**3) Registration (anonymous → portal user)**

- Anonymous user hitting “Request” is sent to a registration form:
  - Captures company details, trade/tax license numbers, legal entity type, and primary contact info.
  - Validates that the email does not already exist as a partner/user; if it does, asks them to sign in.
- On success:
  - Creates a new company `res.partner` as the customer’s organization.
  - Creates a child contact partner for the primary contact.
  - Creates a `res.users` portal user bound to that contact and adds them to `base.group_portal`.
  - Triggers a reset-password email, then redirects them to login and back to the request form.

**4) Submit service request (portal – `/my/requests/new` / `/services/<id>/request`)**

- Pre-conditions:
  - Product must be `available_on_wink`.
- For authenticated portal users:
  - The controller:
    - Preloads employees from `kuec.employee.directory` for the user’s commercial partner.
    - If requested as upgrade/downgrade from an existing retainer:
      - Validates that the referenced `sale.order` belongs to the same commercial partner and is a WINK portal request.
      - Fetches subscription policy from `wink.subscription.group` via `_wink_get_policy` to precompute allowed operations and textual labels.
      - Optionally computes proration data through `_wink_compute_proration` to show remaining value.
    - For bundle services:
      - Resolves bundle and tiers (`wink.bundle` and `wink.bundle.tier`) and their included items.
      - Renders per-tier child services and allows selecting employees per child service.
    - For subscription services:
      - Builds subscription plans from Recurring Prices or subscription plan models.
      - Handles plan preselection via `?plan=<recurrence_id>`.
- Validation rules on POST (`/my/requests/submit`):
  - For retainers:
    - Ensures a billing plan is chosen when recurring prices exist (either via `selected_recurrence_id` or legacy `recurring_pricing_id`).
    - Ensures customers cannot create a duplicate active retainer for the same service (unless this is an explicit change-from flow).
  - For employee selection:
    - For standalone services with `requires_employee_selection = True`:
      - Enforces at least one employee selected.
    - For bundles:
      - Enforces employee selection per child service that requires it, and returns a clear error per missing child.
- Resulting data:
  - Creates a `sale.order` flagged as a WINK request:
    - `partner_id` = commercial partner.
    - `order_line` = 1 line for the requested service.
    - `wink_request_notes`, `wink_requested_start_date`, `wink_is_portal_request`, `wink_source_product_id`, `origin='WINK Portal'`.
    - Applies `wink_payment_term_id` if configured on the product.
    - Flag `wink_price_confirmed` depending on `price_visibility` (hidden prices require coordinator unlock).
  - For subscription services:
    - Populates recurrence/plan fields on the order and (if applicable) the order line.
    - Stores `wink_recurring_pricing_id` so policy and proration can safely locate the pricing line without failing when the subscription module is absent.
  - For bundle services:
    - Sets `wink_bundle_tier_id` on the order.
    - Adjusts the bundle order line name/price to reflect the chosen tier.
    - Creates `wink.bundle.entitlement` records per child service and per entitled quantity, optionally with employee selections per entitlement.
  - For standalone services with simple one-time requests:
    - Optionally auto-confirms the order (triggering native project/task creation) when:
      - `commercial_structure == 'standalone'` and `request_frequency == 'one_time'`.
- Notifications:
  - Posts a chatter message indicating submission via WINK portal.
  - Sends coordinator notification and customer confirmation emails using configured mail templates.

**5) Post-submission portal experience**

- **My Requests list** (`/my/requests`):
  - Displays all WINK portal requests for the customer’s commercial partner.
  - Shows subscription badges (using safe precomputed descriptor data to avoid Odoo 18 QWeb descriptor crashes).
  - Supports simple sort options (date, reference, stage).
- **Request detail** (`/my/requests/<id>`) shows:
  - Core order info.
  - For retainers:
    - Current plan label, price, and currency symbol (precomputed).
    - List of available plans for change (based on recurring lines).
  - For bundles:
    - Tier and bundle names, and entitlement state with activation controls.
  - Compliance area:
    - Derived document requirements (for standalone or bundling) via `_wink_document_requirements`.
    - Document submissions and their current review status.
  - Payment CTA for eligible orders.

**6) Document compliance**

- **Service-level document definitions**:
  - For each `product.template`, internal staff can define `kuec.service.document` items declaring:
    - Document name.
    - Requirement level (required/optional).
    - Any reference attachments.
- **Document submissions from portal**:
  - Portal page `/my/requests/<id>/documents`:
    - Lists required and optional documents for that specific request:
      - For standalone services: derived from the service product’s `kuec_document_ids`.
      - For bundles: union of document requirements across child service products in all entitlements.
    - Shows upload forms per requirement and the current submission state via `kuec.document.submission`.
  - Upload endpoint (`/my/requests/<id>/documents/upload`):
    - Ensures the order belongs to the logged-in customer (commercial partner).
    - Ensures the requested requirement actually belongs to that order’s allowed requirements.
    - Validates file presence and mimetype (PDF, key image and Word formats).
    - Creates or updates a `kuec.document.submission`:
      - Links to `sale.order`, `kuec.service.document`, and `ir.attachment`.
      - Sets state to `under_review` and records submission timestamp.
    - Redirects back with success or specific error flags for the QWeb template.
- **Back-office document review**:
  - Coordinators use `kuec.document.submission` actions:
    - `action_approve`: sets state to `approved`, records reviewer and time, clears notes.
    - `action_request_change`: enforces presence of coordinator notes, sets `change_required`, and logs the request.
    - `action_reject`: enforces a rejection reason and sets state to `rejected`.
  - Each decision:
    - Posts a clear chatter message on the associated `sale.order`.
    - Optionally sends a customer-facing email via mail template.
  - Customers can open or download attachments via dedicated actions returning `ir.actions.act_url`.
- **Task-stage hard gate**:
  - When a project task progresses from the initial stage (sequence ≤ 10) to a later stage on a WINK portal request:
    - The system checks `_wink_all_required_docs_approved()` on the linked order.
    - If any required documents are not approved, it blocks the stage change with a detailed error listing missing items.

**7) Employee Directory workflow**

- **Backend management**:
  - Internal users:
    - Define `kuec.employee.directory` entries per customer company (`partner_id`).
    - Benefit from validation that passport and Emirates ID values are globally unique (except when blank).
    - Use Odoo backend forms/views for editing and browsing.
- **Portal self-service**:
  - When a partner has `employee_directory_enabled = True`:
    - Portal exposes `/my/employees` listing employees for the customer’s commercial partner.
    - Portal shows:
      - A list view with sorting options (name, job title, UAE status).
      - A detailed edit form to view or update a single employee.
      - A creation form for adding new employees.
    - Controller-level access control:
      - All reads/writes validate that the employee’s `partner_id` is exactly the portal user’s commercial partner.
  - Bulk import:
    - Customers can:
      - Download a standardized Excel template with all supported fields.
      - Upload a populated Excel file for batch import.
    - Server-side parsing:
      - Normalizes and validates text, dates, enumerated values, and country names/codes.
      - Collects row-level error messages if values are malformed.
      - On success, creates `kuec.employee.directory` entries for the partner in a transactional savepoint and returns a JSON result with success count and/or errors.

**8) Retainer subscription lifecycle & expiry reminders**

- **Policy definition**:
  - Per retainer product:
    - Assigns a `wink.subscription.group` that:
      - Controls whether upgrades/downgrades/cancellations are allowed.
      - Defines minimum days before a plan change is allowed.
      - Determines whether downgrade/cancellation credits go to wallet, next cycle, or not refunded.
    - Defines plans (`wink.subscription.plan`) with:
      - Standard monthly price (used for proration).
      - Optional recurrence-name hints.
  - The proration logic:
    - Uses standard monthly price and remaining days in the current period (via `_compute_remaining_credit`).
    - Ignores any annual discounts for the purpose of remaining value calculations.
- **Order linkage**:
  - For retainer orders:
    - The system:
      - Links the order to a product’s subscription group/policy.
      - Stores the selected pricing line (`wink_recurring_pricing_id`) and recurrence ID where applicable.
  - Upgrade/downgrade flows:
    - Link the new order back to the previous order via `wink_change_from_order_id`.
    - Post reciprocal chatter messages on both orders with plan labels when available.
- **Expiry reminder cron**:
  - Daily job:
    - Scans confirmed/done orders that have `next_invoice_date`.
    - Pulls global reminder-day offsets from a configuration parameter.
    - Checks per-product override (`reminder_days_before`) if set; else falls back to global list.
    - When a reminder should be sent:
      - Triggers a mail template.
      - Posts a clear audit message on the subscription order.

**9) Payment and price-visibility gating**

- **Hidden pricing**:
  - For some services, `price_visibility = 'hidden'`:
    - Portal creates the request but sets `wink_price_confirmed = False`.
    - Checkout and payment routes in both `/shop` and `/my/requests/<id>/pay`:
      - Detect presence of any hidden-price products and prevent payment until coordinator toggles the flag via `action_kuec_finalize_price`.
  - Coordinators:
    - Use `action_kuec_finalize_price` to unlock payment once they have finalised pricing.
    - The action also posts a chatter message for audit.
- **Upfront deposit handling**:
  - For configured payment terms with a percentage-based first line:
    - The request payment controller overrides the payment amount from total to the computed deposit amount.
    - Ensures portal uses a deposit while leaving the underlying order totals/invoices intact.

**10) Closure / Cancellation**

- **Closure**:
  - For one-time services:
    - Orders can be auto-confirmed, spawning tasks which then move through stages subject to compliance hard-gate logic.
  - For retainers:
    - Service delivery is continuous, with bundle entitlements being activated over time and tracked against entitlements.
- **Cancellation (retainers)**:
  - Customers can:
    - Trigger a cancellation request via `/my/requests/<id>/retainer/cancel`.
    - This sets a flag and posts a chatter message; no automatic subscription termination is executed in this module.
    - Coordinators must then act in the backend to fully end the subscription according to policy.

---

## 3) Findings (Issues List)

> Note: Issue IDs are the sole allowed drivers for code changes. No change may be implemented without being explicitly linked to one of the Issue IDs below.

| ID | Severity | Area | File/Model/View | Description | How to Reproduce | Current vs Expected | Risk/Impact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISSUE-001 | Medium | Upgrade / Performance / Best Practice | `kuec.employee.directory` (`models/kuec_employee_directory.py`) | `_auto_init` uses raw SQL updates to normalize empty strings to NULL for passport and Emirates ID fields. This bypasses ORM, is harder to maintain across database engines, and violates the “ORM only” rule, while also lacking explicit multi-company scoping. | Install/upgrade the module on a database with existing employee rows where `passport_number` or `emirates_id` are empty strings; `_auto_init` runs and executes raw SQL `UPDATE` statements. | **Current**: Direct SQL `UPDATE` on the table with fixed column names. **Expected**: Use ORM-based cleanup with proper model awareness and error handling, preserving behaviour but aligning with upgrade-safe Odoo practices. | Medium: Behaviour is currently correct but brittle; future schema changes or non-PostgreSQL backends could break silently; raw SQL also complicates review and testing. |
| ISSUE-002 | High | Security | `controllers/excel_upload.py` – `upload_employees` route | Bulk employee import route disables CSRF protection (`csrf=False`) and is reachable for any logged-in portal user whose partner has `employee_directory_enabled`. Combined with file upload, this increases exposure to CSRF-based attacks that could inject unintended employees into a customer’s directory. | As a logged-in portal user with employee directory enabled, inspect the `/my/employees/upload` network call from the frontend; note the route specifics (`csrf=False`). A malicious site could trigger a cross-origin POST while the user is logged in. | **Current**: Route is protected only by `auth='user'` and partner flag; no CSRF, no additional anti-automation headers, and no explicit origin checks. **Expected**: CSRF protection enabled or an equivalent strong mitigation (e.g., CSRF token, X-Requested-With enforcement, origin/referrer validation) while keeping UX intact. | High: Data integrity risk (silent mass insertion of employees for a portal customer) and potential reputational risk; while constrained to logged-in users, it remains a realistic CSRF vector. |
| ISSUE-003 | Medium | UX / Error Messaging | `project.task` override (`models/project_task.py`) | The compliance hard-gate error message on stage change for standalone services can show low-quality labels (Python record repr) when pending docs are a recordset instead of human-readable names, making it harder for coordinators to understand which documents are missing. | Create a WINK portal request for a standalone service with required documents, upload none, then move the first task from the initial stage to a later stage. Observe the error message content for pending docs. | **Current**: `_wink_all_required_docs_approved` returns a recordset for standalone flows, and the error code `str(p or _('Unknown'))` produces technical strings instead of the document names. **Expected**: Error consistently lists user-friendly document names in all scenarios (standalone or bundle). | Medium: Functional behaviour is correct (hard-gate works), but UX is confusing, which slows operations and increases support overhead. |
| ISSUE-004 | Medium | Security / Multi-Company / Portal | `security/record_rules.xml` in `kuec_portal_foundation` – `rule_portal_sale_order_personal` | Portal rule on `sale.order` gives portal users write access to their own orders (while preventing create/unlink). This is more permissive than many standard portal setups, potentially allowing portal users to edit sensitive fields on confirmed orders, affecting accounting integrity if not fully constrained by view-level logic. | Log in as portal user, navigate to `/my/orders` or `/my/requests` (depending on enabled menus), attempt to edit accessible fields on confirmed orders through any backend-like or RPC channel if available. | **Current**: `perm_write=True` for portal users on `sale.order`, with domain limited to `message_partner_ids` membership. **Expected**: Either fully intentional write access with additional field-level controls, or stricter read-only rules for portal to align with conservative accounting and audit practices. | Medium: Depends on the exposed views and fields; potential for accidental or intentional edits to financially relevant orders from the portal side. Needs explicit confirmation of business intent or narrowing of write scope. |
| ISSUE-005 | Medium | Security / CSRF | `controllers/request.py` and `controllers/portal.py` – multiple POST routes | Most POST routes use `csrf=True`, but CSRF is disabled for the JSON-based employee upload route only. There is no additional lightweight header or origin check to compensate. While this is captured as ISSUE-002, the broader pattern should be validated to ensure no other routes silently weaken CSRF guarantees. | Review all routes in `kuec_service_catalogue` and attempt CSRF-free POST calls (e.g., via curl or a crafted HTML form). | **Current**: POST routes for request submission and registration use CSRF correctly; Excel upload does not. **Expected**: A consistent pattern where exceptions to CSRF are rare, narrowly scoped, and compensated by other mitigations. | Medium: The concrete exploitable case is ISSUE-002; this item tracks the need for a consistent mitigation story around CSRF exceptions. |
| ISSUE-006 | Low | Multi-Company / Configuration | `res.config.settings` + `sale.order._cron_send_expiry_reminders` | Reminder thresholds for subscription expiry are stored in a global `ir.config_parameter`. In a multi-company WINK deployment with different reminder policies per company, this would not be sufficient, and the logic does not currently consult `res.company`-level settings. | Configure multiple companies with potentially different expiry reminder needs; observe that the cron uses a single global parameter for all subscriptions. | **Current**: Global CSV setting `kuec_service_catalogue.default_reminder_days` applied uniformly to all subscriptions across companies unless product override is used. **Expected**: Either explicit documentation that reminders are global, or a company-aware configuration (e.g., `res.company` fields surfaced via settings) plus corresponding cron logic. | Low/Medium: Functional today for single-company use; becomes a configuration limitation (not a bug) in multi-company shared-service deployments. |

---

## 4) Proposed Fix Plan (No Code Yet)

> For each Issue ID, this section defines the planned changes, their justification, affected components, change risk, and validation steps. **No code has been modified yet.**

### ISSUE-001 – Replace raw SQL in `_auto_init` on `kuec.employee.directory`

- **Root cause analysis**:
  - `_auto_init` currently executes two hard-coded SQL UPDATE statements directly on `kuec_employee_directory`, normalizing empty strings to NULL for `passport_number` and `emirates_id`.
  - This was introduced to avoid violations of Python-level uniqueness checks when legacy data had empty strings, but it ties the module to a specific table/column layout and bypasses ORM safeguards.
- **Proposed solution**:
  - Refactor `_auto_init` to:
    - Use ORM-based cleanup:
      - Search for records where `passport_number == ''` or `emirates_id == ''`.
      - Write those fields as `False` (NULL) using the model’s own `write` method.
    - Run under `sudo()` to ensure it can clean all companies’ data when upgrading.
    - Keep existing uniqueness constraints and behaviour identical from a business perspective.
  - Avoid any behavioural changes beyond the internal implementation detail (how normalization is performed).
- **Affected components**:
  - `models/kuec_employee_directory.py`:
    - `_auto_init` implementation only.
- **Upgrade risk level**: **Low**
  - Logic continues to normalize data, but via ORM.
  - ORM-based write is idempotent and respects current schema and hooks.
- **Validation plan**:
  - In a test database:
    - Seed `kuec.employee.directory` records with `passport_number=''` and `emirates_id=''`.
    - Trigger module upgrade (or call `_auto_init` in isolation).
    - Confirm:
      - Those empty strings are converted to NULL (`False` in ORM).
      - No uniqueness errors arise when creating new records with blank values.
      - No other fields are modified.

### ISSUE-002 – Harden Excel bulk employee upload route (`/my/employees/upload`)

- **Root cause analysis**:
  - The Excel upload endpoint is a powerful data-write operation but is configured with `csrf=False`.
  - It currently relies only on `auth='user'` and partner-level checks; there is no explicit CSRF token or header check, so a malicious third-party site could trick a logged-in user into submitting a file upload.
- **Proposed solution**:
  - Re-enable CSRF protection on the route **and/or** add layered mitigations that are compatible with the current frontend implementation:
    - Preferred approach:
      - Set `csrf=True` and ensure the frontend Ajax/form uses Odoo’s standard CSRF token (`csrf_token` field or X-CSRFToken header).
    - If CSRF cannot be re-enabled without breaking existing clients (e.g., already-deployed external integrations), add:
      - A strict `X-Requested-With: XMLHttpRequest` header check, rejecting non-AJAX calls.
      - Optional origin/referrer check to enforce same-origin requests.
  - Preserve the JSON response contract (success_count + errors) for the frontend.
- **Affected components**:
  - `controllers/excel_upload.py`:
    - Route definition for `/my/employees/upload`.
    - Potential minor adjustments to error handling if CSRF failures need graceful UX.
  - (Frontend JS/template as needed to pass CSRF token or header – outside Python scope but tracked as part of this plan.)
- **Upgrade risk level**: **Medium**
  - Risk of breaking existing uploads if the frontend is not updated in lockstep.
  - Change will be implemented carefully with compatibility considerations; if risk is too high for current deployment, we may start with header/origin checks before full CSRF enforcement.
- **Validation plan**:
  - From portal UI:
    - Verify successful upload of a valid template file still works.
    - Verify invalid Excel formats still return structured JSON errors.
  - From an external site (simulated CSRF):
    - Attempt a simple HTML form POST without CSRF token and without `X-Requested-With`; ensure request is rejected or redirected harmlessly.

### ISSUE-003 – Improve compliance hard-gate error messaging on task stage change

- **Root cause analysis**:
  - `_wink_all_required_docs_approved` returns:
    - For bundles: `(bool, list_of_pending_doc_names)`.
    - For standalone services: `(bool, recordset_of_pending_submission_records)`.
  - The task-stage write override treats the second value generically as an iterable and turns each element into `str(p)`, which for recordsets results in technical representations (e.g., object repr) rather than friendly document names.
- **Proposed solution**:
  - Normalize the return type of `_wink_all_required_docs_approved` so that:
    - In both cases, the second value is a list of doc-name strings (or a homogeneous list of human-readable labels).
  - Update the task-stage write override to:
    - Assume it receives a list of strings and format them directly, removing the need to infer names from recordsets.
  - Keep the functional “hard gate” semantics unchanged: stage change remains blocked until all required docs are approved.
- **Affected components**:
  - `models/kuec_service_request.py` (SaleOrderWink methods, particularly `_wink_all_required_docs_approved`).
  - `models/project_task.py` (`write` override using `_wink_all_required_docs_approved`).
- **Upgrade risk level**: **Low**
  - Change affects only the return payload shape of a helper, not its boolean gate.
  - Entry points are limited and under our control (task write override).
- **Validation plan**:
  - For standalone services with required docs:
    - Attempt to move a task from initial to later stage with missing submissions; confirm error lists clear document names.
    - Approve docs, retry stage change; confirm it succeeds.
  - For bundle services:
    - Repeat the scenario with bundle child-service requirements and confirm names are correctly listed in the error.

### ISSUE-004 – Confirm or narrow portal write access on `sale.order`

- **Root cause analysis**:
  - Portal record rule `rule_portal_sale_order_personal` grants portal users write access on `sale.order` records where they are partners in the chatter.
  - Depending on how views are exposed, this could allow portal users to modify fields on confirmed orders that may affect reporting or downstream flows.
- **Proposed solution**:
  - Short term (review/documentation step):
    - Explicitly document this design choice in the review report and confirm with product/functional owners whether portal write access on orders is intentional and necessary (e.g., to allow customers to adjust non-financial fields like notes).
  - Longer term (if business confirms read-only intent):
    - Introduce a safer record rule (or duplicate) with `perm_write=False` for portal users on `sale.order`, while relying on portal-specific controllers and views for safe interactions.
    - Alternatively, restrict write access via field-level security or view logic to non-financial, low-risk fields only.
- **Affected components**:
  - `kuec_portal_foundation/security/record_rules.xml` (portal rule on `sale.order`).
  - Potential portal views if write is narrowed (outside this immediate code change scope).
- **Upgrade risk level**: **Medium/High** (if we change permissions)
  - May impact existing portal behaviour where customers expect to edit certain fields.
  - Because of this, any change will be postponed until explicit approval and potentially released behind configuration.
- **Validation plan**:
  - Once a decision is made:
    - Test portal flows for viewing and editing orders.
    - Ensure no unintended access errors appear (especially at payment, confirmation, or document upload steps).

### ISSUE-005 – Clarify multi-company behaviour for subscription expiry reminders

- **Root cause analysis**:
  - Reminder offsets come from a global `ir.config_parameter`, and the cron applies them uniformly to all subscriptions with `next_invoice_date`.
  - In a multi-company shared-services scenario, different company entities might require different reminder policies.
- **Proposed solution**:
  - Introduce company-level configuration for reminder days:
    - Add a `many2one` field or integer array-like configuration on `res.company` (e.g., `wink_reminder_days_before`).
    - Expose it via `res.config.settings` as editable per company.
  - Adjust `_cron_send_expiry_reminders` logic:
    - For each subscription, resolve reminder days from:
      - Product-level override if set.
      - Else company-level configuration if present.
      - Else global default.
  - Clearly document the precedence and defaults in settings descriptions.
- **Affected components**:
  - `models/res_config_settings.py` (to surface new company-level fields).
  - Potential new fields on `res.company`.
  - `models/sale_order.py` (`_cron_send_expiry_reminders`).
- **Upgrade risk level**: **Medium**
  - Field additions on `res.company` and expanded logic in cron.
  - Needs careful migration to avoid changing behaviour in existing single-company deployments.
- **Validation plan**:
  - Single-company environment:
    - Ensure behaviour remains identical when company-level setting is left empty.
  - Multi-company test:
    - Configure different reminder days per company.
    - Create subscriptions per company and advance dates to trigger reminders.
    - Confirm each company’s subscriptions follow its configured policy.

---

## 5) Implementation Summary (To Be Completed After Fixes)

> No code changes have been applied yet. This section will be populated once the approved fixes (by Issue ID) are implemented.

- **Planned content** (post-implementation):
  - For each Issue ID:
    - Short description of the change.
    - Files updated.
    - Notes on data migration (if any).
    - Result of validation steps.

---

## 6) Manual Test Checklist

### 6.1 Shared Flows (Both Modules)

- **Portal access & isolation**:
  - Log in as different portal users; verify that each sees only:
    - Their own requests, projects, tasks, tickets, invoices, and partner records.
  - Attempt to access objects belonging to a different partner; confirm access is denied or redirected.

- **Branding / UI**:
  - Check that WINK theme variables apply correctly on portal menus, buttons, progress bars, and tier cards.

### 6.2 Service Catalogue & Requests

- **Service discovery**:
  - Browse `/services`:
    - Filter by department, service nature, and delivery model.
    - Search by keyword.
    - Confirm only `available_on_wink` and active, saleable products appear.

- **Service detail & subscription plans**:
  - Open `/services/<id>` for:
    - One-time project service.
    - Retainer service with multiple Recurring Prices.
  - Confirm:
    - Plan cards show correct durations, prices, savings, and feature bullets.
    - “Most popular” flag is rendered where set.

- **Registration flow**:
  - Start from an anonymous user:
    - Submit registration for a new company.
    - Ensure duplicate email detection works.
    - Confirm portal user is created and reset-password email is sent (or at least action invoked).

- **Request creation (standalone)**:
  - As a portal user:
    - Submit a request for a standalone one-time service that:
      - Requires employee selection.
      - Has required documents.
    - Verify:
      - Order is created with WINK flags and origin.
      - Auto-confirm occurs only when rules are met.

- **Request creation (retainer)**:
  - Submit a request for a retainer service:
    - With recurring prices and a selected plan.
    - Ensure that:
      - Order captures recurrence/plan and `wink_recurring_pricing_id`.
      - Request detail page shows correct plan label and price.

- **Upgrade/downgrade flow**:
  - From a live retainer:
    - Initiate a change request (upgrade or downgrade).
    - Confirm:
      - New order is linked back to old order.
      - Proration and policy labels are displayed.
      - Chatter notes appear on both orders.

### 6.3 Bundles & Entitlements

- **Bundle request**:
  - Configure a bundle with multiple tiers and child services.
  - Submit a portal request for a bundle:
    - Select a tier.
    - Provide employees per child service where required.
  - Verify:
    - Order’s bundle line shows tier-specific name and price.
    - Entitlements are created correctly for each child service and quantity.

- **Entitlement activation**:
  - From the portal:
    - Activate entitlements one by one.
    - Confirm:
      - Each activation creates a new (free or zero-priced) service order line.
      - `qty_activated` and state update correctly.
      - Chatter logs capture activation details.

### 6.4 Document Compliance & Tasks

- **Document definition and upload**:
  - For a product:
    - Define required and optional documents.
  - For a portal request:
    - Upload compliant and non-compliant files.
    - Validate mimetype restriction behaviour.

- **Review workflow**:
  - As coordinator:
    - Approve, request changes, and reject document submissions.
    - Confirm:
      - States, reviewer, and timestamps are updated.
      - Chatter notes and notification emails behave as expected.

- **Task-stage hard gate**:
  - For a WINK portal request with required docs missing:
    - Attempt to move the first delivery task beyond the initial stage.
    - Confirm error lists human-readable document names.
  - After approving docs:
    - Repeat stage change; confirm it now succeeds.

### 6.5 Employee Directory & Bulk Import

- **Portal list & detail**:
  - With `employee_directory_enabled` on a partner:
    - Access `/my/employees`, create/edit employees, and verify partner isolation.

- **Bulk import**:
  - Download the Excel template.
  - Upload:
    - A valid file; confirm employees are created.
    - A file with deliberate errors; confirm structured JSON errors are returned.
  - Attempt CSRF-like submission (without proper token or headers) and verify protection is effective once changes are applied.

### 6.6 Subscription Expiry Reminders

- **Global reminder behaviour**:
  - Configure default reminder days.
  - Create subscriptions with `next_invoice_date` in the configured offset range.
  - Trigger cron and confirm:
    - Correct reminders are sent.
    - Chatter entries are posted only once per expected date.

- **(If company-level config is implemented)**:
  - Validate differing reminder policies per company as described in ISSUE-005.

---

## 7) Assumptions & Follow-Ups

- **Assumptions**:
  - Current portal write access to `sale.order` and certain other models reflects an intentional design to support specific collaboration features; no change will be made here without explicit product owner approval (tracked under ISSUE-004).
  - Subscription expiry reminders are intended to be global for the first deployment; multi-company support is an enhancement (ISSUE-005), not a bug fix.
  - Existing frontend code for Excel bulk import can be adjusted if CSRF enforcement is introduced; if backwards compatibility is critical, we will favour incremental hardening (headers/origin checks) over immediate CSRF flip.

- **Follow-ups**:
  - Confirm with stakeholders:
    - Whether portal users should ever be able to modify confirmed sale orders (and if yes, which fields).
    - Whether different legal entities in the WINK shared-services network require independent reminder policies.
  - Based on that feedback:
    - Finalize scope and sequencing of fixes for ISSUE-002, ISSUE-004, and ISSUE-005.
  - Once final requirements are agreed, proceed to implement code changes strictly mapped to the Issue IDs defined above.

