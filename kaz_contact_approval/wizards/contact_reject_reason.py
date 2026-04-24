# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class ContactRejectReason(models.TransientModel):
    _name = 'contact.reject.reason'
    _description = 'Contact Reject Reason'

    reason = fields.Text(string='Reason')
    partner_id = fields.Many2one('res.partner', string='Partner')


    def action_reject_contact(self):
        self.ensure_one()
        partner = self.partner_id
        user = self.env.user
        if not partner:
            raise UserError(_("No partner found to reject."))

        partner.message_post(
            body=_("❌ Contact rejected by %s. Reason: %s") % (user.name, self.reason),
            message_type="comment"
        )
        partner.state = 'rejected'
