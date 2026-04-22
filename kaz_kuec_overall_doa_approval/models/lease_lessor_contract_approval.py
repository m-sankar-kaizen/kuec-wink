# -*- coding: utf-8 -*-
from odoo import models, fields, _


class LesseeLessorContractApproval(models.Model):
    _name = 'lease.lessor.contract.approval'
    _description = 'Lessee Lessor Contract Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'lessor_contract_id'

    lessor_contract_id = fields.Many2one('lease.lessor.contract', string='Lessee Lessor Contract')
