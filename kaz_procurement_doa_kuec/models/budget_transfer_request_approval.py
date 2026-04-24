# -*- coding: utf-8 -*-
from odoo import models, fields, _


class BudgetTransferRequestApproval(models.Model):
    _name = 'budget.transfer.request.approval'
    _description = 'Budget Transfer Request Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'budget_transfer_request_id'

    budget_transfer_request_id = fields.Many2one('budget.transfer.request',
                                                 string='Transfer Request')
