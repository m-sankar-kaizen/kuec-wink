# -*- coding: utf-8 -*-
from odoo import fields, models, _


class Purchase(models.Model):
    _inherit = 'purchase.order'

    tender_bid_id = fields.Many2one('tender.bid', string='Tender Bid', copy=False)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ', copy=False)
    contract_agreement_id = fields.Many2one(related='tender_rfq_id.contract_agreement_id',
                                            string='Contract Agreement', copy=False)
    is_vendor = fields.Boolean(related='partner_id.is_vendor', string='Is Vendor')
    vendor_score = fields.Float(related='partner_id.vendor_score', string='Vendor Score')
    evaluation_rating = fields.Selection(related='partner_id.evaluation_rating',
                                         string='Evaluation Rating')
    order_type = fields.Selection(
        selection=[
            ('material', 'Material Request'),
            ('service', 'Service Order'),
        ],
        string='Order Type',
    )

    def action_open_tender_contract(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Contract Agreement"),
            'view_mode': 'form',
            'res_model': 'purchase.contract.agreement',
            'views': [(False, 'form')],
            'res_id': self.contract_agreement_id.id,
        }

    def action_material_purchase_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Requisition"),
            'view_mode': 'form',
            'res_model': 'material.purchase.requisition',
            'views': [(False, 'form')],
            'res_id': self.custom_requisition_id.id,
        }

    def action_open_tender_bid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender Bid"),
            'view_mode': 'form',
            'res_model': 'tender.bid',
            'views': [(False, 'form')],
            'res_id': self.tender_bid_id.id,
        }

    def action_open_tender_rfq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender"),
            'view_mode': 'form',
            'res_model': 'tender.rfq',
            'views': [(False, 'form')],
            'res_id': self.tender_rfq_id.id,
        }
