# -*- coding: utf-8 -*-
from odoo import models, fields, _


class PettyCashRequestApproval(models.Model):
    _name = 'petty.cash.request.approval'
    _description = 'Petty Cash Request Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'petty_cash_id'

    petty_cash_id = fields.Many2one('petty.cash.request', string='Petty Cash Request')
