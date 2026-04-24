# -*- coding: utf-8 -*-
""" Batch Monetization """
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BatchMonetization(models.TransientModel):
    """ Batch Monetization """
    _name = 'batch.monetization'
    _description = 'Batch Monetization'

    partner_id = fields.Many2one('res.partner', string="Customer")
    amount = fields.Float()

    def create_payment(self):
        """ Create Payment """
        active_id = self._context.get('active_id')
        cheque_management_id = self.env['cheque.management'].browse(active_id)
        self.env['account.payment'].create(
            {'partner_id': self.partner_id.id, 'amount': self.amount, 'cheque_management_id': cheque_management_id.id})

