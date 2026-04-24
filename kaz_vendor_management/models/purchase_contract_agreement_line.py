# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PurchaseContractAgreementLine(models.Model):
    _name = 'purchase.contract.agreement.line'
    _description = 'Purchase Contract Agreement Line'
    _inherit = 'rfq.line.mixin'

    currency_id = fields.Many2one(related='contract_agreement_id.currency_id', string='Currency')
    contract_agreement_id = fields.Many2one('purchase.contract.agreement',
                                            string='Contract Agreement')
    required_qty = fields.Float(string='Required Quantity')
    expected_price_unit = fields.Float(string='Expected Price per Unit')
    amount_in_currency = fields.Float(
        string='Total Amount in Currency',
        store=True,
        help="Total line amount in the selected currency."
    )

