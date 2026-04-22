# -*- coding: utf-8 -*-
from odoo import models, fields, _


class LesseeLeaseContractApproval(models.Model):
    _name = 'lease.lessee.contract.approval'
    _description = 'Lessee Lease Contract Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'lessee_contract_id'

    lessee_contract_id = fields.Many2one('lease.lessee.contract', string='Lessee Lease Contract')
