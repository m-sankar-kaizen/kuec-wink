# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAssetDepreciationApproval(models.Model):
    _name = 'account.asset.depreciation.approval'
    _description = 'Account Asset Depreciation Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'depreciation_id'

    depreciation_id = fields.Many2one('account.asset.depreciation', string='Account Asset Depreciation')
