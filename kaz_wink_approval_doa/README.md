# kaz_wink_approval_doa — WINK DOA Approval

## Purpose
Implements a Coordinator-level Delegation of Authority (DOA) approval workflow for WINK company on Account Move records (Vendor Bills, Customer Invoices, Journal Entries, etc.).

## Key Features
- Single-stage approval: Draft → Coordinator Approval → Fully Approved
- Auto-confirms (posts) Vendor Bills on Coordinator approval
- Reject and Return for Correction available at the coordinator stage
- Adds `coordinator_approval` stage to the shared `kuec_approval_state` field
- Extends `action_post` and `button_cancel` visibility rules to enforce the WINK workflow
- KUEC approval flow is completely unaffected

## Dependencies
- `kaz_kuec_overall_doa_approval`
- `kaz_kuec_wink_company`

## Installation
**Docker:**
```bash
docker exec -it <container> odoo -u kaz_wink_approval_doa -d <db_name> --stop-after-init
```
**Bare Host:**
```bash
python odoo-bin -c odoo.conf -u kaz_wink_approval_doa -d <db_name> --stop-after-init
```

## Access Roles (WINK DOA/Access Rights category)

| Group | Role |
|-------|------|
| Coordinator | Approve, Reject, or Return for Correction at the coordinator stage |
| Department Head | Reserved for future multi-level expansion |
| CCOE | Reserved for future multi-level expansion |
| Legal Team | Reserved for future multi-level expansion |
| CEO | Reserved for future multi-level expansion |
| Reset to Draft | Allows resetting posted/approved WINK moves back to draft |

## Approval Flow
```
draft
 └─► [Submit for Approval]  →  coordinator_approval  (notifies all Coordinator users)
                                     ├─► [Coordinator Approve]  →  approved
                                     │         └─► if Vendor Bill: auto-posted (confirmed)
                                     ├─► [Reject]  →  rejected + cancelled
                                     └─► [Return for Correction]  →  draft
```
