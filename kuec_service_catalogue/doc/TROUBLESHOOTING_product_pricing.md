# Troubleshooting: "Model 'product.pricing' does not exist in registry"

This error appears when **something** in your deployment still tries to load code that extends `product.pricing`, but that model is not provided by your Odoo instance (e.g. no Subscription app).

## Cause

- The addon **kuec_service_catalogue_subscription** was removed from this repo. It extended `product.pricing`.
- If your **database** still has that addon marked as **Installed**, Odoo will try to load it on every registry reload (e.g. when you click **Install** or **Upgrade** on any app). If the addon code is still on the server (from an older deploy), loading it fails because `product.pricing` does not exist.

## Fix

### 1. Use the latest code (no subscription addon)

- Ensure your deployment (e.g. Odoo.sh) is building from the **latest master** where the folder `kuec_service_catalogue_subscription` no longer exists.
- Redeploy / push to trigger a fresh build so that folder is not present on the server.

### 2. Uninstall the stuck module from the database

If the error persists, the database likely still has **kuec_service_catalogue_subscription** as installed. You must uninstall it.

**Option A – From the UI (if the backend loads)**

- After a deploy **without** the subscription addon folder, the backend may load (the failing module is “missing” and skipped).
- Go to **Apps**, search for **“KUEC Service Catalogue — Subscription Plan Fields”** (or **kuec_service_catalogue_subscription**).
- If it appears as installed, click **Uninstall**.

**Option B – Via SQL (when the backend does not load)**

Run this on your database (replace with your DB name if needed):

```sql
-- Mark as uninstalled so the registry stops trying to load it
UPDATE ir_module_module
SET state = 'uninstalled'
WHERE name = 'kuec_service_catalogue_subscription';
```

Then **restart the Odoo server** and try again (e.g. Install/Upgrade another app). The registry should load without trying to build `product.pricing`.

### 3. Odoo.sh

- Confirm the **branch** used for the build is the one where `kuec_service_catalogue_subscription` has been removed.
- Trigger a **new build** after pushing the latest commits so the addons path no longer contains that module.
- If the error continues, use **Option B** above on the Odoo.sh database (e.g. via Odoo.sh shell or backup/restore with SQL execution).

---

After this, only **kuec_service_catalogue** (without any `product.pricing` dependency) is used. Plan selection and savings still work with whatever recurring pricing your product uses; the optional “Plan Features” and “Most Popular” fields are only available if you add a custom extension when `product.pricing` exists (see `product_pricing_extension_snippet.md`).
