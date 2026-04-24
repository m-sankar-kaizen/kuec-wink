# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        for record in self:
            if record.partner_id.state == 'draft':
                raise ValidationError("You cannot choose the partner who is in 'Draft' state")
            if record.partner_id.has_expired_documents:
                raise ValidationError(
                    "You cannot choose a partner who has expired documents, Please update the expired documents.")

    def _validate_partner_state(self):
        self.ensure_one()
        if self.partner_id.state != 'approved':
            raise ValidationError(
                "The Partner must be in 'Approved' state to Approve this Quotation.")

    def action_confirm(self):
        for order in self:
            order._validate_partner_state()
        return super().action_confirm()

