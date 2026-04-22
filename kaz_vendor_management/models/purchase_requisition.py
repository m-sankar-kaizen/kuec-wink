# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    order_type = fields.Selection(
        selection=[
            ('material', 'Material Request'),
            ('service', 'Service Order'),
        ],
        string='Order Type',
    )
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ')
    tender_bid_id = fields.Many2one('tender.bid', string='Tender Bid', help="Awarded Tender Bid")

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

    def action_confirm(self):
        res = super().action_confirm()
        if self.tender_rfq_id:
            self.tender_rfq_id.purchase_agreement_id = self.id
        return res

    def action_create_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Order"),
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'views': [(False, 'form')],
            'context': {
                'default_requisition_id': self.id,
                'default_tender_bid_id': self.tender_bid_id.id,
                'default_tender_rfq_id': self.tender_rfq_id.id,
                'default_default_currency_id': self.currency_id.id,
                'default_default_user_id': self.user_id.id,
                'default_order_type': self.order_type,
            },
        }
