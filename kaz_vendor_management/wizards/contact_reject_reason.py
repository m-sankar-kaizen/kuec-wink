# -*- coding: utf-8 -*-
from odoo import models


class ContactRejectReason(models.TransientModel):
    _inherit = 'contact.reject.reason'

    def action_reject_contact(self):
        super().action_reject_contact()
        partner = self.partner_id
        if partner.is_portal:
            partner.action_revoke_access()
