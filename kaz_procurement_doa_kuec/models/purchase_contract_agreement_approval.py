# -*- coding: utf-8 -*-
from odoo import models, fields, _


class ContractAgreementApproval(models.Model):
    _name = 'purchase.contract.agreement.approval'
    _description = 'Contract Agreement Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'agreement_id'

    agreement_id = fields.Many2one('purchase.contract.agreement', string='Contract Agreement', )
