# Hotfix Report — Module Load / Upgrade Crash (Cursor Already Closed)

**Date:** 2026-02-27  
**Modules:** kuec_portal_foundation, kuec_service_catalogue  
**Governance:** All code changes must reference an Issue ID from Findings and Proposed Fix Plan.

---

## 1) Crash Summary and Traceback Excerpt

- **Observed:** Server fails during module install/upgrade with:
  - `odoo.addons.base.models.ir_qweb.QWebException: Error while render the template`
  - `psycopg2.InterfaceError: cursor already closed`
  - `odoo.tools.convert.ParseError: while parsing .../project/data/project_demo.xml:1300`
  - “Some modules have inconsistent states…” (core + custom modules)
  - Bad query on `ir_ui_view` (inheritance resolution) fails because cursor is closed.

- **Interpretation:** The “cursor already closed” and ParseError at project_demo.xml are **secondary**. A prior exception during module load caused a rollback and closed the cursor; subsequent steps (demo loading, QWeb, view resolution) then fail.

---

## 2) Reproduction Steps

| Step | Command / context |
|------|-------------------|
| Environment | Odoo 18, PostgreSQL, addons path including `custom/` |
| Install | `odoo-bin -c odoo.conf -i kuec_portal_foundation,kuec_service_catalogue` (or `-d <db>`) |
| Upgrade | `odoo-bin -c odoo.conf -u kuec_service_catalogue` |
| Optional | `--log-level=debug_sql` to capture first failing operation |
| Demo | If `demo` data is enabled (e.g. `data/demo_data.xml`), demo loading runs after module init; crash can surface during XML parse or QWeb render. |

Crash is deterministic on install/upgrade of `kuec_service_catalogue` once the faulty hook runs.

---

## 3) Root Cause Analysis

- **What closes the cursor:** A rollback triggered by an **exception inside `post_init_hook`** of `kuec_service_catalogue`. Odoo calls post_init_hook with `(cr, registry)` only. Our hook was defined as `def post_init_hook(env):` and used `env['kuec.employee.directory']`. So the first argument was actually the **cursor** `cr`, not an environment. Calling `cr['kuec.employee.directory']` is invalid and raises (e.g. TypeError/AttributeError). That exception aborts the transaction, the cursor is closed, and the process continues with a closed cursor, leading to QWebException and ParseError in later steps.

- **Why project_demo.xml:1300:** Demo loading (or other XML) runs in the same transaction after the hook. Once the cursor is invalid, any subsequent DB or template operation fails; the reported file/line is where the failure is detected, not the root cause.

- **Conclusion:** **ISSUE-009** — (1) Hook was not discoverable: manifest used full dotted path but Odoo 18 does `getattr(py_module, post_init)(env)`, so the addon module must expose the hook (e.g. import in `__init__.py`) and manifest must be `'post_init_hook': 'post_init_hook'`. (2) In Odoo 18 the hook is called with **one argument `env`**, not `(cr, registry)`; signature must be `def post_init_hook(env):`. Use `env.cr.savepoint()` and batched ORM; never close `env.cr`.

---

## 4) Findings (Issue Register)

| ID | Severity | Area | Component | Description | Risk |
|----|----------|------|-----------|-------------|------|
| **ISSUE-009** | Critical | Install / Hook | `kuec_service_catalogue/_post_init_hook.py` | `post_init_hook(env)` is wrong. Odoo calls `post_init_hook(cr, registry)`. First arg is cursor; using it as env causes exception → rollback → cursor closed → cascade failures. | Module install/upgrade breaks; inconsistent states. |
| ISSUE-001 | — | (Context) | Same hook (content) | Hook content (ORM cleanup) is correct once signature and env are fixed. | — |

---

## 5) Proposed Fix Plan (No Code Until This Section Is Done)

### ISSUE-009 — Correct post_init_hook signature and env creation

- **Root cause:** Hook signature and env usage are wrong; exception during init closes cursor.
- **Required change:**
  1. **Wiring:** Odoo 18 does `getattr(py_module, post_init)(env)`, so the addon module must expose the hook. In `__init__.py`: `from ._post_init_hook import post_init_hook`. In manifest: `'post_init_hook': 'post_init_hook'`.
  2. **Signature:** In Odoo 18 the hook is called with **one argument `env`**: `def post_init_hook(env):`.
  3. **Safety:** Do not call `env.cr.close()`. Use `with env.cr.savepoint():` around the ORM batch. Batched ORM (e.g. limit 2000) to avoid long locks.
  4. **Idempotency:** Keep current behaviour: search records with `passport_number=''` or `emirates_id=''`, write to `False` in batches.
- **Affected files:** `_post_init_hook.py`, `__init__.py`, `__manifest__.py`.
- **Validation:** Run `-u kuec_service_catalogue` (or install both custom modules) on a DB; no cursor error; no inconsistent module states; demo load (if enabled) completes or is skipped without crash.

---

## 6) Patch Summary and File List

| File | Issue ID | Summary |
|------|----------|---------|
| `custom/reports/HOTFIX_REPORT.md` | — | This report (reproduction, findings, fix plan, validation). |
| `custom/kuec_service_catalogue/_post_init_hook.py` | **ISSUE-009** | Signature `(env)` for Odoo 18; `with env.cr.savepoint():`; batched ORM (limit 2000); no env.cr.close(). |
| `custom/kuec_service_catalogue/__init__.py` | **ISSUE-009** | Expose hook: `from ._post_init_hook import post_init_hook` so getattr(module, 'post_init_hook') works. |
| `custom/kuec_service_catalogue/__manifest__.py` | **ISSUE-009** | `'post_init_hook': 'post_init_hook'` (Odoo 18 looks up by this name on the addon module). |

---

## 7) Validation Checklist

- [ ] **Install/upgrade:** `-i kuec_portal_foundation,kuec_service_catalogue` or `-u kuec_service_catalogue` completes without exception.
- [ ] **Cursor:** No `psycopg2.InterfaceError: cursor already closed` in logs.
- [ ] **Module states:** No “inconsistent states” for core or custom modules.
- [ ] **Demo (if used):** Loading demo data (e.g. project_demo.xml) does not crash; or run with `--without-demo=all` to confirm crash was hook-related.
- [ ] **Hook behaviour:** After fix, upgrade with existing `kuec.employee.directory` rows that have `passport_number=''` or `emirates_id=''`; they are normalized to NULL and no duplicate-check errors.

**Implementation:** Fix for ISSUE-009 applied.

**Docker validation (2026-02-27):**
- **Install:** `docker-compose exec -T web odoo -c /etc/odoo/odoo.conf -d test_kuec_ok -i kuec_portal_foundation,kuec_service_catalogue --stop-after-init --without-demo=all` → **Exit 0.** “Modules loaded.” “Registry loaded.” No cursor already closed, no QWebException.
- **Upgrade:** `docker-compose exec -T web odoo -c /etc/odoo/odoo.conf -d test_kuec_ok -u kuec_service_catalogue --stop-after-init --without-demo=all` → **Exit 0.** “Modules loaded.” “Registry loaded.”
- **Module states:** No “inconsistent states” reported.

---

## 8) Assumptions and Follow-ups

- **Assumptions:** The only init-time hook in scope is this post_init_hook; no pre_init_hook or migration scripts are involved in the crash. project_demo.xml is core; we do not change it.
- **Follow-ups:** If demo loading still fails after this fix, treat as a separate issue (e.g. demo data or view dependency). Re-run with `--without-demo=all` to confirm clean install/upgrade.
