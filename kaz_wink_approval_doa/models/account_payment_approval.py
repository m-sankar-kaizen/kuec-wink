# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPaymentApproval(models.Model):
    _name = 'account.payment.approval'
    _description = 'Account Payment Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'payment_id'

    payment_id = fields.Many2one('account.payment', string='Payment')
