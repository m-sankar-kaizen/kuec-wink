# -*- coding: utf-8 -*-
{
    'name': "Secure Attachment Access Control",
    'summary': """
        Restricts attachment access to internal users only and improves model-level permission enforcement.
    """,
    'description': """
        This module provides enhanced access control for attachments (ir.attachment) in Odoo.

        Key Features:
        - Only internal users (employees or admins) are allowed to access attachments.
        - Portal and public users are denied access unless the attachment is explicitly marked as public.
        - Access is also denied if the attachment is not linked to any record (i.e., missing `res_model` or `res_id`).
        - For record-linked attachments, model-level access rights and record rules are strictly enforced.
        - Allows users to modify their own profile images (e.g., for signature editing in res.users).
        - Fully compatible with Odoo’s default file security and respects `public` flag behavior.

        Use Cases:
        - Prevent portal users from viewing sensitive attachments like payslips, invoices, or internal documents.
        - Secure signature uploads and restrict file modification to authorized users.
        - Enforce strict security compliance in multi-company or multi-user SaaS setups.

        This module extends the `check()` method in `ir.attachment` to ensure consistent backend enforcement.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Security',
    'version': '1.0',
    'depends': ['base'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
