# -*- coding: utf-8 -*-
# ISSUE-001: Post-init hook for empty-string normalization (ORM only; no raw SQL).
# ISSUE-009: Odoo 18 calls post_init_hook(env); use savepoint + batching; never close cr.

BATCH_SIZE = 2000


def post_init_hook(env):
    """
    Normalize empty strings to NULL for passport_number and emirates_id on
    kuec.employee.directory. Idempotent; batched to avoid long locks.
    Do not close env.cr; no threads.
    """
    with env.cr.savepoint():
        Model = env['kuec.employee.directory'].sudo()
        for field in ('passport_number', 'emirates_id'):
            while True:
                records = Model.search([(field, '=', '')], limit=BATCH_SIZE)
                if not records:
                    break
                records.write({field: False})
