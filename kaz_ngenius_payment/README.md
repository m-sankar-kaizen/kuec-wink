# Payment Provider: N-Genius

Odoo 18 payment provider integration for **N-Genius Online** (by Network International), a hosted payment page gateway serving the GCC/MENA region.

## Key Features

- Hosted Payment Page (HPP) redirect flow — no card data touches your server
- Sandbox / production toggle via the standard Odoo provider `state` field
- Server-side payment status verification (GET order API) — redirect params are never trusted alone
- Asynchronous webhook endpoint for late payment notifications
- Supports AED, SAR, BHD, KWD, OMR, QAR, EGP, JOD, USD, EUR, GBP
- Correct minor-unit amount conversion (2-decimal and 3-decimal currencies)

## Dependencies

- `payment` (Odoo core payment module)

## Installation

**Docker:**
```bash
docker exec -it <container> odoo -d <database> -i kaz_ngenius_payment --no-http
```

**Bare host:**
```bash
python odoo-bin -d <database> -i kaz_ngenius_payment
```

## Configuration

After installation:

1. Go to **Accounting → Configuration → Payment Providers**
2. Find **N-Genius** and click **Activate**
3. Enter your credentials:
   - **API Key** — issued by Network International (found in the N-Genius portal)
   - **Outlet Reference ID** — your merchant outlet ID from the N-Genius portal
4. Set **State** to `Test` for sandbox or `Enabled` for production
5. Configure your **Webhook URL** in the N-Genius portal:
   - `https://<your-domain>/payment/ngenius/webhook/<tx-reference>`

## Access Roles

| Role | Access |
|------|--------|
| Admin / System | Can view and edit API credentials |
| Portal / Public | Can initiate payments via the HPP redirect |

## API Flow

```
Customer → Odoo checkout → POST /outlets/{id}/orders → N-Genius HPP
N-Genius HPP → Customer pays → GET /payment/ngenius/return?ref=<order_ref>
Odoo → GET /outlets/{id}/orders/{ref} → verify status → update transaction
```
