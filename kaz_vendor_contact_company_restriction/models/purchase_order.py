# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    company_code = fields.Selection(related="company_id.company_code", string="Company Code")

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])
        if kuec_records:
            super(PurchaseOrder, kuec_records)._constrains_partner_id()
            
    def _validate_partner_state(self):
        self.ensure_one()
        if self.company_code in ['KUEC']:
            super()._validate_partner_state()
            
    @api.constrains('amount_untaxed')
    def _restrict_amount(self):
        """
        Constraint to restrict creation of POs exceeding 2000 unless it's linked to a requisition
        or explicitly marked as a partial PO (`partial_po = True`).
        """
        for rec in self:
            if rec.company_code not in ['KUEC']:
                if rec.amount_untaxed > 2000 and not rec.custom_requisition_id:
                    if hasattr(self, 'partial_po') and getattr(self, 'partial_po'):
                        continue
                    raise ValidationError(
                        _("Not allowed to create an RFQ with amount exceeding 2000."))
