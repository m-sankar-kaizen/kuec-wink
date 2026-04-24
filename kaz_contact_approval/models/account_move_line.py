# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        for record in self:
            if record.partner_id:
                if record.partner_id.state != 'approved':
                    raise ValidationError("You cannot choose a partner who is not in 'Approved' state")
                if record.partner_id.has_expired_documents:
                    raise ValidationError(
                        "You cannot choose a partner who has expired documents, Please update the expired documents.")
