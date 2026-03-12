# Deep Review Report — WINK Shared Service Addons

**Modules:** `kuec_portal_foundation`, `kuec_service_catalogue`  
**Governance:** All code changes must reference an Issue ID from Findings and Proposed Fix Plan.

---

## 1) Module Discovery

### 1.1 `kuec_portal_foundation`

| Item | Detail |
|------|--------|
| **Name** | WINK Portal Foundation |
| **Version** | 18.0.1.0.0 |
| **Category** | Hidden |
| **Dependencies** | base_setup, portal, sale_management, sale_subscription, project, account, helpdesk, website, website_sale, web, sign, mass_mailing |
| **Models** | None (security + record rules + theming only) |
| **Menus** | None explicit |
| **Security groups** | group_kuec_admin, group_kuec_coordinator, group_kuec_finance, group_kuec_vendor |
| **Record rules** | Portal: sale.order, project, task, helpdesk ticket, account.move, res.partner. Vendor: sale.order deny, helpdesk assigned, partner own. |
| **Assets** | wink_theme.scss; branded_layout.xml (commented) |
| **Cron** | None |

### 1.2 `kuec_service_catalogue`

| Item | Detail |
|------|--------|
| **Name** | KUEC Service Catalogue |
| **Version** | 18.0.2.4.0 |
| **Category** | Sales |
| **Depends** | kuec_portal_foundation, sale_management, website_sale, project, portal, account, payment, hr, web, web_tour, sale_project |
| **Extended models** | product.template, sale.order, sale.order.line, project.task, project.task.type, res.partner, res.config.settings, product.tag |
| **Custom models** | kuec.service.document, kuec.department, kuec.service.nature, kuec.service.faq, kuec.employee.directory, kuec.document.submission, wink.bundle / tier / tier.item, wink.bundle.entitlement, wink.subscription.group / plan |
| **Controllers** | catalogue, request, portal, excel_upload, main |
| **Security** | ir.model.access.csv, record_rules.xml (portal isolation by commercial partner) |
| **Cron** | ir_cron_kuec_subscription_expiry → sale.order._cron_send_expiry_reminders |

---

## 2) Functional Explanation (As-Is)

### 2.1 `kuec_portal_foundation`

- **Purpose:** Foundational security groups and record rules for WINK portal; portal/vendor users see only their own orders, projects, tasks, tickets, invoices, partner. Theming via SCSS variables.
- **Roles:** KUEC Admin (full), Coordinator (requests/quotes/delivery), Finance (invoicing), Vendor (assigned tickets only).
- **Workflow:** No custom workflow; pure access control and branding.

### 2.2 `kuec_service_catalogue`

- **Purpose:** Service catalogue on `/services`, portal service requests, document compliance, employee directory, bundles, subscription/retainer policies and expiry reminders.
- **Roles:** Customer (portal: browse, register, request, upload docs, manage employees); Coordinator (review, finalize price, approve docs, move tasks); Back-office (configure catalogue).
- **Workflow (high level):**  
  Browse catalogue → (optional) register → submit request (standalone or bundle, with plan selection) → order created (WINK flags, optional auto-confirm) → document requirements and uploads → coordinator approves/rejects docs → task stage move blocked until required docs approved → payment gated by wink_price_confirmed → retainer cancellation and upgrade/downgrade via dedicated flows.  
- **Outputs:** Sale orders, project/tasks, document submissions, chatter and mail templates; expiry reminder cron uses global config and product override.

---

## 3) Findings (Issue Register)

| ID | Severity | Area | Component | Description | Reproduce | Current vs Expected | Risk |
|----|----------|------|-----------|-------------|-----------|---------------------|------|
| ISSUE-001 | Medium | Upgrade / Best practice | kuec.employee.directory | Raw SQL in `_auto_init` normalizes empty strings to NULL for passport/emirates_id. Bypasses ORM; unsafe during registry init if replaced by ORM in _auto_init. | Upgrade module with existing rows where passport_number or emirates_id is ''. | Current: SQL UPDATE. Expected: Post-init hook with batched ORM writes (sudo), same behaviour. | Medium |
| ISSUE-002 | High | Security | controllers/excel_upload.py | Employee upload route has `csrf=False`; no file size cap; no strong mitigations. | POST to /my/employees/upload as logged-in portal user without CSRF token. | Current: Accepted. Expected: csrf=True and/or X-Requested-With + origin check + file size cap; sanitized logs. | High |
| ISSUE-003 | Medium | UX | project.task, sale.order | Compliance hard-gate error shows technical/poor labels for pending docs in standalone flows. | Move task from initial stage with required docs missing. | Current: Inconsistent or technical names. Expected: Always list of user-friendly document names. | Medium |
| ISSUE-004 | Medium | Security | kuec_portal_foundation record_rules.xml | Portal sale.order rule has perm_write=True. No business-necessary portal write path identified; controllers use sudo(). | Attempt portal write to sale.order via RPC/view. | Current: Portal can write. Expected: Conservative hardening: perm_write=False unless business requires it. | Medium |
| ISSUE-006 | Medium | Multi-company / Config | res.config.settings, sale.order cron | Reminder days in global ir.config_parameter; cron not idempotent (can re-send same reminder). | Multi-company; run cron twice for same subscription. | Current: Global config; no “reminder sent” marker. Expected: Company-specific config on res.company; product → company → default; idempotent cron with marker. | Medium |
| ISSUE-007 | Verify | Security | Portal record rules | Rules using message_partner_ids may be too permissive; evaluate and harden if needed. | Review domain_force for portal rules. | Document; only implement if verified. | TBD |
| ISSUE-008 | Verify | Security | Document submission attachments | Attachment access must be strictly isolated (no guessable URLs, no broad ir.attachment exposure). | Check how /web/content is used and attachment ACLs. | Document; only implement if verified. | TBD |

---

## 4) Proposed Fix Plan (No Code Yet)

### ISSUE-001 — Raw SQL in _auto_init

- **Approach:** Do **not** put ORM writes inside `_auto_init` (unsafe during registry init). Remove SQL from `_auto_init`. Add a **post_init_hook** (manifest) that runs once after load; in the hook, with batched ORM writes and `sudo()`, find records with `passport_number == ''` or `emirates_id == ''` and write those fields to `False`. Keep behaviour identical.
- **Affected:** `models/kuec_employee_directory.py` (remove _auto_init SQL), new `_post_init_hook.py`, `__manifest__.py` (post_init_hook).
- **Validation:** Upgrade with seeded empty-string data; confirm NULL and no duplicate-check errors.

### ISSUE-002 — Excel upload CSRF hardening

- **Approach:** Prefer `csrf=True` and ensure frontend sends CSRF token. If that breaks deployed clients: keep csrf off only with strong mitigations: require `X-Requested-With: XMLHttpRequest`, enforce same-origin (Origin/Referer), add strict file size cap, add lightweight rate limiting per partner. Keep JSON response contract. Add sanitized logs (counts, no PII).
- **Affected:** `controllers/excel_upload.py`.
- **Validation:** Valid upload still works; POST without token/headers rejected or redirected.

### ISSUE-003 — Compliance gate message quality

- **Approach:** Normalize helper so pending docs are always a **list of user-friendly names** (strings). Update task stage block message to use that list.
- **Affected:** `models/kuec_service_request.py` (_wink_all_required_docs_approved), `models/project_task.py` (write override).
- **Validation:** Standalone and bundle flows show clear document names in error.

### ISSUE-004 — Portal sale.order write access

- **Approach:** Confirm no business-necessary portal write path (controllers use sudo). Default: conservative hardening — set portal rule `perm_write=False`. If business needs limited edits later, add explicit safe controller endpoints, not blanket write.
- **Affected:** `kuec_portal_foundation/security/record_rules.xml`.
- **Validation:** Portal flows (payment, docs, request detail) still work; no unintended access errors.

### ISSUE-006 — Company-specific reminder config + idempotency

- **Approach:** (1) Add reminder-days config on `res.company` (e.g. Char CSV), surface via `res.config.settings`. (2) Cron resolves reminder days in order: product override → company config → fallback default. (3) Make cron idempotent: store a “reminder sent” marker on sale.order (e.g. which day-offsets already sent); do not re-send for same offset.
- **Affected:** New or extended `res.company` fields, `res.config.settings`, `models/sale_order.py` (cron + marker field on sale.order).
- **Validation:** Single-company unchanged when company empty; multi-company uses company config; double cron run does not duplicate reminder.

### ISSUE-007 / ISSUE-008 — Verification only

- **Approach:** Verify and document: (007) whether message_partner_ids rules are too permissive; (008) whether attachments are reachable by unauthorized users. Implement changes only if verified and planned with Issue IDs.
- **Affected:** Report and, if verified, security/controllers.

---

## 5) Implementation Summary (After Fixes)

*(Populated after code changes.)*

| Issue ID | Files changed | Summary | Validation |
|----------|---------------|---------|------------|
| ISSUE-001 | kuec_employee_directory.py, _post_init_hook.py, __manifest__.py | Removed _auto_init SQL; added post_init_hook with batched ORM normalization. | Upgrade + seeded data: empty strings → NULL. |
| ISSUE-002 | excel_upload.py | csrf=True; file size cap (10 MB); sanitized logging. Frontend must send CSRF token (form or header). | Upload with token works; no-token rejected. |
| ISSUE-003 | kuec_service_request.py, project_task.py | _wink_all_required_docs_approved returns (bool, list[str]); task uses list. | Error shows document names. |
| ISSUE-004 | record_rules.xml | Portal sale.order perm_write=False. | Portal flows unchanged; no write from portal. |
| ISSUE-006 | res_company.py, res_config_settings.py, sale_order.py, views/settings, data | Company reminder days; cron product→company→default; wink_expiry_reminder_sent_days on order; idempotent send. | Single/multi-company; no duplicate reminders. |
| ISSUE-007 | — | Verified: portal rules use message_partner_ids; domain limits to own records. No change. | Documented. |
| ISSUE-008 | — | Verified: attachments are ir.attachment with res_model res_id; access follows document submission ACLs. No guessable URL change. | Documented. |

---

## 6) Manual Test Checklist

- [ ] Portal: own orders/projects/tasks only; no cross-user visibility.
- [ ] Create request (standalone + bundle); approve docs; move task (gate message shows doc names).
- [ ] Employee directory: create/edit; bulk upload with valid file (CSRF token); reject POST without token.
- [ ] Subscription expiry: set product/company reminder days; run cron; confirm reminder once per day-offset; run again, no duplicate.
- [ ] Payment gating: hidden price → coordinator unlocks → payment allowed.
- [ ] Retainer cancel/upgrade/downgrade flows and chatter.

---

## 7) Assumptions & Follow-ups

- **Assumptions:** Portal does not need direct write on sale.order (all writes via controller sudo). Reminder idempotency uses a stored list of “already sent” day-offsets on the order. ISSUE-007/008 verification does not require code change unless findings are positive.
- **Follow-ups:** If portal must edit specific order fields later, add explicit controller endpoints and keep perm_write=False. Consider rate limiting for Excel upload if abuse appears. Frontend for `/my/employees/upload` must send CSRF token (e.g. `csrf_token` in form or `X-CSRFToken` header).
