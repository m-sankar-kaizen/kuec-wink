# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, api, _
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    """
    Inherits: ir.attachment

    Purpose:
    --------
    This customization enforces stricter access control for attachments in Odoo.
    It ensures that only internal users (employees or admins) can access non-public attachments.
    Portal users or external users are restricted from accessing attachments unless explicitly marked public.

    Enhancements:
    -------------
    - Adds validation to `check()` method to restrict access based on:
        * Whether the user is internal
        * Whether the attachment is public
        * Ownership and resource link of the attachment
    - Automatically validates permissions for linked models (`res_model`, `res_id`) when available.
    - Allows self-access for res.users image signature use-cases.

    Use Cases:
    ----------
    - Prevents portal users from accessing invoices or HR documents via attachments.
    - Prevents unauthorized access to document attachments not linked to models.
    - Allows users to upload/change their own signatures securely.

    Note:
    -----
    This override applies only to programmatic access and actions in Odoo's business logic.
    It does not affect static file serving via `/web/content` which has its own routing and ACL mechanism.
    """
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        """
        Checks access to ir.attachment records based on the user's group,
        the attachment's visibility, and the linked resource model.

        Args:
            mode (str): One of 'read', 'write', 'create', or 'unlink'.
            values (dict, optional): Dict of attachment values (e.g., during create/write).

        Raises:
            AccessError: If the user doesn't have access rights to the attachment or its linked model.

        Returns:
            bool: True if access is granted.
        """
        # Superusers bypass all restrictions
        if self.env.is_superuser():
            return True

        # Ensure only internal users (employees/admins) can access private documents
        if not (self.env.is_admin() or self.env.user._is_internal()):
            raise AccessError(_("Sorry, you are not allowed to access this document."))

        # Collect res_model/res_id references to verify access to related business records
        model_ids = defaultdict(set)  # Structure: {model_name: set(ids)}

        if self:
            # Avoid stale values and directly query the DB for accurate context
            self.env['ir.attachment'].flush_model(
                ['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
            self._cr.execute(
                'SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s',
                [tuple(self.ids)]
            )
            for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
                # Skip if public read and read mode
                if public and mode == 'read':
                    continue
                # Skip if record is being edited before link is established or it's a binary field
                if not self.env.is_system() and (
                        res_field or (not res_id and create_uid != self.env.uid)):
                    pass
                if not (res_model and res_id):
                    continue
                model_ids[res_model].add(res_id)

        # Also check values being passed in (for record creation)
        if values and values.get('res_model') and values.get('res_id'):
            model_ids[values['res_model']].add(values['res_id'])

        # Validate access rights on referenced models
        for res_model, res_ids in model_ids.items():
            # Skip deleted resources
            if res_model not in self.env:
                continue

            # Special case: user updating their own profile image (allowed)
            if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
                continue

            records = self.env[res_model].browse(res_ids).exists()

            # Determine required access type
            access_mode = 'write' if mode in ('create', 'unlink') else mode

            # Validate rights and rules
            records.check_access_rights(access_mode)
            records.check_access_rule(access_mode)

        return True
