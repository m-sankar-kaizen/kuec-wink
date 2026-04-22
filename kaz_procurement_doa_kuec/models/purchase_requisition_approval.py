# -*- coding: utf-8 -*-
from odoo import models, fields, _


class PurchaseRequisitionApproval(models.Model):
    _name = 'purchase.requisition.approval'
    _description = 'Purchase Requisition Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'requisition_id'

    requisition_id = fields.Many2one('purchase.requisition', string='Requisition')
