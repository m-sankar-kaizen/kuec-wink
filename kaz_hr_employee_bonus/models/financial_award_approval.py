# -*- coding: utf-8 -*-
from odoo import models, fields


class FinancialAwardApproval(models.Model):
    _name = 'financial.award.approval'
    _description = 'Financial Award Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'award_id'

    award_id = fields.Many2one('financial.award', string='Financial Award')
