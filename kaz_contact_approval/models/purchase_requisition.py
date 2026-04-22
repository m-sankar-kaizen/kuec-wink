# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import ValidationError


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    @api.constrains('vendor_id')
    def _constrains_vendor_id(self):
        for record in self:
            if record.vendor_id.state == 'draft':
                raise ValidationError("You cannot choose the vendor who is in 'Draft' state")
            if record.vendor_id.has_expired_documents:
                raise ValidationError(
                    "You cannot choose a vendor who has expired, Please update the expired documents.")
