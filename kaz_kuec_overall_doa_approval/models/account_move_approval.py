# -*- coding: utf-8 -*-
from odoo import models, fields, _


class AccountMoveApproval(models.Model):
    _name = 'account.move.approval'
    _description = 'Account Move Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'account_move_id'

    account_move_id = fields.Many2one('account.move', string='Account Move')
