# -*- coding: utf-8 -*-
""" Account Payment """
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    """ inherit Account Payment """
    _inherit = 'account.payment'

    cheque_management_id = fields.Many2one('cheque.management')

    @api.onchange('cheque_management_id')
    def _onchange_cheque_management_id(self):
        """ cheque_management_id """
        if self.cheque_management_id:
            self.partner_id = self.cheque_management_id.cheque_management_id.id

    def action_post(self):
        """ inherit action_post() """
        res = super(AccountPayment, self).action_post()
        self.cheque_management_id.batch_monetization += self.amount
        self.cheque_management_id.reminder = self.cheque_management_id.amount - self.cheque_management_id.batch_monetization
        self.cheque_management_id.state_batch_monetization = '1'
        return res
