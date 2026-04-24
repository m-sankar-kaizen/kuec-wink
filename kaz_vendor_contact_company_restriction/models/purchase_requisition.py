# -*- coding: utf-8 -*-
from odoo import models, api, fields


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.constrains('vendor_id')
    def _constrains_vendor_id(self):
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])
        if kuec_records:
            super(PurchaseRequisition, kuec_records)._constrains_vendor_id()

    def _get_purchase_agreement_reminder_companies(self):
        """filter the companies the cron"""
        return self.env['res.company'].search([('company_code', 'in', ['KUEC'])])
