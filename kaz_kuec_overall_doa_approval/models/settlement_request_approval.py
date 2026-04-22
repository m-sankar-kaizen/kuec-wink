# -*- coding: utf-8 -*-
from odoo import models, fields, _


class SettlementRequest(models.Model):
    _name = 'settlement.request.approval'
    _description = 'Settlement Request Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'settlement_request_id'

    settlement_request_id = fields.Many2one('settlement.request', string='Settlement Request')
