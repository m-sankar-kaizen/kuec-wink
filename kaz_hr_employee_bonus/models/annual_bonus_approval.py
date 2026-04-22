# -*- coding: utf-8 -*-
from odoo import models, fields


class AnnualBonusApproval(models.Model):
    _name = 'annual.bonus.approval'
    _description = 'Annual Bonus Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'bonus_id'

    bonus_id = fields.Many2one('annual.bonus', string='Annual Bonus')
