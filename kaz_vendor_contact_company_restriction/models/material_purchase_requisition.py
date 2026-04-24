# -*- coding: utf-8 -*-
from odoo import fields, models, api


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    action_state = fields.Selection(
        selection=[
            ('no_action', 'No Action Needed'),
            ('rfq', 'RFQ'),
            ('tender', 'Tender'),
            ('action_needed', 'Action Needed'),
        ],
        string='Action State',
        compute='_compute_action_state',
        store=True,
    )
    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.depends('requisition_type_id', 'is_tender', 'kuec_approval_state',
                 'purchase_ids', 'tender_rfq_id')
    def _compute_action_state(self):
        for rec in self:
            # 1. Early exit / Default case
            if rec.kuec_approval_state != 'approved':
                rec.action_state = 'no_action'
                continue

            # 2. Logic based on Tender vs Standard
            if rec.is_tender:
                # Use inline ternary operator for cleaner assignment
                rec.action_state = 'tender' if rec.tender_rfq_id else 'action_needed'
            else:
                # Check truthiness of recordset (empty recordset = False)
                rec.action_state = 'rfq' if rec.purchase_ids else 'action_needed'

    def _get_purchase_requisition_reminder_companies(self):
        """filter the companies the cron"""
        return self.env['res.company'].search([('company_code', 'in', ['KUEC'])])